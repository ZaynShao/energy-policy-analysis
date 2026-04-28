#!/usr/bin/env python3
"""
extract_references_title_match.py
P1 — references title_match 补漏:扫无文号 《xxx》 引用,通过标题反查匹配。

借 extract_cites_basis.py 的 stage_3c 机制,但放宽:
  - 不限高分政策(全部 263 政策)
  - 不限开头 800 字符(扫全 body)
  - 输出 rel=references(低精度高召回,与 regex 文号匹配并行)

去重:
  - 与现有 references.jsonl(regex 抓的)去重
  - 与 cites_basis.jsonl 去重(避免覆盖严格演进基础)
  - 与 supersedes/iterates/extends/clarifies/aligns_with/conflicts_with 去重

输出:
  - 1_extracted/relations/references.jsonl 追加 (extracted_by=title_match)
  - _meta/references_title_match_summary.md
"""

import json
import re
import sys
import yaml
from pathlib import Path
from datetime import datetime, timezone, timedelta

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
POLICIES = VAULT / "0_raw/policies"
RELATIONS = VAULT / "1_extracted/relations"
REFERENCES = RELATIONS / "references.jsonl"
SUMMARY_OUT = VAULT / "_meta/references_title_match_summary.md"

CST = timezone(timedelta(hours=8))
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
TITLE_QUOTE_RE = re.compile(r"《([^》《]{5,80})》")

EDGE_FILES_TO_CHECK_DEDUP = [
    "supersedes", "iterates", "extends", "clarifies",
    "references", "aligns_with", "conflicts_with", "cites_basis"
]


def parse_fm(text):
    m = FM_RE.match(text)
    if not m:
        return None, text
    try:
        return yaml.safe_load(m.group(1)) or {}, text[m.end():]
    except yaml.YAMLError:
        return None, text


def cn_now_iso():
    return datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def main():
    # 1. 建 title → pid 反查 + meta
    id_to_meta = {}
    title_to_id = {}
    for f in sorted(POLICIES.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        fm, body = parse_fm(text)
        if fm is None:
            continue
        pid = fm.get("id")
        if not pid:
            continue
        title = (fm.get("title") or "").strip()
        id_to_meta[pid] = {"title": title, "body": body}
        if title and title not in title_to_id:
            title_to_id[title] = pid

    print(f"[init] {len(id_to_meta)} policies, {len(title_to_id)} unique titles")

    # 2. 收集已有所有 (from, to) 对(去重用)
    existing_pairs = set()
    for ef in EDGE_FILES_TO_CHECK_DEDUP:
        path = RELATIONS / f"{ef}.jsonl"
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    edge = json.loads(line.strip())
                except (json.JSONDecodeError, ValueError):
                    continue
                fid = edge.get("from")
                tid = edge.get("to")
                if fid and tid:
                    existing_pairs.add((fid, tid))
    print(f"[init] existing edges (dedup): {len(existing_pairs)}")

    # 3. 扫每篇 body 全文
    new_edges = []
    for from_id, meta in id_to_meta.items():
        from_title = meta["title"]
        body = meta["body"] or ""
        if not body:
            continue

        seen_in_this_doc = set()  # (from, to) 单文档去重
        for m in TITLE_QUOTE_RE.finditer(body):
            cited = m.group(1).strip()
            if not cited or cited == from_title:
                continue

            to_id = None
            # 精确匹配
            if cited in title_to_id:
                to_id = title_to_id[cited]
            else:
                # 子串匹配(cited len ≥10,任一互含)
                for cand_title, cand_id in title_to_id.items():
                    if cand_id == from_id:
                        continue
                    if len(cited) >= 10 and (cited in cand_title or cand_title in cited):
                        to_id = cand_id
                        break

            if not to_id or to_id == from_id:
                continue

            pair = (from_id, to_id)
            if pair in existing_pairs:
                continue
            if pair in seen_in_this_doc:
                continue
            seen_in_this_doc.add(pair)
            existing_pairs.add(pair)

            start = max(0, m.start() - 30)
            end = min(len(body), m.end() + 30)
            evidence = body[start:end].replace("\n", " ").strip()[:200]

            new_edges.append({
                "from": from_id,
                "to": to_id,
                "rel": "references",
                "evidence": evidence,
                "title_matched": cited[:80],
                "confidence": 0.8,
                "extracted_by": "title_match",
                "extracted_at": cn_now_iso(),
            })

    print(f"[done] new title_match references: {len(new_edges)}")

    # 4. append to references.jsonl
    if new_edges:
        with REFERENCES.open("a", encoding="utf-8") as f:
            for e in new_edges:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        print(f"[out] appended to {REFERENCES.name}")

    # 5. summary
    from_counter = {}
    for e in new_edges:
        from_counter[e["from"]] = from_counter.get(e["from"], 0) + 1
    top_from = sorted(from_counter.items(), key=lambda x: -x[1])[:15]

    summary = ["# references title_match 补漏报告\n",
               f"- 输入政策: {len(id_to_meta)}",
               f"- 新增 references 边: **{len(new_edges)}**",
               f"- 去重 (与 8 类现有边对照): 已实施",
               "",
               "## Top 15 引用最多的 from 政策",
               ""]
    for pid, n in top_from:
        title = id_to_meta.get(pid, {}).get("title", "?")[:50]
        summary.append(f"- {pid}: {n} 条 ({title})")

    summary.append("")
    summary.append("## 样本(前 10)")
    summary.append("")
    for e in new_edges[:10]:
        summary.append(f"- `{e['from']}` → `{e['to']}` (matched: {e['title_matched'][:30]})")
        summary.append(f"  - evidence: {e['evidence'][:80]}")

    SUMMARY_OUT.write_text("\n".join(summary), encoding="utf-8")
    print(f"[out] summary → {SUMMARY_OUT.name}")


if __name__ == "__main__":
    main()
