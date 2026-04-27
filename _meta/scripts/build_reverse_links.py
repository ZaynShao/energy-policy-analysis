#!/usr/bin/env python3
"""
build_reverse_links.py
Step 6d / B 阶段 — 生成 _index_by_policy/<P_id>.md 反链文件 (按 schema_v3.md §6.4)

输入:
  - 0_raw/policies/*.md           (建 P_id → meta 反查)
  - 1_extracted/relations/<rel>.jsonl  (8 类 typed relations)

输出:
  - 1_extracted/relations/_index_by_policy/<P_id>.md
    (只为有入向边的 target 生成,每个文件含 8 类入向 section)

行为:
  - 每次跑全量重建(先清空 _index_by_policy/ 下旧 .md,再生成)
  - section 内按 from.date 时间倒序
  - 每条入向条目:简版 `- [[P_xxx]] — title (YYYY-MM-DD)`
  - yaml header 含 policy_file 相对路径(指回 0_raw/policies/)
"""

import json
import sys
import yaml
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict

VAULT_ROOT = Path.home() / "Documents/Zayn Main/政策分析"
POLICIES_DIR = VAULT_ROOT / "0_raw/policies"
RELATIONS_DIR = VAULT_ROOT / "1_extracted/relations"
OUTPUT_DIR = RELATIONS_DIR / "_index_by_policy"

CST = timezone(timedelta(hours=8))

# 8 类出向 → 入向 section 标签 (按 schema_v3.md §6.4 命名表)
REL_TO_SECTION_LABEL = {
    "cites_basis":    "被引为依据 (cited_as_basis_by)",
    "supersedes":     "被废止 (superseded_by)",
    "iterates":       "被迭代 (iterated_by)",
    "extends":        "被扩展 (extended_by)",
    "clarifies":      "被细化 (clarified_by)",
    "references":     "被引用 (referenced_by)",
    "aligns_with":    "被对齐 (aligns_with_by)",
    "conflicts_with": "被冲突 (conflicts_with_by)",
}

# 反链文件内 section 出现顺序 (cites_basis 优先,演进类次之,引用/对齐类靠后)
SECTION_ORDER = [
    "cites_basis",
    "supersedes",
    "iterates",
    "extends",
    "clarifies",
    "references",
    "aligns_with",
    "conflicts_with",
]


def cn_now_iso():
    return datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def parse_frontmatter(md_path: Path):
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, parts[2]


def build_id_to_meta():
    id_to_meta = {}
    for md in POLICIES_DIR.glob("*.md"):
        fm, _ = parse_frontmatter(md)
        pid = fm.get("id")
        if not pid:
            continue
        date = fm.get("date") or ""
        if hasattr(date, "isoformat"):
            date = date.isoformat()
        id_to_meta[pid] = {
            "title": fm.get("title", "") or "",
            "date": str(date),
            "file_name": md.name,
        }
    return id_to_meta


def main():
    print(f"[init] vault:    {VAULT_ROOT}")
    print(f"[init] output:   {OUTPUT_DIR}")

    id_to_meta = build_id_to_meta()
    print(f"[init] policies indexed: {len(id_to_meta)}")

    # 收集 inbound: target_id → {rel: [edges...]}
    inbound = defaultdict(lambda: defaultdict(list))
    rel_files_seen = 0
    total_edges = 0

    for rel in SECTION_ORDER:
        path = RELATIONS_DIR / f"{rel}.jsonl"
        if not path.exists():
            print(f"[warn] missing relation file: {rel}.jsonl")
            continue
        rel_files_seen += 1
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    edge = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"[warn] bad json in {rel}.jsonl: {e}", file=sys.stderr)
                    continue
                from_id = edge.get("from")
                to_id = edge.get("to")
                if not (from_id and to_id):
                    continue
                from_meta = id_to_meta.get(from_id, {})
                inbound[to_id][rel].append({
                    "from_id": from_id,
                    "from_title": from_meta.get("title", ""),
                    "from_date": from_meta.get("date", ""),
                })
                total_edges += 1

    print(f"[init] relation files seen:   {rel_files_seen}/{len(SECTION_ORDER)}")
    print(f"[init] total inbound edges:   {total_edges}")
    print(f"[init] unique targets:        {len(inbound)}")

    # 安全检查 + 清空旧反链
    if "_index_by_policy" not in str(OUTPUT_DIR):
        print(f"[fatal] OUTPUT_DIR 路径异常,中止: {OUTPUT_DIR}", file=sys.stderr)
        sys.exit(2)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    old_count = 0
    for old in OUTPUT_DIR.glob("*.md"):
        old.unlink()
        old_count += 1
    if old_count:
        print(f"[init] removed {old_count} old reverse-link files")

    # 生成反链
    written = 0
    for target_id, rels in inbound.items():
        target_meta = id_to_meta.get(target_id, {})
        target_title = target_meta.get("title", "")
        target_file_name = target_meta.get("file_name", "")
        total_inbound = sum(len(v) for v in rels.values())

        # 每个 section 内按 from_date 倒序
        for rel_key in rels:
            rels[rel_key].sort(key=lambda e: e["from_date"] or "", reverse=True)

        # frontmatter dict (保插入顺序,sort_keys=False)
        fm = {
            "policy_id": target_id,
            "title": target_title,
            "inbound_edge_count": total_inbound,
            "last_updated": cn_now_iso(),
        }
        if target_file_name:
            fm["policy_file"] = f"../../../0_raw/policies/{target_file_name}"
        else:
            fm["target_in_vault"] = False

        fm_yaml = yaml.safe_dump(
            fm, allow_unicode=True, default_flow_style=False, sort_keys=False
        ).rstrip()

        lines = ["---", fm_yaml, "---", "", f"# 入向反链:{target_id}", ""]

        for rel_key in SECTION_ORDER:
            if rel_key not in rels:
                continue
            edges = rels[rel_key]
            label = REL_TO_SECTION_LABEL[rel_key]
            lines.append(f"## {label} — {len(edges)}")
            lines.append("")
            for e in edges:
                fid = e["from_id"]
                ftitle = (e["from_title"] or "").strip()
                fdate = (e["from_date"] or "")[:10] or "—"
                if ftitle:
                    lines.append(f"- [[{fid}]] — {ftitle} ({fdate})")
                else:
                    lines.append(f"- [[{fid}]] ({fdate})")
            lines.append("")

        out_file = OUTPUT_DIR / f"{target_id}.md"
        out_file.write_text("\n".join(lines), encoding="utf-8")
        written += 1

    print(f"\n[done] {written} 反链页生成")

    # breakdown
    section_target_count = defaultdict(int)
    for target_id, rels in inbound.items():
        for rel_key in rels:
            section_target_count[rel_key] += 1
    print("\n[breakdown] (target 数 = 有该入向的政策数)")
    for rel in SECTION_ORDER:
        n_targets = section_target_count.get(rel, 0)
        n_edges = sum(
            len(rels[rel]) for target_id, rels in inbound.items() if rel in rels
        )
        print(f"  {rel:<16}  {n_targets:4d} targets  /  {n_edges:4d} edges")


if __name__ == "__main__":
    main()
