#!/usr/bin/env python3
"""
audit_alert: 读 audit_state_history 比较本周 vs 上周,触发阈值告警

阈值(PHASE2_PLAYBOOK §1):
- 矩阵覆盖率单周下降 > 5% → 告警
- citation_gap 新增 > 50 → 告警
- isolated 政策单周 +20 → 告警(本会话新增,B7 已分类后特别值得监控)
- 任一 P0 主题 × P0 省 0 命中 → 告警(从 coverage_matrix.json 直读)

输出:
- 控制台打印
- _meta/audit/audit_alerts.md 追加新告警块
- 退出码 0=无告警 / 1=有告警
"""
from __future__ import annotations
import json
import sys
from datetime import datetime
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent.parent
AUDIT_DIR = VAULT / "_meta" / "audit"
HISTORY = AUDIT_DIR / "audit_state_history.jsonl"
ALERTS_MD = AUDIT_DIR / "audit_alerts.md"
COV_MATRIX = VAULT / "_meta" / "audit_2026-05-06" / "coverage_matrix.json"

P0_THEMES = ["vpp_theme", "energy_storage_theme", "power_market", "v2g",
             "aggregator_access", "distribution_grid_opening"]
P0_PROVINCES = {  # code → 名称
    "110000": "北京市", "310000": "上海市", "320000": "江苏省",
    "330000": "浙江省", "440000": "广东省", "370000": "山东省",
}

NOW_ISO = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")


def load_history() -> list[dict]:
    if not HISTORY.exists():
        return []
    rows = []
    for ln in HISTORY.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            try:
                rows.append(json.loads(ln))
            except json.JSONDecodeError:
                pass
    return rows


def main() -> int:
    history = load_history()
    if not history:
        print("[no history] 至少跑一次 weekly_audit.py 后再 alert")
        return 0

    cur = history[-1]
    prev = history[-2] if len(history) >= 2 else None
    alerts = []

    # 1. 覆盖率周环比
    if prev and "coverage_summary" in cur and "coverage_summary" in prev:
        c = cur["coverage_summary"]["ratio"]
        p = prev["coverage_summary"]["ratio"]
        delta = c - p
        if delta < -0.05:
            alerts.append(f"⚠ 覆盖率单周下降 {delta*100:.1f}% (上周 {p*100:.1f}% → 本周 {c*100:.1f}%)")

    # 2. citation gap 新增
    if prev and "citation_gaps_total" in cur and "citation_gaps_total" in prev:
        new = cur["citation_gaps_total"] - prev["citation_gaps_total"]
        if new > 50:
            alerts.append(f"⚠ citation gap 单周新增 {new}(上周 {prev['citation_gaps_total']} → 本周 {cur['citation_gaps_total']})")

    # 3. isolated 单周 +20
    if prev and "relations_metric" in cur and "relations_metric" in prev:
        c_iso = cur["relations_metric"].get("quadrants", {}).get("isolated", 0)
        p_iso = prev["relations_metric"].get("quadrants", {}).get("isolated", 0)
        if c_iso - p_iso > 20:
            alerts.append(f"⚠ isolated 政策单周 +{c_iso - p_iso}(上周 {p_iso} → 本周 {c_iso})")

    # 4. P0 主题 × P0 省零命中(并指出根因 — 见 SKILL §A.6)
    if COV_MATRIX.exists():
        try:
            cov = json.loads(COV_MATRIX.read_text(encoding="utf-8"))
            zero_p0 = []
            for th in P0_THEMES:
                if th not in cov:
                    continue
                for code, name in P0_PROVINCES.items():
                    if cov[th].get(code, 0) == 0:
                        zero_p0.append(f"{th} × {name}")
            if zero_p0:
                # 提示运行 diagnose_p0_gaps 看 R1/R2/R3 根因区分
                alerts.append(
                    f"⚠ P0 主题×P0 省零命中 {len(zero_p0)} cells:\n   - "
                    + "\n   - ".join(zero_p0[:10])
                    + "\n   (跑 `python3 _meta/scripts/diagnose_p0_gaps.py` 看根因 R1/R2/R3,SKILL §A.6)"
                )
        except json.JSONDecodeError:
            pass

    # 5. fetch 失败的 P0×P0 url(B 类修复 — 不让 fetch 错变成隐形漏抓)
    p0_diag = VAULT / "_meta" / "audit" / "p0_gaps_diagnosis.md"
    if p0_diag.exists():
        # 简单 parse:看 "R2" 类别 cell 数
        try:
            text = p0_diag.read_text(encoding="utf-8")
            r2_count = text.count("R2 fetch")
            if r2_count > 0:
                alerts.append(
                    f"⚠ {r2_count} 个 P0 cell 因 fetch 失败漏抓(R2,见 p0_gaps_diagnosis.md)"
                    "\n   走 SKILL §A.6 fallback chain(playwright/手动)重抓"
                )
        except OSError:
            pass

    # 输出
    if not alerts:
        print(f"[ok @ {NOW_ISO}] 无告警")
        return 0

    block = [f"\n---\n## Alert @ {NOW_ISO}\n"]
    for a in alerts:
        block.append(a)
    block.append("")
    block.append(f"详情见 _meta/audit/weekly_summary_{datetime.now().strftime('%Y-%m-%d')}.md")

    with ALERTS_MD.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(block) + "\n")
    for a in alerts:
        print(a)
    print(f"\n告警 {len(alerts)} 条 → 追加到 {ALERTS_MD}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
