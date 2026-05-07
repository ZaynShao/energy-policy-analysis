#!/usr/bin/env python3
"""一次性脚本: 从 5 主题 _input.json + policy_summaries.jsonl 构造前端格式 JSON.

2026-05-07 起加 isolated 过滤(B7 分类后):
  读 _meta/audit/isolated_classification.jsonl,跳过 suggested_action ==
  "exclude_from_main_graph" 的 pid(news/index_page 类污染政策)。
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_exclude_pids() -> set[str]:
    """读 isolated_classification.jsonl,返回 suggested_action='exclude_from_main_graph' 的 pid 集"""
    path = ROOT / "_meta" / "audit" / "isolated_classification.jsonl"
    if not path.exists():
        return set()
    excludes = set()
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if r.get("suggested_action") == "exclude_from_main_graph":
            excludes.add(r["pid"])
    return excludes


EXCLUDE_PIDS = load_exclude_pids()

THEMES = [
    ("V2G", "V2G(车网互动)"),
    ("VPP_THEME", "虚拟电厂"),
    ("CHARGING_INFRA", "充电基础设施"),
    ("ENERGY_STORAGE_THEME", "新型储能"),
    ("POWER_MARKET", "电力市场"),
]

DIRECT_MUNI_CODES = {"110000", "120000", "310000", "500000"}

PROV_OF_CITY = {
    "包头市": ("150000", "包头市"),
    "广州市": ("440000", "广州市"),
    "深圳市": ("440000", "深圳市"),
    "苏州市": ("320000", "苏州市"),
    "慈溪市": ("330000", "慈溪市"),
}

#  直辖市下辖区: cityName 用区名本身,独立成 cityGroup (前端期望)
#  普通省下辖县/县级市: cityName 归并到所属地级市 (前端期望)
DISTRICT_TO_CITY = {
    # 直辖市下辖区 (cityName = 区名,provinceCode = 直辖市码)
    "上海市松江区": ("310000", "松江区"),
    "上海市长宁区": ("310000", "长宁区"),
    "浦东新区": ("310000", "浦东新区"),
    "重庆市南川区": ("500000", "南川区"),
    "重庆市涪陵区": ("500000", "涪陵区"),
    # 普通省下县/县级市 (归并到所属地级市)
    "通许县": ("410000", "开封市"),
}

DIRECT_MUNI_NAME = {
    "110000": "北京市",
    "120000": "天津市",
    "310000": "上海市",
    "500000": "重庆市",
}


def load_summaries():
    p = ROOT / "1_extracted" / "policy_summaries.jsonl"
    out = {}
    with p.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            out[r["policy_id"]] = r
    return out


def shape_summary(rec):
    if not rec:
        return "(暂无摘要)"
    s = (rec.get("summary") or "").strip()
    one = (rec.get("summary_one_liner") or "").strip()

    if s:
        # 优先取至第一句"。"内的内容; 控制 30-80 字
        m = re.split(r"[。\n]", s, maxsplit=1)
        first = m[0].strip()
        if 30 <= len(first) <= 80:
            return first
        if len(first) > 80:
            # 截到 80 字附近的标点
            cut = first[:80]
            for ch in ("，", "、", "；"):
                k = cut.rfind(ch)
                if k >= 30:
                    return cut[:k]
            return cut
        # first < 30 字: 拼下一段
        joined = first
        rest = s[len(first):].lstrip("。\n")
        for ch in rest:
            joined += ch
            if len(joined) >= 30 and ch in "。，；、":
                break
            if len(joined) >= 80:
                break
        return joined.rstrip("。") if len(joined) >= 30 else (joined or one or "(暂无摘要)")

    if one:
        return one
    return "(暂无摘要)"


def join_issuer(issuer):
    if not issuer:
        return ""
    if isinstance(issuer, str):
        return issuer
    # 已经是字符串里 join 的, 也可能是单元素 list
    return "、".join(x.strip() for x in issuer if x.strip())


def map_level_and_group(region):
    """返回 (level, group_kind, province_code, city_name)"""
    code = (region.get("code") or "").strip()
    name = (region.get("name") or "").strip()
    raw_level = (region.get("level") or "").strip()

    if raw_level == "国家" or code == "000000":
        return ("national", "national", "", "")

    if code in DIRECT_MUNI_CODES:
        return ("municipal", "city", code, DIRECT_MUNI_NAME[code])

    if raw_level == "省":
        return ("provincial", "province", code, "")

    if raw_level == "市":
        if code and len(code) == 6 and code.endswith("00") and code[2:] != "0000":
            # 地级市自身 code (如 慈溪 330282 — 县级市挂浙江省下) 走 PROV_OF_CITY
            pass
        if name in PROV_OF_CITY:
            pc, cn = PROV_OF_CITY[name]
            return ("municipal", "city", pc, cn)
        # fallback: 慈溪 已有 330282 但 name 在表中
        return ("municipal", "city", "", name)

    if raw_level == "区":
        if name in DISTRICT_TO_CITY:
            pc, cn = DISTRICT_TO_CITY[name]
            return ("district", "city", pc, cn)
        return ("district", "city", "", name)

    return ("national", "national", "", "")


def build_topic(theme_dir, theme_zh, summaries):
    inp = json.load(open(ROOT / "2_crystallized" / "themes" / theme_dir / "_input.json"))
    national = []
    by_prov = {}
    by_city = {}

    excluded_count = 0
    for p in inp["policies"]:
        # B7 isolated 过滤:跳过 exclude_from_main_graph 标记的政策
        if p.get("id") in EXCLUDE_PIDS:
            excluded_count += 1
            continue
        item = {
            "title": (p.get("title") or "").strip(),
            "issuingOrg": join_issuer(p.get("issuer")) or "(未知)",
            "issueDate": (p.get("date") or "1900-01-01").strip() or "1900-01-01",
            "summary": shape_summary(summaries.get(p["id"])),
        }
        # date sanity: 若只有年份 YYYY 补 -01-01
        if re.fullmatch(r"\d{4}", item["issueDate"]):
            item["issueDate"] = item["issueDate"] + "-01-01"

        level, kind, pc, cn = map_level_and_group(p.get("region", {}))
        item["level"] = level

        # 重排序字段顺序
        ordered = {
            "title": item["title"],
            "issuingOrg": item["issuingOrg"],
            "issueDate": item["issueDate"],
            "level": item["level"],
            "summary": item["summary"],
        }

        if kind == "national":
            national.append(ordered)
        elif kind == "province":
            grp = by_prov.setdefault(pc, {
                "provinceCode": pc,
                "provinceName": p["region"].get("name", ""),
                "policies": [],
            })
            grp["policies"].append(ordered)
        elif kind == "city":
            key = (pc, cn)
            grp = by_city.setdefault(key, {
                "provinceCode": pc,
                "cityName": cn,
                "policies": [],
            })
            grp["policies"].append(ordered)

    # 排序: 国家级按日期降序, 省按 code, 市按 (province, city), 主题内每组政策按日期降序
    national.sort(key=lambda x: x["issueDate"], reverse=True)
    province_list = sorted(by_prov.values(), key=lambda g: g["provinceCode"])
    for g in province_list:
        g["policies"].sort(key=lambda x: x["issueDate"], reverse=True)
    city_list = sorted(by_city.values(), key=lambda g: (g["provinceCode"], g["cityName"]))
    for g in city_list:
        g["policies"].sort(key=lambda x: x["issueDate"], reverse=True)

    if excluded_count:
        print(f"  [filter] {theme_dir}: 排除 {excluded_count} 个 exclude_from_main_graph 政策")

    return {
        "topic": theme_zh,
        "national": national,
        "byProvince": province_list,
        "byCity": city_list,
    }


def main():
    summaries = load_summaries()
    print(f"[B7 filter] 加载 {len(EXCLUDE_PIDS)} 个 exclude_from_main_graph 政策(读自 _meta/audit/isolated_classification.jsonl)")
    topics = []
    for theme_dir, theme_zh in THEMES:
        topics.append(build_topic(theme_dir, theme_zh, summaries))

    out = {
        "fetchedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "topics": topics,
    }

    out_path = ROOT / "_meta" / "topic_distribution.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))

    # stats
    print(f"Wrote: {out_path}")
    for t in topics:
        n_nat = len(t["national"])
        n_prov = sum(len(g["policies"]) for g in t["byProvince"])
        n_city = sum(len(g["policies"]) for g in t["byCity"])
        total = n_nat + n_prov + n_city
        print(f"  {t['topic']:20s}  national={n_nat:3d}  province={n_prov:3d}({len(t['byProvince'])}省)  city={n_city:3d}({len(t['byCity'])}市)  total={total}")


if __name__ == "__main__":
    main()
