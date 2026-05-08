#!/usr/bin/env python3
"""一次性 — 把 tier_b_other_theme_p0_prov.jsonl 242 url 按 P0 省切 5 批。

按省切批理由(SKILL §A.6.8):同省政府文风一致 → 5C/rel_judge 召回率高;
edge 密度集中在同省。最小两省(江苏 23 + 浙江 13)合并避免太碎。

切批顺序:广东 54 / 上海 51 / 北京 51 / 山东 50 / 江浙 36
"""
import json
from pathlib import Path

VAULT = Path(__file__).resolve().parents[2]
SRC = VAULT / "_meta" / "audit" / "p2_7_remaining" / "tier_b_other_theme_p0_prov.jsonl"
OUT_DIR = VAULT / "_meta" / "audit" / "p2_7_remaining"

BATCH_PROVINCES = [
    ("b1_guangdong", ["440000"]),
    ("b2_shanghai", ["310000"]),
    ("b3_beijing", ["110000"]),
    ("b4_shandong", ["370000"]),
    ("b5_jiangsu_zhejiang", ["320000", "330000"]),
]


def main():
    rows = []
    with SRC.open(encoding="utf-8") as f:
        for ln in f:
            if ln.strip():
                rows.append(json.loads(ln))
    print(f"src: {len(rows)} url")

    seen_urls = set()
    batches = {name: [] for name, _ in BATCH_PROVINCES}
    unrouted = []

    for row in rows:
        url = row.get("url", "")
        if url in seen_urls:
            continue
        provs_in_row = set()
        for m in row.get("layer_meta") or []:
            if isinstance(m, dict) and m.get("province_code"):
                provs_in_row.add(m["province_code"])
        routed = False
        for batch_name, batch_provs in BATCH_PROVINCES:
            if any(p in provs_in_row for p in batch_provs):
                batches[batch_name].append(row)
                seen_urls.add(url)
                routed = True
                break
        if not routed:
            unrouted.append(row)

    print(f"\n切批结果:")
    for name, items in batches.items():
        out = OUT_DIR / f"{name}.jsonl"
        with out.open("w", encoding="utf-8") as f:
            for row in items:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"  {name}: {len(items):>3} url → {out.name}")

    if unrouted:
        out = OUT_DIR / "b_unrouted.jsonl"
        with out.open("w", encoding="utf-8") as f:
            for row in unrouted:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"  unrouted: {len(unrouted)} → {out.name}")

    total = sum(len(v) for v in batches.values())
    print(f"\nrouted: {total} / {len(rows)} src | unique url: {len(seen_urls)}")


if __name__ == "__main__":
    main()
