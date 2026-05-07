#!/usr/bin/env python3
"""一次性 — 把 candidates_rest.jsonl 1696 url 中扣除 p0_refetch_seeds R3
(P0×P0 已立项)的 ~1373 url,按 3 层重要性分到 jsonl + 写 index.md

3 层:
  A. P0 主题 × 非 P0 省/national(790)— 最优先,P0 主题在跨省覆盖
  B. 非 P0 主题 × P0 省(242)— 重点省非主战场主题
  C. 长尾(341)— 非 P0 主题 × 非 P0 省
"""
import json
from collections import defaultdict, Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

VAULT = Path(__file__).resolve().parents[2]
AUDIT = VAULT / "_meta" / "audit_2026-05-06"
OUT_DIR = VAULT / "_meta" / "audit" / "p2_7_remaining"

P0_THEMES = {"v2g", "vpp_theme", "charging_infra", "power_market",
             "energy_storage_theme", "aggregator_access",
             "distribution_grid_opening", "green_power_trading_theme"}
P0_PROVS = {"110000", "310000", "320000", "330000", "370000", "440000"}
PROV_NAMES = {"110000": "北京", "310000": "上海", "320000": "江苏", "330000": "浙江",
              "370000": "山东", "440000": "广东"}

THEME_ZH = {
    "v2g": "V2G", "vpp_theme": "虚拟电厂", "charging_infra": "充电基础设施",
    "power_market": "电力市场", "energy_storage_theme": "新型储能",
    "aggregator_access": "聚合商接入", "distribution_grid_opening": "配电网开放",
    "green_power_trading_theme": "绿电交易",
    "carbon_market_theme": "碳市场", "equipment_renewal_theme": "设备更新",
    "gas_station_transition_theme": "加油站转型",
    "petroleum_retail_compliance": "成品油零售合规",
    "residential_charging": "居住充电",
}


def load_jsonl(p):
    out = []
    for ln in Path(p).read_text(encoding="utf-8", errors="ignore").splitlines():
        if not ln.strip():
            continue
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            pass
    return out


def in_p0_x_p0(c):
    for m in c.get("layer_meta") or []:
        if not isinstance(m, dict):
            continue
        if m.get("theme_id") in P0_THEMES and m.get("province_code") in P0_PROVS:
            return True
    return False


def stratify(c):
    """A / B / C / D"""
    has_p0_theme = has_p0_prov = has_any_theme = False
    for m in c.get("layer_meta") or []:
        if not isinstance(m, dict):
            continue
        if m.get("theme_id"):
            has_any_theme = True
            if m["theme_id"] in P0_THEMES:
                has_p0_theme = True
        if m.get("province_code") in P0_PROVS:
            has_p0_prov = True
    if not has_any_theme:
        return "D"
    if has_p0_theme:
        return "A"
    if has_p0_prov:
        return "B"
    return "C"


def cn_now_iso():
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def main():
    rest = load_jsonl(AUDIT / "candidates_rest.jsonl")
    print(f"candidates_rest 总: {len(rest)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    tiers = {"A": [], "B": [], "C": [], "D": []}
    p0_x_p0_skipped = 0
    for c in rest:
        if in_p0_x_p0(c):
            p0_x_p0_skipped += 1  # 已在 p0_refetch_seeds R3
            continue
        tiers[stratify(c)].append(c)

    # 写 jsonl
    for k, items in tiers.items():
        if not items:
            continue
        fn = {
            "A": "tier_a_p0_theme_other_prov.jsonl",
            "B": "tier_b_other_theme_p0_prov.jsonl",
            "C": "tier_c_long_tail.jsonl",
            "D": "tier_d_no_theme.jsonl",
        }[k]
        with (OUT_DIR / fn).open("w", encoding="utf-8") as f:
            for c in items:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        print(f"  Tier {k}: {len(items)} → {fn}")

    # 主题/省份分布(给 index.md 用)
    def theme_dist(items):
        cnt = Counter()
        for c in items:
            for m in c.get("layer_meta") or []:
                if isinstance(m, dict) and m.get("theme_id"):
                    cnt[m["theme_id"]] += 1
                    break
        return cnt

    def prov_dist(items):
        cnt = Counter()
        for c in items:
            for m in c.get("layer_meta") or []:
                if isinstance(m, dict) and m.get("province_code"):
                    cnt[m["province_code"]] += 1
                    break
        return cnt

    a_themes = theme_dist(tiers["A"])
    b_provs = prov_dist(tiers["B"])

    # 写 index.md
    lines = []
    lines.append("---")
    lines.append("title: P2.7 剩余候选(扣除 p0_refetch_seeds R3 已立项)")
    lines.append(f"generated_at: {cn_now_iso()}")
    lines.append("generated_by: _meta/scripts/oneshot_build_p2_7_remaining.py")
    lines.append(f"total_remaining: {sum(len(v) for v in tiers.values())}")
    lines.append(f"p0_x_p0_already_in_p0_refetch_seeds: {p0_x_p0_skipped}")
    lines.append("---")
    lines.append("")
    lines.append("# P2.7 剩余候选 — 分层立项")
    lines.append("")
    lines.append(f"**总**: {sum(len(v) for v in tiers.values())} url")
    lines.append("(扣除已在 `_meta/audit/p0_refetch_seeds.md` R3 中的 P0 主题×P0 省 "
                 f"{p0_x_p0_skipped} url 后)")
    lines.append("")
    lines.append("## 分层概览")
    lines.append("")
    lines.append("| Tier | 描述 | 数量 | 文件 | 优先级 |")
    lines.append("|---|---|---:|---|---|")
    lines.append(f"| **A** | P0 主题 × 非 P0 省 / national | {len(tiers['A'])} | "
                 f"`tier_a_p0_theme_other_prov.jsonl` | **高**(P0 内容,跨省补全) |")
    lines.append(f"| **B** | 非 P0 主题 × P0 省 | {len(tiers['B'])} | "
                 f"`tier_b_other_theme_p0_prov.jsonl` | 中(京沪苏浙鲁粤的碳市场/设备更新等) |")
    lines.append(f"| **C** | 非 P0 主题 × 非 P0 省 | {len(tiers['C'])} | "
                 f"`tier_c_long_tail.jsonl` | 低(长尾) |")
    if tiers["D"]:
        lines.append(f"| D | layer_meta 无 theme | {len(tiers['D'])} | "
                     f"`tier_d_no_theme.jsonl` | citation 抽到 |")
    lines.append("")

    lines.append("## Tier A 主题分布(790 P0 主题候选,跨非 P0 省)")
    lines.append("")
    lines.append("| theme | 候选数 |")
    lines.append("|---|---:|")
    for t, n in a_themes.most_common():
        lines.append(f"| {THEME_ZH.get(t, t)} | {n} |")
    lines.append("")

    lines.append("## Tier B 省份分布(242 非 P0 主题在 P0 省)")
    lines.append("")
    lines.append("| province | 候选数 |")
    lines.append("|---|---:|")
    for p, n in b_provs.most_common():
        lines.append(f"| {PROV_NAMES.get(p, p)} | {n} |")
    lines.append("")

    lines.append("## 执行建议")
    lines.append("")
    lines.append("1. **先做 p0_refetch_seeds R3 / R2**(已立项,323 url,P0×P0,见独立文件)")
    lines.append("2. **再做 Tier A**(790)— 分批 fetch + trigger A:")
    lines.append("   ```bash")
    lines.append("   python3 _meta/audit_2026-05-06/fetch_candidates.py \\")
    lines.append("     --in _meta/audit/p2_7_remaining/tier_a_p0_theme_other_prov.jsonl \\")
    lines.append("     --log _meta/audit_2026-05-06/fetch_p2_7_a.log \\")
    lines.append("     --concurrency 8")
    lines.append("   # → normalize_to_raw + trigger A.1 prepare 派 5C / rel_judge subagent")
    lines.append("   ```")
    lines.append("   按主题切批(每主题 ~100-140 url),每批走完整 trigger A 流程")
    lines.append("   (~1-2 小时 LLM)")
    lines.append("3. **Tier B**(242)— 同上,按省切批")
    lines.append("4. **Tier C**(341)— 长尾,可走 daily_query 自动重抓而非一次性")
    lines.append("")
    lines.append("## 关联文件")
    lines.append("")
    lines.append("- `_meta/audit/p0_refetch_seeds.md` — P0×P0 优先,323 url(本清单不重复)")
    lines.append("- `_meta/audit/missing_base_policies.md` — 53 base pid commentary 引用断")
    lines.append("- `_meta/audit/p0_gaps_diagnosis.md` — R0-R4 漏抓机制诊断")
    lines.append("- SKILL §A.6 — P0 漏抓诊断 + 重抓协议")
    lines.append("")

    (OUT_DIR / "index.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote: {OUT_DIR.relative_to(VAULT)}/index.md")


if __name__ == "__main__":
    main()
