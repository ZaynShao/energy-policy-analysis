#!/usr/bin/env python3
"""把 5c/inputs.jsonl 和 rel_judge/inputs.jsonl 各拆 7 batch + 各 batch 写独立 prompt"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
N_BATCH = 7

# 5c
src5c = ROOT / "_l2_rebuild_state" / "5c" / "inputs.jsonl"
prompt5c_orig = (ROOT / "_l2_rebuild_state" / "5c" / "prompt.md").read_text()

lines = src5c.read_text().strip().split("\n")
print(f"5c total: {len(lines)} rows, splitting into {N_BATCH} batches")

per_batch = (len(lines) + N_BATCH - 1) // N_BATCH
batch_dir = ROOT / "_l2_rebuild_state" / "5c"
results_dir = batch_dir / "results"
results_dir.mkdir(exist_ok=True)

for i in range(N_BATCH):
    batch_lines = lines[i*per_batch:(i+1)*per_batch]
    if not batch_lines:
        continue
    batch_file = batch_dir / f"batch_{i+1}.jsonl"
    batch_file.write_text("\n".join(batch_lines) + "\n")
    # prompt for this batch
    bp = prompt5c_orig.replace(
        str(src5c),
        str(batch_file)
    ).replace(
        "results.jsonl",
        f"batch_{i+1}_results.jsonl"
    )
    bp += f"\n\nNOTE: 这是 batch {i+1}/{N_BATCH}, 含 {len(batch_lines)} 政策。处理完输出到 batch_{i+1}_results.jsonl。\n"
    (batch_dir / f"prompt_batch_{i+1}.md").write_text(bp)
    print(f"  batch {i+1}: {len(batch_lines)} rows → {batch_file.name}")

# rel_judge
src_rel = ROOT / "_l2_rebuild_state" / "rel_judge" / "inputs.jsonl"
prompt_rel_orig = (ROOT / "_l2_rebuild_state" / "rel_judge" / "prompt.md").read_text()

lines_rel = src_rel.read_text().strip().split("\n")
print(f"\nrel_judge total: {len(lines_rel)} target pids, splitting into {N_BATCH} batches")
per_batch_rel = (len(lines_rel) + N_BATCH - 1) // N_BATCH
rel_dir = ROOT / "_l2_rebuild_state" / "rel_judge"
(rel_dir / "results").mkdir(exist_ok=True)
for i in range(N_BATCH):
    batch_lines = lines_rel[i*per_batch_rel:(i+1)*per_batch_rel]
    if not batch_lines:
        continue
    batch_file = rel_dir / f"batch_{i+1}.jsonl"
    batch_file.write_text("\n".join(batch_lines) + "\n")
    bp = prompt_rel_orig.replace(str(src_rel), str(batch_file))
    bp = bp.replace("results.jsonl", f"batch_{i+1}_results.jsonl")
    bp += f"\n\nNOTE: 这是 batch {i+1}/{N_BATCH}, 含 {len(batch_lines)} 目标 pid。\n"
    (rel_dir / f"prompt_batch_{i+1}.md").write_text(bp)
    print(f"  batch {i+1}: {len(batch_lines)} rows → {batch_file.name}")

print("\nDone. 派 subagent 时, 每 subagent 读对应 prompt_batch_N.md,写到 batch_N_results.jsonl")
