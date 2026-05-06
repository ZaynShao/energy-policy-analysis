#!/usr/bin/env python3
"""
oneshot: backfill _meta/audit/rel_judge_history.jsonl 用 vault 现状

对每个 vault 政策(273)写一行 history,标 trigger=build_phase_legacy,
prompt_version + model 都 unknown_legacy。edges_outbound_added/inbound_added
按当前 jsonl 真实计数(对此 pid 当前累计的 outbound/inbound 边数 — 这是
今后 metric 看"已审"标记的 baseline)。

只跑一次(若 history 已存在 build_phase_legacy 行就拒跑)。
"""
from __future__ import annotations
import json
import sys
from datetime import datetime
from pathlib import Path

import yaml

VAULT = Path(__file__).resolve().parent.parent.parent
HISTORY = VAULT / "_meta" / "audit" / "rel_judge_history.jsonl"
NOW_ISO = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")


def main() -> int:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)

    # 1. 拒重 — 已有 build_phase_legacy 行就拒
    if HISTORY.exists():
        for line in HISTORY.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    r = json.loads(line)
                    if r.get("trigger") == "build_phase_legacy":
                        print(f"[abort] history 已含 build_phase_legacy 行,backfill 已跑过")
                        return 0
                except json.JSONDecodeError:
                    pass

    # 2. 收集 vault 273 pid
    pids: list[str] = []
    for p in (VAULT / "0_raw/policies").glob("*.md"):
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if not txt.startswith("---"):
            continue
        end = txt.find("---", 3)
        if end < 0:
            continue
        try:
            fm = yaml.safe_load(txt[3:end]) or {}
        except yaml.YAMLError:
            continue
        if fm.get("id"):
            pids.append(fm["id"])
    pids.sort()
    print(f"vault pids: {len(pids)}")

    # 3. 算每 pid 在 9 类关系 jsonl 的 outbound/inbound 累计
    out_count: dict[str, int] = {p: 0 for p in pids}
    in_count: dict[str, int] = {p: 0 for p in pids}
    rel_dir = VAULT / "1_extracted/relations"
    for jf in rel_dir.glob("*.jsonl"):
        if jf.name.startswith("_"):
            continue
        for line in jf.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            f, t = e.get("from"), e.get("to")
            if f in out_count:
                out_count[f] += 1
            if t in in_count:
                in_count[t] += 1

    # 4. append 273 行
    with HISTORY.open("a", encoding="utf-8") as fh:
        for pid in pids:
            fh.write(json.dumps({
                "pid": pid,
                "ran_at": None,
                "trigger": "build_phase_legacy",
                "prompt_version": "unknown_legacy",
                "model": "unknown_legacy",
                "edges_outbound_added": out_count[pid],
                "edges_inbound_added": in_count[pid],
                "backfilled_at": NOW_ISO,
            }, ensure_ascii=False) + "\n")
    print(f"✓ backfilled {len(pids)} pids → {HISTORY}")

    # 5. 报 isolated(out=0 + in=0)
    isolated = [p for p in pids if out_count[p] == 0 and in_count[p] == 0]
    print(f"  其中 isolated(双 0): {len(isolated)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
