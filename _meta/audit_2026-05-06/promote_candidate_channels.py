#!/usr/bin/env python3
"""
候选渠道主动晋升(47min 后跑)
对渠道目录里"候选"状态的省级发改委/能源局站点,主动用 Tavily site: filter 验证可达性 + 命中政策。

输入:
  - 渠道目录里的"候选"段(机器读 _meta/audit_2026-05-06/tavily_queries.jsonl 里 include_domains)
  - themes_13.yaml 里 P0 主题的 aliases(用于 site:xxx alias 检索)

输出:
  - candidate_promotion_results.jsonl
  - 渠道目录补丁建议(本地 markdown patch,人工 review 后合并)

判定:
  - 命中 ≥3 条 P0 主题政策 → 晋升正式段
  - 命中 1-2 条 → 保留候选,标"低活跃"
  - 0 条 → 删除候选(可能站点改版/失效)
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR = Path(__file__).resolve().parent

# 只验证 P0 主题(储能/VPP/电力市场/V2G/聚合商/配电网)
P0_THEMES = ["energy_storage_theme", "vpp_theme", "power_market", "v2g",
             "aggregator_access", "distribution_grid_opening"]

# 30+ 省发改委候选(从 gen_tavily_queries.py PROV_DRC_SITES 复制,排除已验证)
ALREADY_VERIFIED = {"fgw.sh.gov.cn", "fgw.fujian.gov.cn", "hbdrc.hebei.gov.cn"}

CANDIDATE_DOMAINS = [
    ("110000", "北京市", "fgw.beijing.gov.cn"),
    ("120000", "天津市", "fzgg.tj.gov.cn"),
    ("140000", "山西省", "fgw.shanxi.gov.cn"),
    ("150000", "内蒙古自治区", "fgw.nmg.gov.cn"),
    ("210000", "辽宁省", "fgw.ln.gov.cn"),
    ("220000", "吉林省", "fzggw.jl.gov.cn"),
    ("230000", "黑龙江省", "drc.hlj.gov.cn"),
    ("320000", "江苏省", "fzggw.jiangsu.gov.cn"),
    ("330000", "浙江省", "fzggw.zj.gov.cn"),
    ("340000", "安徽省", "fzggw.ah.gov.cn"),
    ("360000", "江西省", "drc.jiangxi.gov.cn"),
    ("370000", "山东省", "fgw.shandong.gov.cn"),
    ("410000", "河南省", "fgw.henan.gov.cn"),
    ("420000", "湖北省", "fgw.hubei.gov.cn"),
    ("430000", "湖南省", "fgw.hunan.gov.cn"),
    ("440000", "广东省", "drc.gd.gov.cn"),
    ("450000", "广西", "fgw.gxzf.gov.cn"),
    ("460000", "海南省", "plan.hainan.gov.cn"),
    ("500000", "重庆市", "fzggw.cq.gov.cn"),
    ("510000", "四川省", "fgw.sc.gov.cn"),
    ("520000", "贵州省", "fgw.guizhou.gov.cn"),
    ("530000", "云南省", "yndrc.yn.gov.cn"),
    ("610000", "陕西省", "sndrc.shaanxi.gov.cn"),
    ("620000", "甘肃省", "fzgg.gansu.gov.cn"),
    ("630000", "青海省", "fgw.qinghai.gov.cn"),
    ("640000", "宁夏", "fzggw.nx.gov.cn"),
]


def main():
    # 占位骨架: 47min 后跑时实际接 Tavily API
    # 这里先生成"待执行任务"清单
    tasks = []
    for prov_code, prov_name, domain in CANDIDATE_DOMAINS:
        if domain in ALREADY_VERIFIED:
            continue
        # 对每个候选域名跑 6 个 P0 主题的 site: 检索
        for theme_id in P0_THEMES:
            keyword = {
                "energy_storage_theme": "新型储能",
                "vpp_theme": "虚拟电厂",
                "power_market": "电力市场",
                "v2g": "车网互动",
                "aggregator_access": "负荷聚合商",
                "distribution_grid_opening": "配电网"
            }[theme_id]
            tasks.append({
                "task_type": "candidate_promotion",
                "province_code": prov_code,
                "province_name": prov_name,
                "domain": domain,
                "theme_id": theme_id,
                "tavily_query": f"site:{domain} {keyword}",
                "max_results": 5,
                "expected_duration_sec": 2,
            })

    out = AUDIT_DIR / "candidate_promotion_tasks.jsonl"
    with out.open("w") as f:
        for t in tasks:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    print(f"=== 候选渠道晋升任务清单 ===")
    print(f"候选域名数: {len(CANDIDATE_DOMAINS) - len(ALREADY_VERIFIED)}")
    print(f"任务总数(域名 × 6 主题): {len(tasks)}")
    print(f"预估 Tavily 调用: {len(tasks)}")
    print(f"输出 -> {out}")
    print(f"\n47min 后跑流程:")
    print(f"  1. 读 candidate_promotion_tasks.jsonl")
    print(f"  2. 对每条任务调 Tavily site:filter")
    print(f"  3. 命中 ≥3 → 晋升正式段")
    print(f"  4. 命中 1-2 → 保留候选 + 标'低活跃'")
    print(f"  5. 0 → 删除候选(站点失效)")


if __name__ == "__main__":
    main()
