#!/usr/bin/env python3
"""P0 主题 × P0 省 漏抓诊断 — 区分 4 种漏抓机制

输出 _meta/audit/p0_gaps_diagnosis.md(并打印简报)。

4 种漏抓机制:
  R1. 真没政策 — Tavily 0 results AND vault 0 命中
  R2. fetch 失败 — Tavily 抓到 url,promote 后 fetch_top600/retry 全失败
  R3. promote 漏 — Tavily 抓到 + candidates_rest 含,但未进 top600
  R4. 入库后召回失败 — 入了 vault 但 entity 抽取 / region 推断错(本脚本初版不查)

数据源(只读):
  - 0_raw/policies/(vault 现状)
  - _meta/audit_2026-05-06/coverage_matrix.json
  - _meta/audit_2026-05-06/tavily_results_merged.jsonl
  - _meta/audit_2026-05-06/candidates_top600.jsonl
  - _meta/audit_2026-05-06/candidates_rest.jsonl
  - _meta/audit_2026-05-06/fetch_top600.log + fetch_retry.log
  - 2_crystallized/themes/<NAME>/_input.json(主题命中真值)

用法:
  python3 _meta/scripts/diagnose_p0_gaps.py
"""
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

VAULT = Path(__file__).resolve().parents[2]
AUDIT = VAULT / "_meta" / "audit_2026-05-06"
THEMES_DIR = VAULT / "2_crystallized" / "themes"
OUT = VAULT / "_meta" / "audit" / "p0_gaps_diagnosis.md"

# P0 主题(SKILL §1.4 audit_alert 同口径)
P0_THEMES = [
    ("v2g", "V2G", "V2G(车网互动)"),
    ("vpp_theme", "VPP_THEME", "虚拟电厂"),
    ("charging_infra", "CHARGING_INFRA", "充电基础设施"),
    ("power_market", "POWER_MARKET", "电力市场"),
    ("energy_storage_theme", "ENERGY_STORAGE_THEME", "新型储能"),
    ("aggregator_access", "AGGREGATOR_ACCESS", "聚合商接入"),
    ("distribution_grid_opening", "DISTRIBUTION_GRID_OPENING", "配电网开放"),
    ("green_power_trading_theme", "GREEN_POWER_TRADING_THEME", "绿电交易"),
]
# P0 省(audit_alert 同口径)
P0_PROVINCES = [
    ("110000", "北京"),
    ("310000", "上海"),
    ("320000", "江苏"),
    ("330000", "浙江"),
    ("370000", "山东"),
    ("440000", "广东"),
]


def load_jsonl_safe(p):
    out = []
    if not p.exists():
        return out
    for ln in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not ln.strip():
            continue
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            pass
    return out


def cn_now_iso():
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def main():
    # 1. vault 真值:每主题 × 省 命中数(读 13 主题 _input.json,region.code 前 2 位匹配省)
    print("[step 1] 加载 vault 主题命中真值...")
    vault_hits = defaultdict(lambda: defaultdict(list))  # [theme_id][prov_code_2] = [pid,...]
    for theme_id, dir_name, _ in P0_THEMES:
        inp = THEMES_DIR / dir_name / "_input.json"
        if not inp.exists():
            continue
        d = json.loads(inp.read_text(encoding="utf-8"))
        for p in d.get("policies", []):
            code = (p.get("region") or {}).get("code", "")
            if len(code) >= 2:
                vault_hits[theme_id][code[:2] + "0000"].append(p["id"])

    # 2. tavily_results:每 query 的 ok / results 数(按 theme_id × province_code)
    print("[step 2] 加载 tavily_results...")
    results = load_jsonl_safe(AUDIT / "tavily_results_merged.jsonl")
    tavily_by_cell = defaultdict(lambda: {"queries": 0, "total_results": 0, "urls": set()})
    for r in results:
        tid = r.get("theme_id", "")
        pc = r.get("province_code", "")
        cell = tavily_by_cell[(tid, pc)]
        cell["queries"] += 1
        rs = r.get("results", [])
        cell["total_results"] += len(rs)
        for hit in rs:
            cell["urls"].add(hit.get("url", ""))

    # 3. candidates_top600 / rest:layer_meta 中 (theme × province) 分布
    print("[step 3] 加载 candidates...")
    top600 = load_jsonl_safe(AUDIT / "candidates_top600.jsonl")
    rest = load_jsonl_safe(AUDIT / "candidates_rest.jsonl")

    def candidates_by_cell(cs):
        out = defaultdict(list)
        for c in cs:
            seen = set()
            for m in c.get("layer_meta") or []:
                if not isinstance(m, dict):
                    continue
                key = (m.get("theme_id"), m.get("province_code"))
                if key not in seen:
                    out[key].append(c["url"])
                    seen.add(key)
        return out

    top600_cell = candidates_by_cell(top600)
    rest_cell = candidates_by_cell(rest)

    # 4. fetch log:失败 url 集
    print("[step 4] 加载 fetch logs...")
    fail_urls = set()
    for log_file in ["fetch_top600.log", "fetch_retry.log"]:
        p = AUDIT / log_file
        if not p.exists():
            continue
        for ln in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                r = json.loads(ln)
                if not r.get("ok"):
                    fail_urls.add(r.get("url", ""))
            except json.JSONDecodeError:
                pass

    # 5. 诊断每个 P0 主题 × P0 省的 cell
    print("[step 5] 诊断 P0 × P0 矩阵...")
    diagnoses = []  # list of dict
    for theme_id, dir_name, theme_zh in P0_THEMES:
        for pcode, pzh in P0_PROVINCES:
            vault_n = len(vault_hits[theme_id].get(pcode, []))
            tav = tavily_by_cell.get((theme_id, pcode), {"queries": 0, "total_results": 0, "urls": set()})
            top_urls = top600_cell.get((theme_id, pcode), [])
            rest_urls = rest_cell.get((theme_id, pcode), [])
            top_failed = [u for u in top_urls if u in fail_urls]
            top_ok_not_in_vault = [u for u in top_urls if u not in fail_urls]  # 应该入库但实际未必

            # 分类
            if vault_n > 0:
                category = "✓ 健康(已入库)"
                action = "—"
            elif tav["total_results"] == 0 and tav["queries"] > 0:
                category = "R1 真没政策"
                action = "可能是真没政策(Tavily 全省 0 命中);加 city 层 query 兜底"
            elif tav["queries"] == 0:
                category = "R0 query 矩阵漏发"
                action = "看 gen_tavily_queries.py 是否覆盖该 cell"
            elif top_failed and len(top_failed) == len(top_urls):
                category = "R2 fetch 全失败"
                action = "走 SKILL §A.6 fallback chain(playwright/手动)"
            elif top_failed:
                category = f"R2 部分 fetch 失败({len(top_failed)}/{len(top_urls)})"
                action = "重抓失败的 url + 检查为何 ok url 也未入库"
            elif top_urls and not top_failed:
                category = "R4 入库失败(已抓但未入)"
                action = "看 normalize_to_raw / promotion_decisions log"
            elif rest_urls and not top_urls:
                category = "R3 promote 漏"
                action = f"rest 中有 {len(rest_urls)} 候选,本次修 promote 后会进 top600"
            else:
                category = "未知"
                action = "需手工排查"

            diagnoses.append({
                "theme_id": theme_id,
                "theme_zh": theme_zh,
                "province_code": pcode,
                "province_zh": pzh,
                "vault_n": vault_n,
                "tavily_queries": tav["queries"],
                "tavily_results": tav["total_results"],
                "top600_n": len(top_urls),
                "top600_failed_n": len(top_failed),
                "rest_n": len(rest_urls),
                "category": category,
                "action": action,
                "failed_urls": sorted(top_failed)[:10],
                "rest_urls": sorted(rest_urls)[:10],
            })

    # 6. 输出报告
    print(f"[step 6] 写报告 → {OUT.relative_to(VAULT)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("---")
    lines.append("title: P0 主题 × P0 省 漏抓诊断")
    lines.append(f"generated_at: {cn_now_iso()}")
    lines.append("generated_by: _meta/scripts/diagnose_p0_gaps.py")
    lines.append(f"p0_themes: {len(P0_THEMES)}")
    lines.append(f"p0_provinces: {len(P0_PROVINCES)}")
    lines.append(f"cells_total: {len(P0_THEMES) * len(P0_PROVINCES)}")

    cat_counter = defaultdict(int)
    for d in diagnoses:
        cat_counter[d["category"].split("(")[0].strip()] += 1
    for k, v in cat_counter.items():
        lines.append(f"  cat_{k.replace(' ', '_')}: {v}")

    lines.append("---")
    lines.append("")
    lines.append(f"# P0 主题 × P0 省 漏抓诊断({cn_now_iso()})")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append("| category | cells |")
    lines.append("|---|---:|")
    for k, v in sorted(cat_counter.items(), key=lambda x: -x[1]):
        lines.append(f"| {k} | {v} |")
    lines.append("")

    lines.append("## 漏抓矩阵(P0×P0)")
    lines.append("")
    lines.append("| 主题 | 省 | vault | tavily q/r | top600 | top600 失败 | rest | category |")
    lines.append("|------|-----|------:|------:|------:|------:|------:|---------|")
    for d in diagnoses:
        if d["category"].startswith("✓"):
            continue
        lines.append(
            f"| {d['theme_zh']} | {d['province_zh']} | {d['vault_n']} | "
            f"{d['tavily_queries']}/{d['tavily_results']} | {d['top600_n']} | "
            f"{d['top600_failed_n']} | {d['rest_n']} | {d['category']} |"
        )
    lines.append("")

    lines.append("## 重点 cells 详情(非健康)")
    lines.append("")
    for d in diagnoses:
        if d["category"].startswith("✓"):
            continue
        lines.append(f"### {d['theme_zh']} × {d['province_zh']}")
        lines.append("")
        lines.append(f"- **vault 命中**: {d['vault_n']}")
        lines.append(f"- **Tavily**: {d['tavily_queries']} queries / {d['tavily_results']} results")
        lines.append(f"- **top600 候选**: {d['top600_n']}({d['top600_failed_n']} fetch 失败)")
        lines.append(f"- **rest 候选**(promote 漏): {d['rest_n']}")
        lines.append(f"- **category**: {d['category']}")
        lines.append(f"- **action**: {d['action']}")
        if d["failed_urls"]:
            lines.append("- **fetch 失败 url(前 10)**:")
            for u in d["failed_urls"]:
                lines.append(f"  - {u}")
        if d["rest_urls"] and not d["failed_urls"]:
            lines.append("- **rest url(前 10)**:")
            for u in d["rest_urls"]:
                lines.append(f"  - {u}")
        lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")

    # 简报
    print()
    print(f"=== 诊断完成({len(diagnoses)} cells)===")
    for k, v in sorted(cat_counter.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    print(f"\n详见 {OUT.relative_to(VAULT)}")


if __name__ == "__main__":
    main()
