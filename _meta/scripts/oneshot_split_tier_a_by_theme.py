#!/usr/bin/env python3
"""一次性 — 把 tier_a_p0_theme_other_prov.jsonl 790 url 按 P0 主题切成
6 个子批 jsonl,供 P2.7 Tier A.1-A.6 分批 fetch + trigger A 用。

切批策略(handoff 2026-05-07 建议):
  A.1 energy_storage_theme(储能)        — 最大,先校准节奏
  A.2 power_market(电力市场)
  A.3 charging_infra(充电基础设施)
  A.4 distribution_grid_opening(配网开放)
  A.5 v2g + vpp_theme(V2G + 虚拟电厂)   — 合并(跨主题边多)
  A.6 aggregator + green_power + 长尾    — 聚合商 + 绿电 + 居住充电 + 设备更新

每个 url 按"primary theme"(layer_meta 第一个 P0 主题)归批,避免重复 fetch。
若 url 命中多主题,只入第一批,后续批不重复。
"""
import json
from pathlib import Path

VAULT = Path(__file__).resolve().parents[2]
SRC = VAULT / "_meta" / "audit" / "p2_7_remaining" / "tier_a_p0_theme_other_prov.jsonl"
OUT_DIR = VAULT / "_meta" / "audit" / "p2_7_remaining"

# 切批顺序(决定 url 多主题归属)
BATCH_THEMES = [
    ("a1_energy_storage", ["energy_storage_theme"]),
    ("a2_power_market", ["power_market"]),
    ("a3_charging_infra", ["charging_infra", "residential_charging"]),
    ("a4_distribution_grid", ["distribution_grid_opening"]),
    ("a5_v2g_vpp", ["v2g", "vpp_theme"]),
    ("a6_aggregator_green_tail", ["aggregator_access", "green_power_trading_theme",
                                  "equipment_renewal_theme"]),
]


def main():
    rows = []
    with SRC.open(encoding="utf-8") as f:
        for ln in f:
            if ln.strip():
                rows.append(json.loads(ln))
    print(f"src: {len(rows)} url")

    seen_urls = set()
    batches = {name: [] for name, _ in BATCH_THEMES}
    unrouted = []

    for row in rows:
        url = row.get("url", "")
        if url in seen_urls:
            continue
        # 找 primary theme(按 BATCH_THEMES 顺序首中)
        themes_in_row = set()
        for m in row.get("layer_meta") or []:
            if isinstance(m, dict) and m.get("theme_id"):
                themes_in_row.add(m["theme_id"])
        routed = False
        for batch_name, batch_themes in BATCH_THEMES:
            if any(t in themes_in_row for t in batch_themes):
                batches[batch_name].append(row)
                seen_urls.add(url)
                routed = True
                break
        if not routed:
            unrouted.append(row)

    # 写出
    print(f"\n切批结果:")
    for name, items in batches.items():
        out = OUT_DIR / f"{name}.jsonl"
        with out.open("w", encoding="utf-8") as f:
            for row in items:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"  {name}: {len(items):>4} url → {out.name}")

    if unrouted:
        out = OUT_DIR / "a_unrouted.jsonl"
        with out.open("w", encoding="utf-8") as f:
            for row in unrouted:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"  unrouted: {len(unrouted)} → {out.name} (主题不属于任何批,需 review)")

    total_routed = sum(len(v) for v in batches.values())
    print(f"\nrouted total: {total_routed} / {len(rows)} src")
    print(f"unique url after dedup: {len(seen_urls)}")


if __name__ == "__main__":
    main()
