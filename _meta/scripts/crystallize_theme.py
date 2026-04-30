#!/usr/bin/env python3
"""
crystallize_theme.py
通用主题结晶 — 给定 theme(canonical_id),聚合 V2G/power_market/charging_infra/...:
  1. 准备 theme_input.json(政策、关系、区域、issuer、diff、opinion 全套数据)
  2. 生成 timeline.md(纯数据,不依赖 LLM)
  3. 生成 regional-coverage.md(纯数据,空白发现)
  4. 留 overview.md / opinions-summary.md 给 Agent LLM 跑

用法:
  python3 crystallize_theme.py --theme v2g --aliases V2G,车网互动,车网融合
  python3 crystallize_theme.py --theme power_market --aliases 电力市场,电力交易
  python3 crystallize_theme.py --theme charging_infra --aliases 充电基础设施,充电桩

输出:
  2_crystallized/themes/<theme>/
    ├── timeline.md          (脚本生成)
    ├── regional-coverage.md (脚本生成)
    └── _input.json          (Agent 用)
  _meta/<theme>_theme_input.json  (Agent 用)
"""

import argparse
import json
import re
import yaml
from pathlib import Path
from collections import defaultdict, Counter
from datetime import date

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
POLICIES = VAULT / "0_raw" / "policies"
EXTRACTIONS = VAULT / "1_extracted" / "entities" / "_extractions.jsonl"
RELATIONS = VAULT / "1_extracted" / "relations"
DIFFS = VAULT / "1_extracted" / "diffs"
OPINIONS = VAULT / "1_extracted" / "opinions"
THEMES = VAULT / "2_crystallized" / "themes"
BUSINESS_VIEW = VAULT / "_meta" / "business_view"

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def load_business_view_importance() -> dict:
    """读 _meta/business_view/{pid}.yaml 的「重要性」字段(L1.2 后该字段从 raw 迁到此)。
    返回 {pid: int}。"""
    out = {}
    if not BUSINESS_VIEW.exists():
        return out
    for f in BUSINESS_VIEW.glob("*.yaml"):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            imp = data.get("重要性")
            if imp is not None:
                out[f.stem] = int(imp)
        except (yaml.YAMLError, ValueError, OSError):
            continue
    return out

# 31 省级行政区(用于"空白省份"分析)
ALL_PROVINCES = [
    "北京市", "天津市", "上海市", "重庆市",  # 直辖市
    "河北省", "山西省", "内蒙古自治区",
    "辽宁省", "吉林省", "黑龙江省",
    "江苏省", "浙江省", "安徽省", "福建省", "江西省", "山东省",
    "河南省", "湖北省", "湖南省", "广东省", "广西壮族自治区", "海南省",
    "四川省", "贵州省", "云南省", "西藏自治区",
    "陕西省", "甘肃省", "青海省", "宁夏回族自治区", "新疆维吾尔自治区",
]


def parse_fm(text):
    m = FM_RE.match(text)
    if not m:
        return None, text
    try:
        return yaml.safe_load(m.group(1)) or {}, text[m.end():]
    except yaml.YAMLError:
        return None, text


def collect_theme_data(theme_id, aliases):
    """收集一个主题的所有数据"""
    # 0. 业务侧重要性(L1.2 已从 raw 迁到 _meta/business_view/{pid}.yaml)
    importance_by_pid = load_business_view_importance()

    # 1. 通过 entity 反向找:命中该 canonical 的政策
    pids_via_entity = set()
    with open(EXTRACTIONS, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if d["canonical_id"] == theme_id:
                pids_via_entity.add(d["policy_id"])

    # 2. 通过 tag 找:tag 含 aliases 任一
    pids_via_tag = set()
    all_policies = {}
    for f in sorted(POLICIES.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        fm, _ = parse_fm(text)
        if fm is None:
            continue
        pid = fm.get("id")
        if not pid:
            continue
        all_policies[pid] = (fm, f.name)
        tags = fm.get("tags", []) or []
        for t in tags:
            s = str(t)
            if any(a in s for a in aliases):
                pids_via_tag.add(pid)
                break

    pid_set = pids_via_entity | pids_via_tag

    # 提取政策 meta
    policies = []
    for pid in pid_set:
        if pid not in all_policies:
            continue
        fm, fname = all_policies[pid]
        policies.append({
            "id": pid,
            "title": fm.get("title", ""),
            "date": str(fm.get("date") or ""),
            "official": fm.get("official_number") or "",
            "issuer": fm.get("issuer", []) or [],
            "region": fm.get("region", {}) or {},
            "importance": importance_by_pid.get(pid, fm.get("重要性", 0) or 0),
            "tags": fm.get("tags", []) or [],
            "filename": fname,
        })
    policies.sort(key=lambda p: (p["date"], -p["importance"]))

    # 关系
    relations = []
    for rel in ["supersedes", "references", "clarifies", "iterates", "extends", "aligns_with", "conflicts_with"]:
        path = RELATIONS / f"{rel}.jsonl"
        if not path.exists():
            continue
        for line in open(path, encoding="utf-8"):
            d = json.loads(line)
            if d.get("from") in pid_set or d.get("to") in pid_set:
                relations.append(d)

    # diff
    diff_files = []
    if DIFFS.exists():
        for d in DIFFS.glob("*.md"):
            if any(pid in d.stem for pid in pid_set):
                diff_files.append(d.name)

    # opinion 政策
    opinion_pids = []
    if OPINIONS.exists():
        for op in OPINIONS.glob("P_*.md"):
            if op.stem in pid_set:
                opinion_pids.append(op.stem)

    return policies, relations, diff_files, opinion_pids


def render_timeline(theme_id, theme_zh, policies):
    """按 region.level 分组的时间线"""
    by_level = defaultdict(list)
    for p in policies:
        lvl = (p["region"] or {}).get("level", "未知")
        by_level[lvl].append(p)
    for lvl in by_level:
        by_level[lvl].sort(key=lambda p: p["date"])

    lines = []
    lines.append("---")
    lines.append(f"theme: {theme_id}")
    lines.append(f"theme_name: {theme_zh}")
    lines.append("title: 政策时间线")
    lines.append(f"total_policies: {len(policies)}")
    lines.append(f"generated_at: {date.today().isoformat()}")
    lines.append(f"generated_by: crystallize_theme.py (auto data)")
    lines.append("---")
    lines.append("")
    lines.append(f"# {theme_zh} 政策时间线")
    lines.append("")
    lines.append(f"按行政层级 + 日期排序。仅列**重要性 ≥4** 的政策(全量见 _input.json)。")
    lines.append("")

    for lvl in ["国家", "省", "市", "区"]:
        items = by_level.get(lvl, [])
        if not items:
            continue
        items_top = [p for p in items if p["importance"] >= 4]
        lines.append(f"## {lvl}级({len(items)} 篇,≥4 分 {len(items_top)} 篇)")
        lines.append("")
        for p in items_top:
            issuer = "/".join(p["issuer"]) if p["issuer"] else "?"
            mark = "⭐" * p["importance"]
            on = p["official"] or ""
            on_part = f" [{on}]" if on else ""
            lines.append(f"- **{p['date']}**  {mark}  `{p['id']}`{on_part}")
            lines.append(f"  - {p['title'][:55]}")
            lines.append(f"  - {issuer[:60]}  ·  {p['region'].get('name', '?')}")
        lines.append("")

    # 统计层
    total_imp = sum(p["importance"] for p in policies)
    avg_imp = total_imp / max(1, len(policies))
    high = sum(1 for p in policies if p["importance"] >= 4)
    lines.append("## 时间线观察(自动统计)")
    lines.append("")
    lines.append(f"- 主题总政策数:**{len(policies)}**")
    lines.append(f"- 重要性 ≥4 的政策:**{high}** ({high/max(1,len(policies))*100:.0f}%)")
    lines.append(f"- 平均重要性:**{avg_imp:.2f}**")

    # 高峰年份
    year_count = Counter()
    for p in policies:
        if p["date"]:
            year_count[p["date"][:4]] += 1
    if year_count:
        peak_y, peak_c = year_count.most_common(1)[0]
        lines.append(f"- 政策密集年份:**{peak_y}** ({peak_c} 篇)")
        lines.append(f"- 年度分布:" + " · ".join(f"{y}={c}" for y, c in sorted(year_count.items())))
    lines.append("")

    return "\n".join(lines)


def render_regional_coverage(theme_id, theme_zh, policies):
    """区域覆盖矩阵 + 空白发现"""
    # 按 region.name 聚合(只算省级以上)
    by_region = defaultdict(list)
    for p in policies:
        name = (p["region"] or {}).get("name", "?")
        by_region[name].append(p)

    # 地市级 / 区级 的省份归属(简化:不归属,单列)
    province_level = {}  # 省份 → 政策列表
    city_level = {}
    district_level = {}
    national = []
    for name, ps in by_region.items():
        lvl = (ps[0]["region"] or {}).get("level", "")
        if lvl == "国家":
            national.extend(ps)
        elif lvl == "省" and name in ALL_PROVINCES:
            province_level[name] = ps
        elif lvl == "市":
            city_level[name] = ps
        elif lvl == "区":
            district_level[name] = ps

    lines = []
    lines.append("---")
    lines.append(f"theme: {theme_id}")
    lines.append(f"theme_name: {theme_zh}")
    lines.append("title: 区域覆盖矩阵")
    lines.append(f"generated_at: {date.today().isoformat()}")
    lines.append(f"generated_by: crystallize_theme.py (auto data)")
    lines.append("---")
    lines.append("")
    lines.append(f"# {theme_zh} 区域覆盖矩阵")
    lines.append("")
    lines.append(f"## 覆盖概况")
    lines.append("")
    lines.append(f"- 国家级:**{len(national)}** 篇")
    lines.append(f"- 省级:**{sum(len(v) for v in province_level.values())}** 篇,**{len(province_level)} / 31** 省级行政区(覆盖率 {len(province_level)/31*100:.0f}%)")
    lines.append(f"- 地市级:**{sum(len(v) for v in city_level.values())}** 篇,**{len(city_level)}** 城市")
    lines.append(f"- 区级:**{sum(len(v) for v in district_level.values())}** 篇,**{len(district_level)}** 区(京沪津渝下辖)")
    lines.append("")

    lines.append("## 省级矩阵")
    lines.append("")
    lines.append("| 省份 | 政策数 | ≥4 分数 | 主要 issuer | 最早 | 最近 |")
    lines.append("|------|:----:|:----:|------------|------|------|")
    sorted_provs = sorted(province_level.items(), key=lambda kv: -len(kv[1]))
    for prov, ps in sorted_provs:
        ps_sorted = sorted(ps, key=lambda p: p["date"])
        issuers = Counter()
        for p in ps:
            for iss in (p["issuer"] or []):
                issuers[iss] += 1
        top_iss = issuers.most_common(1)[0][0][:20] if issuers else "?"
        high = sum(1 for p in ps if p["importance"] >= 4)
        earliest = ps_sorted[0]["date"] if ps_sorted else ""
        latest = ps_sorted[-1]["date"] if ps_sorted else ""
        lines.append(f"| {prov} | {len(ps)} | {high} | {top_iss} | {earliest} | {latest} |")
    lines.append("")

    # 空白省份
    covered_provs = set(province_level.keys())
    blank_provs = [p for p in ALL_PROVINCES if p not in covered_provs]
    lines.append(f"## 空白省份(滴滴能源应关注)")
    lines.append("")
    lines.append(f"**{len(blank_provs)} / 31** 省级未出台 {theme_zh} 主题政策:")
    lines.append("")
    # 按地理大区分组
    regions_geo = {
        "东北": ["辽宁省", "吉林省", "黑龙江省"],
        "华北": ["北京市", "天津市", "河北省", "山西省", "内蒙古自治区"],
        "华东": ["上海市", "江苏省", "浙江省", "安徽省", "福建省", "江西省", "山东省"],
        "中南": ["河南省", "湖北省", "湖南省", "广东省", "广西壮族自治区", "海南省"],
        "西南": ["重庆市", "四川省", "贵州省", "云南省", "西藏自治区"],
        "西北": ["陕西省", "甘肃省", "青海省", "宁夏回族自治区", "新疆维吾尔自治区"],
    }
    for geo, provs in regions_geo.items():
        blanks_here = [p for p in provs if p in blank_provs]
        covered_here = [p for p in provs if p not in blank_provs]
        if blanks_here:
            lines.append(f"- **{geo}**:空 {len(blanks_here)}/{len(provs)} → {' / '.join(blanks_here)}  · 已覆盖:{' / '.join(covered_here) if covered_here else '无'}")
        else:
            lines.append(f"- {geo}:全部覆盖 ✅")
    lines.append("")

    # 地市级
    if city_level:
        lines.append("## 地市级覆盖")
        lines.append("")
        lines.append("| 城市 | 政策数 | ≥4 分数 |")
        lines.append("|------|:----:|:----:|")
        for city, ps in sorted(city_level.items(), key=lambda kv: -len(kv[1])):
            high = sum(1 for p in ps if p["importance"] >= 4)
            lines.append(f"| {city} | {len(ps)} | {high} |")
        lines.append("")

    # 区级(京沪津渝)
    if district_level:
        lines.append("## 区级覆盖(京沪津渝下辖区)")
        lines.append("")
        lines.append("| 区 | 政策数 |")
        lines.append("|------|:----:|")
        for dist, ps in sorted(district_level.items(), key=lambda kv: -len(kv[1])):
            lines.append(f"| {dist} | {len(ps)} |")
        lines.append("")

    return "\n".join(lines)


REGISTRY = VAULT / "_meta" / "themes_registry.yaml"


def load_themes_registry() -> list:
    """读 _meta/themes_registry.yaml,返回 [{id, dir_name, zh, aliases}, ...]"""
    if not REGISTRY.exists():
        return []
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8")) or {}
    return data.get("themes", [])


def crystallize_one(theme_id: str, theme_zh: str, aliases: list, dir_name: str = None):
    """跑单主题 — 提到 main 外便于 --all 循环复用"""
    out_dir = THEMES / (dir_name or theme_id.upper())
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Crystallizing theme: {theme_id}({theme_zh})")
    print(f"  aliases: {aliases}")
    policies, relations, diff_files, opinion_pids = collect_theme_data(theme_id, aliases)
    print(f"  政策: {len(policies)}  关系: {len(relations)}  diff: {len(diff_files)}  opinion: {len(opinion_pids)}")

    (out_dir / "timeline.md").write_text(
        render_timeline(theme_id, theme_zh, policies), encoding="utf-8"
    )
    (out_dir / "regional-coverage.md").write_text(
        render_regional_coverage(theme_id, theme_zh, policies), encoding="utf-8"
    )

    region_dist = defaultdict(lambda: defaultdict(int))
    for p in policies:
        lvl = (p["region"] or {}).get("level", "未知")
        name = (p["region"] or {}).get("name", "?")
        region_dist[lvl][name] += 1
    issuer_count = Counter()
    for p in policies:
        for iss in (p.get("issuer") or []):
            issuer_count[iss] += 1

    payload = {
        "theme": theme_id,
        "theme_zh": theme_zh,
        "aliases": aliases,
        "policies": policies,
        "policies_count": len(policies),
        "relations": relations,
        "relations_count": len(relations),
        "diff_files": diff_files,
        "opinion_policy_ids": opinion_pids,
        "region_distribution": {lvl: dict(d) for lvl, d in region_dist.items()},
        "top_issuers": dict(issuer_count.most_common(15)),
        "top_5_importance": sorted(policies, key=lambda p: -p["importance"])[:5],
    }
    input_path = VAULT / "_meta" / f"{theme_id}_theme_input.json"
    input_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "_input.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  → {out_dir}/_input.json")
    print(f"  → {input_path}")
    print("  === Done ===\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", help="canonical_id (如 power_market / charging_infra)")
    ap.add_argument("--aliases", help="逗号分隔(如 '电力市场,电力交易')")
    ap.add_argument("--theme_zh", help="中文展示名(如 '电力市场')")
    ap.add_argument("--all", action="store_true", help="循环跑 _meta/themes_registry.yaml 中全部主题")
    args = ap.parse_args()

    if args.all:
        themes = load_themes_registry()
        if not themes:
            print("[fatal] _meta/themes_registry.yaml 不存在或为空")
            return
        print(f"=== 循环跑 {len(themes)} 主题(from registry)===\n")
        for t in themes:
            crystallize_one(
                theme_id=t["id"],
                theme_zh=t["zh"],
                aliases=t.get("aliases", []),
                dir_name=t.get("dir_name"),
            )
        print(f"=== 全 {len(themes)} 主题完成 ===")
        return

    if not (args.theme and args.aliases and args.theme_zh):
        ap.error("非 --all 模式需 --theme + --aliases + --theme_zh")
    aliases = [a.strip() for a in args.aliases.split(",") if a.strip()]
    crystallize_one(args.theme, args.theme_zh, aliases)
    return

    # ↓↓↓ 旧 main 单条流程已迁到 crystallize_one,以下保留为参考但不可达
    out_dir = THEMES / args.theme.upper()  # 大写以醒目
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Crystallizing theme: {args.theme}({args.theme_zh})")
    print(f"  aliases: {aliases}")
    policies, relations, diff_files, opinion_pids = collect_theme_data(args.theme, aliases)
    print(f"  政策: {len(policies)}")
    print(f"  关系: {len(relations)}")
    print(f"  diff 文件: {len(diff_files)}")
    print(f"  opinion 政策: {len(opinion_pids)}")

    # 写 timeline + regional-coverage(脚本完成,无需 LLM)
    (out_dir / "timeline.md").write_text(
        render_timeline(args.theme, args.theme_zh, policies), encoding="utf-8"
    )
    (out_dir / "regional-coverage.md").write_text(
        render_regional_coverage(args.theme, args.theme_zh, policies), encoding="utf-8"
    )

    # 写 _input.json(给 Agent 跑 overview + opinions-summary)
    region_dist = defaultdict(lambda: defaultdict(int))
    for p in policies:
        lvl = (p["region"] or {}).get("level", "未知")
        name = (p["region"] or {}).get("name", "?")
        region_dist[lvl][name] += 1

    issuer_count = Counter()
    for p in policies:
        for iss in (p.get("issuer") or []):
            issuer_count[iss] += 1

    payload = {
        "theme": args.theme,
        "theme_zh": args.theme_zh,
        "aliases": aliases,
        "policies": policies,
        "policies_count": len(policies),
        "relations": relations,
        "relations_count": len(relations),
        "diff_files": diff_files,
        "opinion_policy_ids": opinion_pids,
        "region_distribution": {lvl: dict(d) for lvl, d in region_dist.items()},
        "top_issuers": dict(issuer_count.most_common(15)),
        "top_5_importance": sorted(policies, key=lambda p: -p["importance"])[:5],
    }
    input_path = VAULT / "_meta" / f"{args.theme}_theme_input.json"
    input_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "_input.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n=== Done ===")
    print(f"  timeline.md → {out_dir / 'timeline.md'}")
    print(f"  regional-coverage.md → {out_dir / 'regional-coverage.md'}")
    print(f"  _input.json → {input_path}")
    print(f"  Agent 接力:overview.md + opinions-summary.md(LLM 必须)")


if __name__ == "__main__":
    main()
