#!/usr/bin/env python3
"""
upgrade_frontmatter_v2_to_v3.py
Step 3 — 把 0_raw/policies/ 下 357 篇 v2 frontmatter 升级到 v3 schema。

v3 字段:id / title / official_number / issuer (数组) / date / region / provenance (嵌套) /
        tags / scores / 重要性 / 行动分类 / 价值标签 / archive (可选)
丢:url, source_type, confidence, collected_by, collected_at, collected_mode (合并到 provenance)
   source (改名 issuer 数组), 文号 (改名 official_number), type (目录隔离不需要),
   related/supersedes/iterates (raw 不写关系)
"""

import re
import json
import hashlib
from pathlib import Path
import yaml

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
POLICIES = VAULT / "0_raw" / "policies"
LOG = VAULT / "_meta" / "step3_upgrade_log.jsonl"

# ============== 机构缩写映射 ==============
ISSUER_MAP = {
    # 中央(精确名,优先匹配)
    "国务院办公厅": "GO", "国办": "GO",
    "中共中央办公厅 国务院办公厅": "CCGO",
    "中共中央办公厅": "CCO",
    "国务院": "SC",
    # 部委
    "国家发展和改革委员会": "NDRC", "国家发展改革委": "NDRC", "国家发改委": "NDRC", "发展改革委": "NDRC",
    "国家能源局": "NEA",
    "工业和信息化部": "MIIT", "工信部": "MIIT",
    "财政部": "MOF",
    "生态环境部": "MEE", "环保部": "MEE",
    "住房和城乡建设部": "MOHURD", "住建部": "MOHURD",
    "国家税务总局": "STA", "税务总局": "STA",
    "中国人民银行": "PBOC",
    "商务部": "MOFCOM",
    "交通运输部": "MOT",
    "国家市场监督管理总局": "SAMR", "市场监管总局": "SAMR",
    "国家金融监督管理总局": "NFRA",
    "中国证券监督管理委员会": "CSRC", "证监会": "CSRC",
    "国家电网有限公司": "SGCC", "国家电网公司": "SGCC", "国家电网": "SGCC",
    "中国南方电网有限责任公司": "CSG", "南方电网": "CSG",
    "国家邮政局": "POST",
    "国家粮食和物资储备局": "GRAIN",
    # 直辖市(只匹配市本级,区级走 fallback)
    "北京市": "BJ", "上海市": "SH", "天津市": "TJ", "重庆市": "CQ",
    # 省份
    "河北省": "HE", "山西省": "SX", "内蒙古自治区": "NM",
    "辽宁省": "LN", "吉林省": "JL", "黑龙江省": "HL",
    "江苏省": "JS", "浙江省": "ZJ", "安徽省": "AH",
    "福建省": "FJ", "江西省": "JX", "山东省": "SD",
    "河南省": "HA", "湖北省": "HB", "湖南省": "HN",
    "广东省": "GD", "广西壮族自治区": "GX", "广西": "GX",
    "海南省": "HI",
    "四川省": "SC2",  # 与"国务院"SC冲突,用 SC2
    "贵州省": "GZ", "云南省": "YN", "西藏自治区": "XZ", "西藏": "XZ",
    "陕西省": "SN", "甘肃省": "GS", "青海省": "QH",
    "宁夏回族自治区": "NX", "宁夏": "NX",
    "新疆维吾尔自治区": "XJ", "新疆": "XJ",
}

# ============== 行政区划代码(省级) ==============
REGION_CODE = {
    "北京市": "110000", "天津市": "120000", "河北省": "130000",
    "山西省": "140000", "内蒙古自治区": "150000",
    "辽宁省": "210000", "吉林省": "220000", "黑龙江省": "230000",
    "上海市": "310000", "江苏省": "320000", "浙江省": "330000",
    "安徽省": "340000", "福建省": "350000", "江西省": "360000",
    "山东省": "370000",
    "河南省": "410000", "湖北省": "420000", "湖南省": "430000",
    "广东省": "440000", "广西壮族自治区": "450000", "海南省": "460000",
    "重庆市": "500000", "四川省": "510000", "贵州省": "520000",
    "云南省": "530000", "西藏自治区": "540000",
    "陕西省": "610000", "甘肃省": "620000", "青海省": "630000",
    "宁夏回族自治区": "640000", "新疆维吾尔自治区": "650000",
}

# 按 issuer_short 输出归类 region
CENTRAL_SHORTS = {"GO", "SC", "CCO", "CCGO",
                  "NDRC", "NEA", "MIIT", "MOF", "MEE", "MOHURD",
                  "STA", "PBOC", "MOFCOM", "MOT", "SAMR", "NFRA",
                  "CSRC", "SGCC", "CSG", "POST", "GRAIN", "NDC",
                  "NDRC_NEA"}
PROV_SHORTS = {"BJ", "SH", "TJ", "CQ",  # 直辖市
               "HE", "SX", "NM", "LN", "JL", "HL",
               "JS", "ZJ", "AH", "FJ", "JX", "SD",
               "HA", "HB", "HN", "GD", "GX", "HI",
               "SC2", "GZ", "YN", "XZ", "SN", "GS",
               "QH", "NX", "XJ"}
SHORT_TO_REGION_NAME = {
    "BJ": "北京市", "SH": "上海市", "TJ": "天津市", "CQ": "重庆市",
    "HE": "河北省", "SX": "山西省", "NM": "内蒙古自治区",
    "LN": "辽宁省", "JL": "吉林省", "HL": "黑龙江省",
    "JS": "江苏省", "ZJ": "浙江省", "AH": "安徽省",
    "FJ": "福建省", "JX": "江西省", "SD": "山东省",
    "HA": "河南省", "HB": "湖北省", "HN": "湖南省",
    "GD": "广东省", "GX": "广西壮族自治区", "HI": "海南省",
    "SC2": "四川省", "GZ": "贵州省", "YN": "云南省",
    "XZ": "西藏自治区", "SN": "陕西省", "GS": "甘肃省",
    "QH": "青海省", "NX": "宁夏回族自治区", "XJ": "新疆维吾尔自治区",
}
PROVINCIAL_PROV_FULL = list(REGION_CODE.keys())
ZHIXIASHI = ["北京", "上海", "天津", "重庆"]

# 直辖市下辖区(京沪津渝)— 简化集合
DISTRICT_KEYWORDS = ["东城区", "西城区", "朝阳区", "丰台区", "石景山区", "海淀区", "门头沟区",
                     "房山区", "通州区", "顺义区", "昌平区", "大兴区", "怀柔区", "平谷区",
                     "密云区", "延庆区",  # 北京 16
                     "黄浦区", "徐汇区", "长宁区", "静安区", "普陀区", "虹口区", "杨浦区",
                     "闵行区", "宝山区", "嘉定区", "浦东新区", "金山区", "松江区", "青浦区",
                     "奉贤区", "崇明区",  # 上海 16
                     "和平区", "河东区", "河西区", "南开区", "河北区", "红桥区", "东丽区",
                     "西青区", "津南区", "北辰区", "武清区", "宝坻区", "滨海新区", "宁河区",
                     "静海区", "蓟州区",  # 天津 16
                     "万州区", "涪陵区", "渝中区", "大渡口区", "江北区", "沙坪坝区", "九龙坡区",
                     "南岸区", "北碚区", "綦江区", "大足区", "渝北区", "巴南区", "黔江区",
                     "长寿区", "江津区", "合川区", "永川区", "南川区", "璧山区", "铜梁区",
                     "潼南区", "荣昌区", "开州区", "梁平区", "武隆区"]  # 重庆


FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

def parse_frontmatter(text):
    """切 frontmatter 与正文,返回 (fm dict, body str)。
    用 regex 精确匹配开头的 frontmatter 块,内容里的 --- 不会误匹配。"""
    m = FM_RE.match(text)
    if not m:
        return None, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None, text
    body = text[m.end():]
    return fm, body


def issuer_short(source):
    if not source:
        return "UNK"
    src = str(source).strip()
    # 精确匹配优先
    if src in ISSUER_MAP:
        return ISSUER_MAP[src]
    # 包含匹配:按"出现位置最早 + 最长"优先(主发文机构通常排第一)
    hits = []
    for k in ISSUER_MAP.keys():
        idx = src.find(k)
        if idx >= 0:
            hits.append((idx, -len(k), k))  # 位置升序 + 长度降序
    if hits:
        hits.sort()
        return ISSUER_MAP[hits[0][2]]
    # 兜底:hash 前 4 位大写
    return "OTHER" + hashlib.sha256(src.encode("utf-8")).hexdigest()[:4].upper()


def extract_num_from_official(official):
    if not official:
        return None
    s = str(official)
    m = re.search(r"〔\s*\d{4}\s*〕\s*(\d+)\s*号", s)
    if m:
        return m.group(1)
    m = re.search(r"\(\s*\d{4}\s*\)\s*(\d+)\s*号", s)
    if m:
        return m.group(1)
    m = re.search(r"第?(\d+)号", s)
    if m:
        return m.group(1)
    return None


def gen_id(fm):
    """P_<year>_<issuer>_<num_or_dateHash>"""
    year = "0000"
    date = fm.get("date")
    if date:
        m = re.match(r"(\d{4})", str(date))
        if m:
            year = m.group(1)

    src = fm.get("source", "")
    issuer = issuer_short(src)

    official = fm.get("文号", "") or ""
    num = extract_num_from_official(official)
    if num:
        return f"P_{year}_{issuer}_{num}"
    # 兜底:date(MMDD) + title hash 4
    date_compact = "0000"
    if date:
        m = re.match(r"\d{4}-(\d{2})-(\d{2})", str(date))
        if m:
            date_compact = m.group(1) + m.group(2)
    title = fm.get("title", "") or ""
    h = hashlib.sha256(title.encode("utf-8")).hexdigest()[:4]
    return f"P_{year}_{issuer}_{date_compact}{h}"


def detect_region(source):
    """从 source 推 region {level, code, name},以 issuer_short 为主路由"""
    if not source:
        return {"level": "未知", "code": "999999", "name": "未知"}
    src = str(source).strip()
    short = issuer_short(src)

    # 1. issuer 缩写命中中央集合
    if short in CENTRAL_SHORTS:
        return {"level": "国家", "code": "000000", "name": "全国"}

    # 2. issuer 缩写命中省级集合(直辖市本级或省份)
    if short in PROV_SHORTS:
        prov_name = SHORT_TO_REGION_NAME.get(short, "")
        # 进一步看是否是直辖市下辖区(source 含具体区名)
        if short in {"BJ", "SH", "TJ", "CQ"}:
            for d in DISTRICT_KEYWORDS:
                if d in src:
                    return {"level": "区", "code": "", "name": f"{prov_name}{d}"}
        return {"level": "省", "code": REGION_CODE.get(prov_name, ""), "name": prov_name}

    # 3. OTHER_*:从 source 字面再判一次
    # 3a. 直辖市下辖区
    for d in DISTRICT_KEYWORDS:
        if d in src:
            for city in ZHIXIASHI:
                if city in src:
                    return {"level": "区", "code": "", "name": f"{city}市{d}"}
            return {"level": "区", "code": "", "name": d}

    # 3b. 市级(找"X市"模式)
    m = re.search(r"([一-龥]{2,8}市)", src)
    if m:
        return {"level": "市", "code": "", "name": m.group(1)}

    # 3c. 县/区
    m = re.search(r"([一-龥]{2,8}[县区])", src)
    if m:
        return {"level": "区", "code": "", "name": m.group(1)}

    return {"level": "未知", "code": "999999", "name": src[:8]}


def upgrade_provenance(fm):
    """整理为嵌套 dict"""
    old_prov = fm.get("provenance", "")
    fetched_via = "firecrawl"
    if isinstance(old_prov, str):
        if "trafilatura" in old_prov:
            fetched_via = "tavily+trafilatura"
        elif "firecrawl" in old_prov:
            fetched_via = "firecrawl"
        elif old_prov:
            fetched_via = old_prov.split("+")[0]

    return {
        "url": fm.get("url", "") or "",
        "source_type": fm.get("source_type", "") or "",
        "fetched_via": fetched_via,
        "fetched_at": str(fm.get("collected_at", "") or ""),
        "collected_by": fm.get("collected_by", "policy-watch"),
        "collected_mode": fm.get("collected_mode", "build-phase-manual"),
        "confidence": fm.get("confidence", 0.0),
    }


def upgrade_frontmatter(fm):
    new = {}
    new["id"] = gen_id(fm)
    new["title"] = fm.get("title", "")
    new["official_number"] = fm.get("文号", "") or ""
    src = fm.get("source", "")
    new["issuer"] = [src] if src else []
    new["date"] = str(fm.get("date", "")) if fm.get("date") else ""
    new["region"] = detect_region(src)
    new["provenance"] = upgrade_provenance(fm)
    new["tags"] = fm.get("tags", []) or []
    new["scores"] = fm.get("scores", {}) or {}
    new["重要性"] = fm.get("重要性", 0)
    new["行动分类"] = fm.get("行动分类", "") or ""
    new["价值标签"] = fm.get("价值标签", []) or []
    if fm.get("archive"):
        new["archive"] = fm["archive"]
    return new


def dump_frontmatter(fm):
    return yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)


def upgrade_file(path):
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    if fm is None:
        return {"path": path.name, "ok": False, "error": "no_frontmatter"}

    # 幂等:已是 v3 格式(有 id + provenance dict)→ 跳过升级,返回现有 id
    if "id" in fm and isinstance(fm.get("provenance"), dict):
        return {
            "path": path.name,
            "ok": True,
            "id": fm["id"],
            "region_level": (fm.get("region") or {}).get("level", "未知"),
            "issuer_short": fm["id"].split("_")[2] if fm["id"].count("_") >= 2 else "?",
            "skipped": True,
        }

    try:
        new_fm = upgrade_frontmatter(fm)
        new_text = "---\n" + dump_frontmatter(new_fm) + "---\n" + body
        path.write_text(new_text, encoding="utf-8")
        return {
            "path": path.name,
            "ok": True,
            "id": new_fm["id"],
            "region_level": new_fm["region"]["level"],
            "issuer_short": new_fm["id"].split("_")[2] if new_fm["id"].count("_") >= 2 else "?",
            "skipped": False,
        }
    except Exception as e:
        return {"path": path.name, "ok": False, "error": repr(e)}


def resolve_id_collisions(id_map, log):
    """对碰撞 id,按文件名字典序加后缀 _a/_b/_c... 物理唯一化"""
    fixed = 0
    for pid, paths in id_map.items():
        if len(paths) <= 1:
            continue
        paths_sorted = sorted(paths)
        for i, pname in enumerate(paths_sorted):
            suffix = chr(ord('a') + i)  # a/b/c/d ...
            new_id = f"{pid}_{suffix}"
            fpath = POLICIES / pname
            text = fpath.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(text)
            if fm is None:
                continue
            fm["id"] = new_id
            new_text = "---\n" + dump_frontmatter(fm) + "---\n" + body
            fpath.write_text(new_text, encoding="utf-8")
            fixed += 1
            log.write(json.dumps({"action": "id_suffix", "old_id": pid, "new_id": new_id, "path": pname}, ensure_ascii=False) + "\n")
    return fixed


def main():
    files = sorted(POLICIES.glob("*.md"))
    print(f"Total: {len(files)} policies")

    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "w", encoding="utf-8") as logf:
        ok = 0
        fail = 0
        skipped = 0
        id_map = {}
        region_count = {}
        for f in files:
            r = upgrade_file(f)
            logf.write(json.dumps(r, ensure_ascii=False) + "\n")
            if r.get("ok"):
                ok += 1
                if r.get("skipped"):
                    skipped += 1
                pid = r["id"]
                id_map.setdefault(pid, []).append(r["path"])
                rl = r["region_level"]
                region_count[rl] = region_count.get(rl, 0) + 1
            else:
                fail += 1

        # 处理 id 碰撞
        dups = {k: v for k, v in id_map.items() if len(v) > 1}
        fixed = resolve_id_collisions(dups, logf) if dups else 0

    print(f"OK: {ok} (skipped {skipped})  FAIL: {fail}")
    print(f"\nRegion 分布:")
    for k, v in sorted(region_count.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v}")

    print(f"\nID 碰撞: {len(dups)} 组,加后缀化 {fixed} 文件")
    for k, v in list(dups.items())[:5]:
        print(f"  {k} -> {len(v)} 篇 (suffix _a/_b/...)")

    print(f"\nLog: {LOG}")


if __name__ == "__main__":
    main()
