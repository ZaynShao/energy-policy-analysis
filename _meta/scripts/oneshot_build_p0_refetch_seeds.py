#!/usr/bin/env python3
"""一次性 — 把 P0 漏抓诊断 × 候选池 → _meta/audit/p0_refetch_seeds.md

合并 3 类种子:
  1. R2 fetch 失败 url(diagnose_p0_gaps 找出的):需走 SKILL §A.6 fallback chain
  2. R3 promote 漏 url(rest 中 P0×P0 候选,top600 没收):走 trigger A 直接重抓
  3. 提示:53 missing_base_policies(单独文件,本清单只提引用)

输出:_meta/audit/p0_refetch_seeds.md(给 trigger A `prepare --pids` 或
gen_daily_queries 喂数据)。
"""
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

VAULT = Path(__file__).resolve().parents[2]
AUDIT = VAULT / "_meta" / "audit_2026-05-06"
OUT = VAULT / "_meta" / "audit" / "p0_refetch_seeds.md"

P0_THEMES = {
    "v2g": "V2G(车网互动)",
    "vpp_theme": "虚拟电厂",
    "charging_infra": "充电基础设施",
    "power_market": "电力市场",
    "energy_storage_theme": "新型储能",
    "aggregator_access": "聚合商接入",
    "distribution_grid_opening": "配电网开放",
    "green_power_trading_theme": "绿电交易",
}
P0_PROVINCES = {
    "110000": "北京", "310000": "上海", "320000": "江苏",
    "330000": "浙江", "370000": "山东", "440000": "广东",
}


def load_jsonl(p):
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


def load_vault_hits():
    """每 (theme_id, province_code_2位) 在 vault 中已收的政策数"""
    import yaml
    THEMES_DIR = VAULT / "2_crystallized" / "themes"
    name_to_id = {
        "V2G": "v2g", "VPP_THEME": "vpp_theme", "CHARGING_INFRA": "charging_infra",
        "POWER_MARKET": "power_market", "ENERGY_STORAGE_THEME": "energy_storage_theme",
        "AGGREGATOR_ACCESS": "aggregator_access",
        "DISTRIBUTION_GRID_OPENING": "distribution_grid_opening",
        "GREEN_POWER_TRADING_THEME": "green_power_trading_theme",
    }
    hits = defaultdict(int)
    for dir_name, tid in name_to_id.items():
        inp = THEMES_DIR / dir_name / "_input.json"
        if not inp.exists():
            continue
        d = json.loads(inp.read_text(encoding="utf-8"))
        for p in d.get("policies", []):
            code = (p.get("region") or {}).get("code", "")
            if len(code) >= 2:
                hits[(tid, code[:2] + "0000")] += 1
    return hits


def main():
    vault_hits = load_vault_hits()
    # 加载候选池 + fetch log
    top600 = load_jsonl(AUDIT / "candidates_top600.jsonl")
    rest = load_jsonl(AUDIT / "candidates_rest.jsonl")

    fail_urls = set()
    for log in ["fetch_top600.log", "fetch_retry.log"]:
        p = AUDIT / log
        if not p.exists():
            continue
        for ln in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                r = json.loads(ln)
                if not r.get("ok"):
                    fail_urls.add(r.get("url", ""))
            except json.JSONDecodeError:
                pass

    # url meta lookup:url → (title, layer_meta)
    url_meta = {}
    for c in top600 + rest:
        url_meta[c["url"]] = {
            "title": c.get("title", ""),
            "layer_meta": c.get("layer_meta", []),
            "in_top600": c in top600,
            "in_rest": c in rest,
        }

    # 按 (theme × prov) 聚合
    cells_r2 = defaultdict(list)  # fetch 失败:走 fallback
    cells_r3 = defaultdict(list)  # promote 漏:trigger A 直接抓

    for url, meta in url_meta.items():
        for m in meta["layer_meta"]:
            if not isinstance(m, dict):
                continue
            tid = m.get("theme_id")
            pc = m.get("province_code")
            if tid not in P0_THEMES or pc not in P0_PROVINCES:
                continue
            # 只对 vault 中 0 命中的 cell 列种子(健康 cell 不需要补)
            if vault_hits.get((tid, pc), 0) > 0:
                continue
            entry = {"url": url, "title": meta["title"]}
            if meta["in_top600"] and url in fail_urls:
                cells_r2[(tid, pc)].append(entry)
            elif meta["in_rest"] and url not in fail_urls:
                cells_r3[(tid, pc)].append(entry)

    # 输出
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("---")
    lines.append("title: P0 主题 × P0 省 重抓种子清单")
    lines.append(f"generated_at: {cn_now_iso()}")
    lines.append("generated_by: _meta/scripts/oneshot_build_p0_refetch_seeds.py")
    lines.append(f"r2_cells: {len(cells_r2)}")
    lines.append(f"r2_urls: {sum(len(v) for v in cells_r2.values())}")
    lines.append(f"r3_cells: {len(cells_r3)}")
    lines.append(f"r3_urls: {sum(len(v) for v in cells_r3.values())}")
    lines.append("---")
    lines.append("")
    lines.append("# P0 主题 × P0 省 重抓种子清单")
    lines.append("")
    lines.append("**生成**: " + cn_now_iso())
    lines.append("")
    lines.append("配套 `_meta/audit/p0_gaps_diagnosis.md`(根因诊断)+ `missing_base_policies.md`")
    lines.append("(53 个 commentary 引用主版本缺失)。")
    lines.append("")

    # R2 段(fetch 失败,走 fallback chain)
    lines.append("## 🚨 R2:fetch 失败 url(走 SKILL §A.6 fallback chain)")
    lines.append("")
    lines.append("Phase 1 fetch_candidates.py 失败的 P0×P0 url。**多数是 SSL/TLS 不兼容**")
    lines.append("(本机 LibreSSL 2.8.3 + 政府老 https 端点)。")
    lines.append("")
    lines.append("**Fallback chain**(逐级试,首个成功为准):")
    lines.append("1. `requests` + 新 OpenSSL Python(`brew install python@3.12` + 重跑 fetch)")
    lines.append("2. **playwright/chromium**(浏览器内核宽容老 TLS)")
    lines.append("3. **手动浏览器抓**:打开 url → 保存 HTML → 放 `_meta/audit_2026-05-06/manual_staging/<8hash>.md`")
    lines.append("4. **换源**:同政策可能在 ndrc.gov.cn / nea.gov.cn / 央媒(人民日报)有镜像")
    lines.append("")
    if not cells_r2:
        lines.append("(无)")
        lines.append("")
    for (tid, pc) in sorted(cells_r2.keys()):
        urls = cells_r2[(tid, pc)]
        lines.append(f"### {P0_THEMES[tid]} × {P0_PROVINCES[pc]}")
        lines.append("")
        for e in urls:
            lines.append(f"- {e['title'][:70]}")
            lines.append(f"  - {e['url']}")
        lines.append("")

    # R3 段(promote 漏,直接走 trigger A)
    lines.append("## 📥 R3:promote 漏 url(走 trigger A SKILL §2 prepare 重抓)")
    lines.append("")
    lines.append("rest 中含 P0×P0 候选(layer_meta 标 P0 主题 + P0 省),Phase 1 因为")
    lines.append("`candidates_top600` 600 cutoff 没纳入。本次直接挑出供 trigger A 重抓。")
    lines.append("")
    lines.append("**操作**:")
    lines.append("```bash")
    lines.append("# 手动列 url → fetch_candidates 单跑(本机 SSL OK 的话)")
    lines.append("# 或 normalize_to_raw 后走 trigger A:")
    lines.append("python3 _meta/scripts/rebuild_l2.py prepare --trigger pid_change --pids ...")
    lines.append("```")
    lines.append("")
    if not cells_r3:
        lines.append("(无)")
        lines.append("")
    for (tid, pc) in sorted(cells_r3.keys()):
        urls = cells_r3[(tid, pc)]
        lines.append(f"### {P0_THEMES[tid]} × {P0_PROVINCES[pc]}({len(urls)} url)")
        lines.append("")
        for e in urls[:15]:  # 每 cell 最多 15
            lines.append(f"- {e['title'][:70]}")
            lines.append(f"  - {e['url']}")
        if len(urls) > 15:
            lines.append(f"- ... 余 {len(urls) - 15} 条(全量见 candidates_rest.jsonl 按 layer_meta 过滤)")
        lines.append("")

    # 引用 missing_base_policies
    lines.append("## 📌 关联清单")
    lines.append("")
    lines.append("- `_meta/audit/missing_base_policies.md` — 53 个 base pid commentary 引用断")
    lines.append("  (含发改环资〔2025〕1745 / 发改能源〔2024〕1128 等 P0 政策)")
    lines.append("- `_meta/audit/p0_gaps_diagnosis.md` — R0~R4 漏抓机制诊断")
    lines.append("- `_meta/audit/fetch_failed_for_manual.jsonl` — fetch_candidates.py 自动追加")
    lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote: {OUT.relative_to(VAULT)}")
    print(f"  R2 cells: {len(cells_r2)} | R2 urls: {sum(len(v) for v in cells_r2.values())}")
    print(f"  R3 cells: {len(cells_r3)} | R3 urls: {sum(len(v) for v in cells_r3.values())}")


if __name__ == "__main__":
    main()
