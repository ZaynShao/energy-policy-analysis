#!/usr/bin/env python3
"""
Tavily 矩阵 query 生成器(轻量,不调用 API)
输出: tavily_queries.jsonl,每行一个 query 计划

设计原则:
  - 三层矩阵: 主题 × (省份 + 重点地市) × 时间窗口
  - 优先级 P0/P1/P2 阶梯,P0 全跑,P1 重点跑,P2 抽样跑
  - 每 query 含: query 文本 / include_domains / 时间窗口 / 期望命中数(用于 47min 后 Tavily 直接调用)

时间窗口策略:
  - 近 24 个月(2024-05 起) — 最重要的政策都在这窗口
  - 近 24-36 个月(2023-05 - 2024-04) — 第二批
  - 36+ 月(2020-2023-04) — 兜底,只对国家级和重要省级跑
"""
import json
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR = Path(__file__).resolve().parent

# 候选省级发改委站点(从渠道目录第二段抓回来)
PROV_DRC_SITES = {
    "110000": ["fgw.beijing.gov.cn"],
    "120000": ["fzgg.tj.gov.cn"],
    "130000": ["hbdrc.hebei.gov.cn"],
    "140000": ["fgw.shanxi.gov.cn"],
    "150000": ["fgw.nmg.gov.cn"],
    "210000": ["fgw.ln.gov.cn"],
    "220000": ["fzggw.jl.gov.cn"],
    "230000": ["drc.hlj.gov.cn"],
    "310000": ["fgw.sh.gov.cn"],
    "320000": ["fzggw.jiangsu.gov.cn"],
    "330000": ["fzggw.zj.gov.cn"],
    "340000": ["fzggw.ah.gov.cn"],
    "350000": ["fgw.fujian.gov.cn"],
    "360000": ["drc.jiangxi.gov.cn"],
    "370000": ["fgw.shandong.gov.cn"],
    "410000": ["fgw.henan.gov.cn"],
    "420000": ["fgw.hubei.gov.cn"],
    "430000": ["fgw.hunan.gov.cn"],
    "440000": ["drc.gd.gov.cn"],
    "450000": ["fgw.gxzf.gov.cn"],
    "460000": ["plan.hainan.gov.cn"],
    "500000": ["fzggw.cq.gov.cn"],
    "510000": ["fgw.sc.gov.cn"],
    "520000": ["fgw.guizhou.gov.cn"],
    "530000": ["yndrc.yn.gov.cn"],
    "540000": ["xzdrc.xizang.gov.cn"],
    "610000": ["sndrc.shaanxi.gov.cn"],
    "620000": ["fzgg.gansu.gov.cn"],
    "630000": ["fgw.qinghai.gov.cn"],
    "640000": ["fzggw.nx.gov.cn"],
    "650000": []  # 新疆候选未列
}
# 各省能源局(P0/P1 主题强相关)
PROV_ENERGY_SITES = {
    "320000": ["nyj.jiangsu.gov.cn"],
    "330000": ["zjnyj.zj.gov.cn"],
    "440000": ["drc.gd.gov.cn"],  # 广东由 drc 兼能源
    "370000": ["nyj.shandong.gov.cn"],  # 已在缺口列表
    "350000": ["fgw.fujian.gov.cn"],
}

# 中央部委(必收)
NATIONAL_SITES = [
    "www.gov.cn", "www.ndrc.gov.cn", "www.nea.gov.cn",
    "www.miit.gov.cn", "www.mofcom.gov.cn", "www.mof.gov.cn",
    "www.mohurd.gov.cn", "www.mee.gov.cn",
    "zfxxgk.nea.gov.cn", "zfxxgk.ndrc.gov.cn",
]


def load_themes():
    return yaml.safe_load(open(AUDIT_DIR / "themes_13.yaml"))["themes"]


def load_target_cities():
    return yaml.safe_load(open(AUDIT_DIR / "target_cities.yaml"))


def get_priority_tier(theme_id):
    cfg = yaml.safe_load(open(AUDIT_DIR / "themes_13.yaml"))
    pri = cfg.get("priority_tiers", {})
    if theme_id in pri.get("P0_critical", []): return "P0"
    if theme_id in pri.get("P1_important", []): return "P1"
    if theme_id in pri.get("P2_supportive", []): return "P2"
    return "P2"


def main():
    themes = load_themes()
    tc = load_target_cities()

    queries = []
    qid = 0

    # ========== Layer 1: 国家级 × 13 主题 ==========
    for th in themes:
        primary_alias = th["zh"]
        secondary = th["aliases"][0] if th["aliases"] else primary_alias
        qid += 1
        queries.append({
            "qid": f"NAT_{qid:04d}",
            "layer": "national",
            "theme_id": th["id"],
            "theme_zh": th["zh"],
            "tier": get_priority_tier(th["id"]),
            "query_text": f"{primary_alias} {secondary} 实施意见 OR 通知 OR 方案",
            "include_domains": NATIONAL_SITES,
            "time_window": "近24月",
            "max_results": 15,
            "purpose": "中央部委政策最新版"
        })

    # ========== Layer 2: 13 主题 × 31 省 ==========
    for th in themes:
        tier = get_priority_tier(th["id"])
        for prov in tc["provinces"]:
            # P0 主题全跑;P1 主题对 P0/P1 省份跑;P2 主题对 P0 省份跑
            prov_pri = prov["priority"]
            if tier == "P0":
                pass  # 全跑
            elif tier == "P1" and prov_pri in ("P0", "P1"):
                pass
            elif tier == "P2" and prov_pri == "P0":
                pass
            else:
                continue

            sites = PROV_DRC_SITES.get(prov["code"], [])
            sites += PROV_ENERGY_SITES.get(prov["code"], [])
            primary_alias = th["zh"]
            secondary = th["aliases"][0] if th["aliases"] else primary_alias

            qid += 1
            queries.append({
                "qid": f"PROV_{qid:04d}",
                "layer": "provincial",
                "theme_id": th["id"],
                "theme_zh": th["zh"],
                "tier": tier,
                "province_code": prov["code"],
                "province_name": prov["name"],
                "query_text": f"{prov['name']} {primary_alias} OR {secondary}",
                "include_domains": sites if sites else None,
                "time_window": "近24月",
                "max_results": 10,
                "purpose": f"{prov['name']}{th['zh']}省级政策"
            })

    # ========== Layer 3: 重点地市 × 主题 ==========
    for th in themes:
        cities_raw = tc["target_cities_by_theme"].get(th["id"], {})
        if not cities_raw:
            continue
        # 处理 inherit_from
        if isinstance(cities_raw, dict) and "inherit_from" in cities_raw:
            cities_raw = tc["target_cities_by_theme"].get(cities_raw["inherit_from"], {})
        # cities_raw 可能是 dict {pilot_cities_first_batch: [...], extended: [...]} 或 {target: [...]}
        cities = []
        if isinstance(cities_raw, dict):
            for k, v in cities_raw.items():
                if isinstance(v, list):
                    cities.extend(v)
        elif isinstance(cities_raw, list):
            cities = cities_raw

        for city in cities:
            qid += 1
            primary_alias = th["zh"]
            queries.append({
                "qid": f"CITY_{qid:04d}",
                "layer": "municipal",
                "theme_id": th["id"],
                "theme_zh": th["zh"],
                "tier": get_priority_tier(th["id"]),
                "province_code": city.get("code", "")[:2] + "0000",
                "city_name": city["name"],
                "city_role": city.get("role", ""),
                "query_text": f"{city['name']} {primary_alias} 试点 OR 方案 OR 通知",
                "include_domains": None,  # 市级用通用搜索,后期再具体限定
                "time_window": "近24月",
                "max_results": 8,
                "purpose": f"{city['name']}{th['zh']}市级政策({city.get('role','')})"
            })

    # 写出
    out = AUDIT_DIR / "tavily_queries.jsonl"
    with out.open("w") as f:
        for q in queries:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    # 统计
    print(f"\n=== Tavily query 生成完成 ===")
    print(f"总 query 数: {len(queries)}")
    by_layer = {}
    by_tier = {}
    for q in queries:
        by_layer[q["layer"]] = by_layer.get(q["layer"], 0) + 1
        by_tier[q["tier"]] = by_tier.get(q["tier"], 0) + 1
    print("按 layer:")
    for k, v in by_layer.items():
        print(f"  {k}: {v}")
    print("按 tier:")
    for k, v in by_tier.items():
        print(f"  {k}: {v}")
    print(f"\n输出 -> {out}")
    print(f"\n47min 后跑命令:")
    print(f"  python3 _meta/audit_2026-05-06/run_tavily_matrix.py --queries {out}")


if __name__ == "__main__":
    main()
