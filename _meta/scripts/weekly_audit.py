#!/usr/bin/env python3
"""
weekly_audit: 串 audit 三件套 + 写 alert state(可被 audit_alert.py 比较)

本地 deterministic,无 API 调用。每周日 9:00 跑(launchd 或 cron)。

跑的:
1. _meta/audit_2026-05-06/local_coverage_baseline.py
   → coverage_baseline.md / coverage_matrix.json
2. _meta/audit_2026-05-06/audit_official_number_seq.py
   → official_number_audit.md / official_number_gaps.json
3. _meta/audit_2026-05-06/audit_citation_gaps.py
   → citation_gaps.md / citation_gaps.json

最后:
4. 拼合 _meta/audit/weekly_summary_<date>.md
5. 更新 _meta/audit/audit_state.json(给 audit_alert.py 做周比较)
"""
from __future__ import annotations
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent.parent
AUDIT_DIR = VAULT / "_meta" / "audit_2026-05-06"
OUT_DIR = VAULT / "_meta" / "audit"
OUT_DIR.mkdir(parents=True, exist_ok=True)

NOW = datetime.now()
NOW_DATE = NOW.strftime("%Y-%m-%d")
NOW_ISO = NOW.strftime("%Y-%m-%dT%H:%M:%S+08:00")


def run_step(label: str, script: Path) -> tuple[bool, str]:
    """跑一个 audit 子脚本,返回 (success, stdout_tail)"""
    print(f"\n[{label}] {script.name}")
    if not script.exists():
        return False, f"missing: {script}"
    r = subprocess.run(
        ["python3", str(script)],
        capture_output=True, text=True,
        cwd=str(VAULT)
    )
    tail = (r.stdout or "")[-1000:]
    print(tail)
    if r.returncode != 0:
        print(f"[stderr]\n{(r.stderr or '')[-500:]}")
        return False, tail
    return True, tail


def load_metric() -> dict:
    """读 relations_coverage_metric.py --json 拿当前指标"""
    metric_script = VAULT / "_meta" / "scripts" / "relations_coverage_metric.py"
    r = subprocess.run(
        ["python3", str(metric_script), "--json"],
        capture_output=True, text=True, cwd=str(VAULT)
    )
    if r.returncode != 0:
        return {}
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {}


def main() -> int:
    print(f"=== weekly_audit @ {NOW_ISO} ===")

    # 1-3: run 3 audits
    results = {}
    for label, name in [
        ("coverage", "local_coverage_baseline.py"),
        ("official_number", "audit_official_number_seq.py"),
        ("citation", "audit_citation_gaps.py"),
    ]:
        ok, tail = run_step(label, AUDIT_DIR / name)
        results[label] = {"ok": ok, "tail": tail.splitlines()[-3:]}

    # 4: load coverage matrix + citation gaps for state
    state = {
        "ran_at": NOW_ISO,
        "results": results,
    }
    cov_json = AUDIT_DIR / "coverage_matrix.json"
    if cov_json.exists():
        try:
            cov = json.loads(cov_json.read_text(encoding="utf-8"))
            n_themes = len(cov)
            cells = sum(len(v) for v in cov.values())
            nonzero = sum(1 for v in cov.values() for n in v.values() if n > 0)
            state["coverage_summary"] = {
                "themes": n_themes,
                "cells": cells,
                "nonzero": nonzero,
                "ratio": round(nonzero / cells, 4) if cells else 0,
            }
        except json.JSONDecodeError:
            pass

    cit_json = AUDIT_DIR / "citation_gaps.json"
    if cit_json.exists():
        try:
            gaps = json.loads(cit_json.read_text(encoding="utf-8"))
            if isinstance(gaps, list):
                state["citation_gaps_total"] = len(gaps)
            elif isinstance(gaps, dict):
                state["citation_gaps_total"] = len(gaps)
        except json.JSONDecodeError:
            pass

    metric = load_metric()
    if metric.get("summary"):
        state["relations_metric"] = metric["summary"]

    # 5: append to history + save current state
    state_path = OUT_DIR / "audit_state.json"
    history_path = OUT_DIR / "audit_state_history.jsonl"

    # snapshot 写到 history(append-only)
    with history_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(state, ensure_ascii=False) + "\n")

    # 当前 state 覆写
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ state → {state_path}")
    print(f"✓ history += 1 row → {history_path}")

    # 6: 写 weekly summary md
    summary_path = OUT_DIR / f"weekly_summary_{NOW_DATE}.md"
    lines = [f"# Weekly Audit — {NOW_DATE}", ""]
    lines.append(f"- 跑时: {NOW_ISO}")
    if "coverage_summary" in state:
        cs = state["coverage_summary"]
        lines.append(f"- 主题×省矩阵: {cs['nonzero']}/{cs['cells']} cells ({cs['ratio']*100:.1f}%)")
    if "citation_gaps_total" in state:
        lines.append(f"- citation gap: {state['citation_gaps_total']} 篇")
    if "relations_metric" in state:
        rm = state["relations_metric"]
        lines.append(f"- relations: {rm['policies']} 政策 / {rm['total_edges']} 边 / {rm['quadrants']['isolated']} isolated")
    lines.append("")
    lines.append("## 各 audit 子脚本结果")
    for label, r in results.items():
        status = "✓" if r["ok"] else "✗"
        lines.append(f"- [{status}] {label}")
        for line in r["tail"]:
            if line.strip():
                lines.append(f"      {line}")
    lines.append("")
    lines.append("## 详细输出")
    lines.append(f"- coverage_baseline: `_meta/audit_2026-05-06/coverage_baseline.md`")
    lines.append(f"- official_number: `_meta/audit_2026-05-06/official_number_audit.md`")
    lines.append(f"- citation_gaps: `_meta/audit_2026-05-06/citation_gaps.md`")
    lines.append("")
    lines.append("## 阈值告警")
    lines.append("跑 `python3 _meta/scripts/audit_alert.py` 比较与上周 state 的差异。")
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"✓ summary → {summary_path}")

    return 0 if all(r["ok"] for r in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
