#!/usr/bin/env python3
"""
gen_daily_queries: 基于 coverage_matrix 稀疏度选 50 cells 各 1 query

逻辑(B1.5 — 升级 policy-watch 从固定 51 query → 主题×省矩阵 daily):
- 读 _meta/audit_2026-05-06/coverage_matrix.json(weekly_audit 产)
- 找 13 主题 × 31 省矩阵中**覆盖度最低的 50 cells**(优先 0 命中)
- P0 主题(VPP/储能/电力市场/V2G/聚合商/配电网) cells 加权
- P0 省(京沪苏浙粤鲁) cells 加权
- 生成 50 query plan,写到 _l2_rebuild_state/daily_queries/daily_<date>.jsonl

不调 Tavily API — 只生成 query plan。后续接 run_tavily_matrix.py 调 API。

cron 接入:每天 6:00 跑(launchd / cron)。
"""
from __future__ import annotations
import json
import sys
from datetime import datetime
from pathlib import Path

import yaml

VAULT = Path(__file__).resolve().parent.parent.parent
AUDIT_DIR = VAULT / "_meta" / "audit_2026-05-06"
COV_PATH = AUDIT_DIR / "coverage_matrix.json"
THEMES_PATH = AUDIT_DIR / "themes_13.yaml"
CITIES_PATH = AUDIT_DIR / "target_cities.yaml"

OUT_DIR = VAULT / "_l2_rebuild_state" / "daily_queries"
OUT_DIR.mkdir(parents=True, exist_ok=True)

NOW = datetime.now()
NOW_DATE = NOW.strftime("%Y-%m-%d")
NOW_ISO = NOW.strftime("%Y-%m-%dT%H:%M:%S+08:00")

P0_THEMES = {"vpp_theme", "energy_storage_theme", "power_market", "v2g",
             "aggregator_access", "distribution_grid_opening"}
P0_PROVINCES = {"110000", "310000", "320000", "330000", "440000", "370000"}

# 省级发改委站点(同 gen_tavily_queries.py)
PROV_DRC_SITES = {
    "110000": ["fgw.beijing.gov.cn"], "120000": ["fzgg.tj.gov.cn"],
    "130000": ["hbdrc.hebei.gov.cn"], "140000": ["fgw.shanxi.gov.cn"],
    "150000": ["fgw.nmg.gov.cn"], "210000": ["fgw.ln.gov.cn"],
    "220000": ["fzggw.jl.gov.cn"], "230000": ["drc.hlj.gov.cn"],
    "310000": ["fgw.sh.gov.cn"], "320000": ["fzggw.jiangsu.gov.cn"],
    "330000": ["fzggw.zj.gov.cn"], "340000": ["fzggw.ah.gov.cn"],
    "350000": ["fgw.fujian.gov.cn"], "360000": ["drc.jiangxi.gov.cn"],
    "370000": ["fgw.shandong.gov.cn"], "410000": ["fgw.henan.gov.cn"],
    "420000": ["fgw.hubei.gov.cn"], "430000": ["fgw.hunan.gov.cn"],
    "440000": ["drc.gd.gov.cn"], "450000": ["fgw.gxzf.gov.cn"],
    "460000": ["plan.hainan.gov.cn"], "500000": ["fzggw.cq.gov.cn"],
    "510000": ["fgw.sc.gov.cn"], "520000": ["fgw.guizhou.gov.cn"],
    "530000": ["yndrc.yn.gov.cn"], "540000": ["xzdrc.xizang.gov.cn"],
    "610000": ["sndrc.shaanxi.gov.cn"], "620000": ["fzgg.gansu.gov.cn"],
    "630000": ["fgw.qinghai.gov.cn"], "640000": ["fzggw.nx.gov.cn"],
    "650000": []
}

DAILY_TARGET = 50  # 每天 query 数


def main() -> int:
    if not COV_PATH.exists():
        print(f"[fatal] 缺 {COV_PATH} — 先跑 weekly_audit.py(生成 coverage_matrix.json)")
        return 1

    cov = json.loads(COV_PATH.read_text(encoding="utf-8"))
    themes = yaml.safe_load(THEMES_PATH.read_text(encoding="utf-8"))["themes"]
    theme_by_id = {t["id"]: t for t in themes}

    # 31 省
    provinces = []
    for code, sites in PROV_DRC_SITES.items():
        provinces.append({"code": code, "sites": sites})

    # 列所有 cell + 当前命中数
    cells = []
    for th in themes:
        th_cov = cov.get(th["id"], {})
        for prov in provinces:
            n = th_cov.get(prov["code"], 0)
            # weight: 0 命中 + P0 主题 + P0 省 → 高优
            weight = 0
            weight += (10 if n == 0 else max(0, 5 - n))  # 越稀越加分
            if th["id"] in P0_THEMES:
                weight += 3
            if prov["code"] in P0_PROVINCES:
                weight += 2
            cells.append({
                "theme_id": th["id"],
                "theme_zh": th["zh"],
                "aliases": th.get("aliases", []),
                "province_code": prov["code"],
                "province_sites": prov["sites"],
                "n_current": n,
                "weight": weight,
            })

    # 选 weight 最高的 DAILY_TARGET 个
    cells.sort(key=lambda c: -c["weight"])
    selected = cells[:DAILY_TARGET]

    # 生成 query plan
    queries = []
    for i, c in enumerate(selected, 1):
        primary = c["theme_zh"]
        secondary = c["aliases"][0] if c["aliases"] else primary
        # 省名映射
        prov_name_map = {  # 简化省码→名,完整列表可放 target_cities.yaml
            "110000": "北京", "120000": "天津", "130000": "河北", "140000": "山西",
            "150000": "内蒙古", "210000": "辽宁", "220000": "吉林", "230000": "黑龙江",
            "310000": "上海", "320000": "江苏", "330000": "浙江", "340000": "安徽",
            "350000": "福建", "360000": "江西", "370000": "山东", "410000": "河南",
            "420000": "湖北", "430000": "湖南", "440000": "广东", "450000": "广西",
            "460000": "海南", "500000": "重庆", "510000": "四川", "520000": "贵州",
            "530000": "云南", "540000": "西藏", "610000": "陕西", "620000": "甘肃",
            "630000": "青海", "640000": "宁夏", "650000": "新疆",
        }
        prov_name = prov_name_map.get(c["province_code"], c["province_code"])
        queries.append({
            "qid": f"DAILY_{NOW_DATE}_{i:03d}",
            "generated_at": NOW_ISO,
            "theme_id": c["theme_id"],
            "theme_zh": c["theme_zh"],
            "province_code": c["province_code"],
            "province_name": prov_name,
            "current_coverage": c["n_current"],
            "weight": c["weight"],
            "query_text": f"{prov_name} {primary} OR {secondary} 实施意见 OR 通知",
            "include_domains": c["province_sites"] or None,
            "time_window": "近12月",  # daily 关注新政策,窗口比 weekly 矩阵紧
            "max_results": 8,
        })

    out_path = OUT_DIR / f"daily_{NOW_DATE}.jsonl"
    out_path.write_text(
        "\n".join(json.dumps(q, ensure_ascii=False) for q in queries) + "\n",
        encoding="utf-8"
    )
    print(f"✓ 生成 {len(queries)} daily query → {out_path}")

    # 统计
    print("\n按主题分布:")
    by_theme = {}
    for q in queries:
        by_theme[q["theme_zh"]] = by_theme.get(q["theme_zh"], 0) + 1
    for k, v in sorted(by_theme.items(), key=lambda x: -x[1])[:8]:
        print(f"  {k}: {v}")
    print("\n按省分布(top 10):")
    by_prov = {}
    for q in queries:
        by_prov[q["province_name"]] = by_prov.get(q["province_name"], 0) + 1
    for k, v in sorted(by_prov.items(), key=lambda x: -x[1])[:10]:
        print(f"  {k}: {v}")
    print(f"\n下一步:接 Tavily API arm(配 API key 后):")
    print(f"  python3 _meta/audit_2026-05-06/run_tavily_matrix.py --queries {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
