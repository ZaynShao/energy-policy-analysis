#!/usr/bin/env python3
"""
B7 apply: merge 5 batch results → _meta/audit/isolated_classification.jsonl
+ 生成统计报告 _meta/audit/isolated_classification_summary.md

不改 raw 政策(纯 audit 数据,append 模式)。
前端可读这个 jsonl 决定 graph view 过滤逻辑。
"""
from __future__ import annotations
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent.parent
RESULTS = VAULT / "_l2_rebuild_state" / "isolated_classification" / "results"
OUT_JSONL = VAULT / "_meta" / "audit" / "isolated_classification.jsonl"
OUT_MD = VAULT / "_meta" / "audit" / "isolated_classification_summary.md"

NOW_ISO = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")

LABELS = {"index_page", "news_or_press", "duplicate_or_alt_version", "no_vault_basis", "true_orphan"}
ACTIONS = {"exclude_from_main_graph", "cleanup_candidate", "keep_with_tag", "future_refetch", "accept_orphan"}


def main() -> int:
    rows = []
    for bf in sorted(RESULTS.glob("batch_*.jsonl")):
        for ln in bf.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                r = json.loads(ln)
            except json.JSONDecodeError:
                print(f"[skip-bad-json] {bf.name}: {ln[:80]}")
                continue
            label = r.get("label")
            action = r.get("suggested_action")
            if label not in LABELS:
                print(f"[skip-bad-label] {r.get('pid')}: {label}")
                continue
            if action not in ACTIONS:
                print(f"[skip-bad-action] {r.get('pid')}: {action}")
                continue
            r["_classified_at"] = NOW_ISO
            r["_source_batch"] = bf.name
            rows.append(r)

    print(f"merged: {len(rows)} 行(去坏行后)")

    # dedup by pid(取最后一条 — 同 pid 多次分类时)
    by_pid = {}
    for r in rows:
        by_pid[r["pid"]] = r
    rows = list(by_pid.values())
    print(f"dedup by pid: {len(rows)} 唯一 pid")

    # 写 jsonl(覆盖式 — 这是 audit 当前快照)
    OUT_JSONL.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8"
    )
    print(f"✓ {OUT_JSONL}")

    # stats
    label_count = Counter(r["label"] for r in rows)
    action_count = Counter(r["suggested_action"] for r in rows)
    avg_conf = sum(r.get("confidence", 0) for r in rows) / len(rows) if rows else 0

    # 写 summary md
    lines = [
        f"# Isolated 132 政策分类 — {NOW_ISO}",
        "",
        f"- 总数:**{len(rows)}**",
        f"- 平均 confidence:{avg_conf:.3f}",
        f"- 数据源:`_l2_rebuild_state/isolated_classification/results/batch_*.jsonl`",
        f"- audit 数据:`_meta/audit/isolated_classification.jsonl`(下次跑覆盖)",
        "",
        "## Label 分布",
        "",
        "| label | n | % |",
        "|---|---:|---:|",
    ]
    for label in ["index_page", "news_or_press", "duplicate_or_alt_version", "no_vault_basis", "true_orphan"]:
        n = label_count.get(label, 0)
        lines.append(f"| `{label}` | {n} | {n/len(rows)*100:.1f}% |")

    lines += [
        "",
        "## Suggested Action 分布",
        "",
        "| action | n | % | 处理建议 |",
        "|---|---:|---:|---|",
    ]
    action_meaning = {
        "exclude_from_main_graph": "前端 graph 过滤,不展示主图谱",
        "cleanup_candidate": "review 后可下架到 _archive(同政策有更好版本)",
        "keep_with_tag": "保留,标 'no_vault_basis',P2.7 候选回填时优先抓上位",
        "future_refetch": "正经政策但 body 不全,需重抓",
        "accept_orphan": "真孤儿(早期/边缘),接受现状",
    }
    for action in ["exclude_from_main_graph", "cleanup_candidate", "keep_with_tag", "future_refetch", "accept_orphan"]:
        n = action_count.get(action, 0)
        meaning = action_meaning.get(action, "")
        lines.append(f"| `{action}` | {n} | {n/len(rows)*100:.1f}% | {meaning} |")

    # 子表:按 action 列出 pid(给前端用 / 后续作业用)
    lines += [
        "",
        "## 各 action 政策清单",
        "",
    ]
    for action in ["exclude_from_main_graph", "cleanup_candidate", "keep_with_tag", "future_refetch", "accept_orphan"]:
        pids = [r["pid"] for r in rows if r["suggested_action"] == action]
        lines.append(f"### `{action}` ({len(pids)})")
        lines.append("")
        if pids:
            lines.append("```")
            for pid in pids:
                lines.append(pid)
            lines.append("```")
        lines.append("")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"✓ {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
