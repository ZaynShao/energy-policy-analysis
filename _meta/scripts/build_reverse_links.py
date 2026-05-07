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
import re
import sys
import yaml
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _isolated_filter import load_exclude_pids  # noqa: E402

VAULT_ROOT = Path.home() / "Documents/Zayn Main/政策分析"
POLICIES_DIR = VAULT_ROOT / "0_raw/policies"
COMMENTARIES_DIR = VAULT_ROOT / "0_raw/commentaries"
RELATIONS_DIR = VAULT_ROOT / "1_extracted/relations"
OUTPUT_DIR = RELATIONS_DIR / "_index_by_policy"

# wikilink-as-pid 形如 [[...XXXX]],XXXX 是 4 位 hex 后缀
WIKILINK_SUFFIX_RE = re.compile(r"\[\[.*?-([0-9a-f]{4})\]\]\s*$", re.IGNORECASE)
PID_RE = re.compile(r"^P_[\w]+$")

CST = timezone(timedelta(hours=8))

# 9 类入向 section 标签(被动式,target 视角)
REL_TO_INBOUND_LABEL = {
    "cites_basis":    "被引为依据 (cited_as_basis_by)",
    "supersedes":     "被废止 (superseded_by)",
    "iterates":       "被迭代 (iterated_by)",
    "extends":        "被扩展 (extended_by)",
    "clarifies":      "被细化 (clarified_by)",
    "references":     "被引用 (referenced_by)",
    "aligns_with":    "被对齐 (aligns_with_by)",
    "conflicts_with": "被冲突 (conflicts_with_by)",
    "derives_from":   "被落地 (landed_by)",
}

# 9 类出向 section 标签(主动式,source 视角)
REL_TO_OUTBOUND_LABEL = {
    "cites_basis":    "引用为依据",
    "supersedes":     "废止了",
    "iterates":       "迭代了",
    "extends":        "扩展了",
    "clarifies":      "细化了",
    "references":     "引用了",
    "aligns_with":    "对齐了",
    "conflicts_with": "冲突于",
    "derives_from":   "派生自",
}

# section 出现顺序
SECTION_ORDER = [
    "cites_basis",
    "supersedes",
    "iterates",
    "extends",
    "clarifies",
    "references",
    "aligns_with",
    "conflicts_with",
    "derives_from",
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


def collect_commentary_inbound(id_to_meta):
    """扫 0_raw/commentaries/*.md 的 related_policy → {policy_pid: [commentary_edge,...]}

    related_policy 字段两种格式:
      1. 规范:  P_xxx_xxxx   → 直接用
      2. 历史 bug: [[【title】-机构-XXXX]]  → 按后缀 4 位 hex 解析,唯一匹配才接受
    无法 resolve 的不渲染(P4 audit 处理)。
    """
    pid_by_suffix = defaultdict(list)
    for pid in id_to_meta:
        suffix = pid[-4:].lower()
        pid_by_suffix[suffix].append(pid)

    inbound = defaultdict(list)
    skipped_dangling = 0
    skipped_ambiguous = 0
    resolved_via_suffix = 0
    resolved_direct = 0

    for cfile in sorted(COMMENTARIES_DIR.glob("*.md")):
        text = cfile.read_text(encoding="utf-8", errors="ignore")
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if not m:
            continue
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            continue
        if fm.get("not_policy_related"):
            continue
        rp = fm.get("related_policy")
        if not rp:
            continue
        if isinstance(rp, str):
            rp = [rp]

        ctitle = (fm.get("title") or cfile.stem).strip()
        cdate = fm.get("date_published") or ""
        if hasattr(cdate, "isoformat"):
            cdate = cdate.isoformat()
        cdate = str(cdate)
        csrc = fm.get("related_policy_source", "")

        for entry in rp:
            if not isinstance(entry, str):
                continue
            entry = entry.strip()
            if not entry:
                continue
            target_pid = None
            if PID_RE.match(entry):
                if entry in id_to_meta:
                    target_pid = entry
                    resolved_direct += 1
                else:
                    skipped_dangling += 1
                    continue
            else:
                sm = WIKILINK_SUFFIX_RE.match(entry)
                if not sm:
                    skipped_dangling += 1
                    continue
                suffix = sm.group(1).lower()
                cands = pid_by_suffix.get(suffix, [])
                if len(cands) == 1:
                    target_pid = cands[0]
                    resolved_via_suffix += 1
                elif len(cands) > 1:
                    skipped_ambiguous += 1
                    continue
                else:
                    skipped_dangling += 1
                    continue

            inbound[target_pid].append({
                "commentary_file": cfile.stem,
                "commentary_title": ctitle,
                "commentary_date": cdate,
                "source": csrc,
            })

    print(f"[commentary] direct P_id 解析: {resolved_direct}")
    print(f"[commentary] 后缀匹配解析:    {resolved_via_suffix}")
    print(f"[commentary] dangling 跳过:    {skipped_dangling}")
    print(f"[commentary] 后缀歧义跳过:    {skipped_ambiguous}")
    print(f"[commentary] 唯一 inbound 政策: {len(inbound)}")
    return inbound


def render_commentary_section(lines, edges):
    """渲染评论入向段(被评论 commented_by)"""
    lines.append(f"## 被评论 (commented_by) — {len(edges)}")
    lines.append("")
    for e in edges:
        cfile = e["commentary_file"]
        ctitle = e.get("commentary_title", "")
        cdate = (e.get("commentary_date") or "")[:10] or "—"
        src = e.get("source") or ""
        suffix = f" [{src}]" if src else ""
        if ctitle and ctitle != cfile:
            lines.append(f"- [[{cfile}]] — {ctitle} ({cdate}){suffix}")
        else:
            lines.append(f"- [[{cfile}]] ({cdate}){suffix}")
    lines.append("")


def render_section(lines, label, edges, peer_key):
    """渲染单个 section,edges 已排序。peer_key='from_id'(入向)或 'to_id'(出向)"""
    lines.append(f"## {label} — {len(edges)}")
    lines.append("")
    for e in edges:
        pid = e[peer_key]
        ptitle = (e.get("peer_title") or "").strip()
        pdate = (e.get("peer_date") or "")[:10] or "—"
        lt = e.get("linkage_type")
        suffix = f" [{lt}]" if lt else ""
        if ptitle:
            lines.append(f"- [[{pid}]] — {ptitle} ({pdate}){suffix}")
        else:
            lines.append(f"- [[{pid}]] ({pdate}){suffix}")
    lines.append("")


def main():
    print(f"[init] vault:    {VAULT_ROOT}")
    print(f"[init] output:   {OUTPUT_DIR}")

    id_to_meta = build_id_to_meta()
    print(f"[init] policies indexed: {len(id_to_meta)}")

    # B7 isolated 过滤:涉及 79 个 noise 政策(news/index_page)的所有边都跳过,
    # 这些政策的 _rev_*.md 不生成,Obsidian graph view 也不会有它们的反链节点
    exclude_pids = load_exclude_pids()
    print(f"[filter] excluding {len(exclude_pids)} main_graph_excluded pids from reverse links")

    # 双向收集:
    #   inbound[to_id][rel]   = list of edges (peer = from)
    #   outbound[from_id][rel] = list of edges (peer = to)
    inbound = defaultdict(lambda: defaultdict(list))
    outbound = defaultdict(lambda: defaultdict(list))
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
                linkage_type = edge.get("linkage_type")

                if not from_id:
                    continue

                # B7 isolated 过滤:from / to 任一是 exclude pid → 跳过该边
                if from_id in exclude_pids or (to_id and to_id in exclude_pids):
                    continue

                # 出向:always 收集(只要 from_id 存在;to 可 null e.g. derives_from to=null)
                from_meta = id_to_meta.get(from_id, {})
                if to_id:
                    to_meta = id_to_meta.get(to_id, {})
                    outbound[from_id][rel].append({
                        "to_id": to_id,
                        "peer_title": to_meta.get("title", ""),
                        "peer_date": to_meta.get("date", ""),
                        "linkage_type": linkage_type,
                    })
                    # 入向:仅 to_id 存在时
                    inbound[to_id][rel].append({
                        "from_id": from_id,
                        "peer_title": from_meta.get("title", ""),
                        "peer_date": from_meta.get("date", ""),
                        "linkage_type": linkage_type,
                    })
                    total_edges += 1

    print(f"[init] relation files seen:   {rel_files_seen}/{len(SECTION_ORDER)}")
    print(f"[init] total edges (with to): {total_edges}")
    print(f"[init] unique inbound targets:  {len(inbound)}")
    print(f"[init] unique outbound sources: {len(outbound)}")

    # commentary inbound (P3 双向化补:评论→政策也进反链页)
    commentary_inbound = collect_commentary_inbound(id_to_meta)
    # B7 过滤:exclude pid 的 commentary inbound 也丢(noise 政策不生成 _rev_*)
    for ep in list(commentary_inbound.keys()):
        if ep in exclude_pids:
            del commentary_inbound[ep]

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

    # 生成双向反链页:任何 pid 在 inbound ∪ outbound ∪ commentary_inbound 任一非空就生成
    all_pids = set(inbound.keys()) | set(outbound.keys()) | set(commentary_inbound.keys())
    written = 0
    for pid in all_pids:
        meta = id_to_meta.get(pid, {})
        title = meta.get("title", "")
        file_name = meta.get("file_name", "")
        in_rels = inbound.get(pid, {})
        out_rels = outbound.get(pid, {})
        comm_edges = commentary_inbound.get(pid, [])
        in_count = sum(len(v) for v in in_rels.values())
        out_count = sum(len(v) for v in out_rels.values())
        comm_count = len(comm_edges)

        # 各 section 内按 peer_date 倒序
        for rel_key in in_rels:
            in_rels[rel_key].sort(key=lambda e: e.get("peer_date") or "", reverse=True)
        for rel_key in out_rels:
            out_rels[rel_key].sort(key=lambda e: e.get("peer_date") or "", reverse=True)
        comm_edges.sort(key=lambda e: e.get("commentary_date") or "", reverse=True)

        fm = {
            "policy_id": pid,
            "title": title,
            "inbound_edge_count": in_count,
            "outbound_edge_count": out_count,
            "commentary_inbound_count": comm_count,
            "last_updated": cn_now_iso(),
        }
        if file_name:
            fm["policy_file"] = f"../../../0_raw/policies/{file_name}"
        else:
            fm["target_in_vault"] = False

        fm_yaml = yaml.safe_dump(
            fm, allow_unicode=True, default_flow_style=False, sort_keys=False
        ).rstrip()

        lines = ["---", fm_yaml, "---", ""]

        # 顶部显式 [[]] 链接到 raw 政策(用真实文件名,不依赖 alias 解析)
        # 这是 Obsidian Graph View 显示 raw 政策不孤立的关键 — alias resolution
        # 在 graph view 不一定可靠,显式文件名 link 是 100% 可靠的 graph 边来源。
        if file_name:
            stem_name = file_name[:-3] if file_name.endswith(".md") else file_name
            lines.append(f"> 政策原文:[[{stem_name}|{title or pid}]]")
            lines.append("")

        # 入向区
        if in_count or comm_count:
            lines.append(f"# 入向反链:{pid}")
            lines.append("")
            for rel_key in SECTION_ORDER:
                if rel_key not in in_rels:
                    continue
                render_section(lines, REL_TO_INBOUND_LABEL[rel_key],
                               in_rels[rel_key], peer_key="from_id")
            if comm_count:
                render_commentary_section(lines, comm_edges)

        # 出向区(双向化新增,2026-04-29)
        if out_count:
            lines.append(f"# 出向引用:{pid}")
            lines.append("")
            for rel_key in SECTION_ORDER:
                if rel_key not in out_rels:
                    continue
                render_section(lines, REL_TO_OUTBOUND_LABEL[rel_key],
                               out_rels[rel_key], peer_key="to_id")

        # 文件名加 _rev_ 前缀避免与 raw 政策的 alias `P_xxx` 命名冲突。
        # Obsidian wiki link 解析优先级:文件名 > alias。同名反链页会"截胡"
        # 所有 [[P_xxx]] 引用,导致 raw 政策本身在 graph view 显示孤立。
        # _rev_ 前缀让 [[P_xxx]] 解析到 raw 政策 alias,反链页通过 [[_rev_P_xxx]]
        # 显式访问(或 Dataview 查 vault)。
        out_file = OUTPUT_DIR / f"_rev_{pid}.md"
        out_file.write_text("\n".join(lines), encoding="utf-8")
        written += 1

    print(f"\n[done] {written} 反链页生成 (双向化)")

    # breakdown
    print("\n[breakdown] (target 数 = 有该方向边的 pid 数)")
    print(f"  {'rel':<16}  {'inbound (T/E)':<20}  {'outbound (T/E)':<20}")
    for rel in SECTION_ORDER:
        in_t = sum(1 for r in inbound.values() if rel in r)
        in_e = sum(len(r[rel]) for r in inbound.values() if rel in r)
        out_t = sum(1 for r in outbound.values() if rel in r)
        out_e = sum(len(r[rel]) for r in outbound.values() if rel in r)
        print(f"  {rel:<16}  {in_t:4d} T / {in_e:4d} E       {out_t:4d} T / {out_e:4d} E")
    comm_t = len(commentary_inbound)
    comm_e = sum(len(v) for v in commentary_inbound.values())
    print(f"  {'commented_by':<16}  {comm_t:4d} T / {comm_e:4d} E       — N/A")


if __name__ == "__main__":
    main()
