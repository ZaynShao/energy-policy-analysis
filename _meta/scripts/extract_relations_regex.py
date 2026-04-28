#!/usr/bin/env python3
"""
extract_relations_regex.py
Step 6a — regex 主导的政策↔政策关系抽取(supersedes / references)。

输入:
  - 0_raw/policies/*.md (357 篇 v3 frontmatter)

输出:
  - 1_extracted/relations/supersedes.jsonl
  - 1_extracted/relations/references.jsonl
  - 1_extracted/relations/_summary_regex.md

策略:
  1. 建立 official_number 反向索引 {prefix〔year〕num号: policy_id}
  2. 扫每篇政策正文,匹配 "X〔YYYY〕Z号" 文号引用
  3. 反查索引 → 命中即生成关系(自引用跳过)
  4. 上下文窗口 30 字判 supersedes / references
  5. sanity check:supersedes 要求 from.date > to.date(否则降级 references)
"""

import re
import json
import yaml
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
POLICIES = VAULT / "0_raw" / "policies"
RELATIONS = VAULT / "1_extracted" / "relations"
RELATIONS.mkdir(parents=True, exist_ok=True)
SUMMARY = RELATIONS / "_summary_regex.md"

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# 文号正则:机构(2-12 中文/字母)+ 〔YYYY〕 + 数字 + 号
DOC_NUM_RE = re.compile(
    r"([一-龥A-Za-z]{2,12})\s*[〔(\[【]\s*(\d{4})\s*[〕)\]】]\s*第?\s*(\d+)\s*号"
)

SUPERSEDE_KW = ["废止", "同时废止", "予以废止", "不再施行", "不再执行",
                "自行失效", "废除", "终止施行", "停止执行", "失效"]


def parse_frontmatter(text):
    m = FM_RE.match(text)
    if not m:
        return None, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None, text
    return fm, text[m.end():]


def normalize_doc_number(s):
    if not s:
        return ""
    s = (s.replace("(", "〔").replace(")", "〕")
         .replace("[", "〔").replace("]", "〕")
         .replace("【", "〔").replace("】", "〕"))
    s = re.sub(r"\s+", "", s)
    return s


def make_key(prefix, year, num):
    return f"{prefix}〔{year}〕{num}号"


def build_index():
    """{key: policy_id} + {policy_id: {title, date, official, body, ...}}"""
    num_index = {}
    meta = {}
    collisions = defaultdict(list)  # key → [policy_ids]

    for f in sorted(POLICIES.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        if fm is None:
            continue
        pid = fm.get("id")
        if not pid:
            continue
        official = fm.get("official_number") or ""
        normalized_official = normalize_doc_number(official)
        m = DOC_NUM_RE.search(normalized_official)
        if m:
            key = make_key(m.group(1), m.group(2), m.group(3))
            collisions[key].append(pid)
            # 第一个为主 index
            if key not in num_index:
                num_index[key] = pid
        meta[pid] = {
            "title": fm.get("title", ""),
            "date": str(fm.get("date") or ""),
            "official": official,
            "filename": f.name,
            "body": body,
            "issuer_short": pid.split("_")[2] if pid.count("_") >= 2 else "?",
        }

    multi = {k: v for k, v in collisions.items() if len(v) > 1}
    return num_index, meta, multi


def detect_relation(context):
    for kw in SUPERSEDE_KW:
        if kw in context:
            return "supersedes", 0.92
    return "references", 0.7


def base_id(pid):
    """剥掉 _a/_b/_c 后缀,得到 sibling 共享的 base"""
    return re.sub(r"_[a-z]$", "", pid)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--references-only", action="store_true",
                        help="只输出 references.jsonl,跳过 supersedes.jsonl(保护 v2 LLM judge 结果)")
    args = parser.parse_args()

    print("Building doc number index...")
    num_index, meta, multi = build_index()
    print(f"  {len(num_index)} unique official numbers")
    print(f"  {len(meta)} policies")
    if multi:
        print(f"  ⚠️  {len(multi)} 文号对多政策(version 重复,选第一个为主):")
        for k, v in list(multi.items())[:5]:
            print(f"    {k} → {v}")

    print("\nScanning bodies for cross-references...")
    pair_evidence = defaultdict(list)  # (from, to, rel) → [evidence dicts]
    total_matches = 0
    self_refs = 0
    sibling_refs = 0  # _a/_b/_c 互引
    same_doc_refs = 0  # 同文号不同 id(数据重复)
    out_of_vault = 0  # 引用了 vault 外的文号

    for from_pid, m_data in meta.items():
        body = m_data["body"]
        if not body:
            continue
        from_date = m_data["date"]
        from_base = base_id(from_pid)
        from_official = normalize_doc_number(m_data["official"])

        for match in DOC_NUM_RE.finditer(body):
            total_matches += 1
            prefix, year, num = match.group(1), match.group(2), match.group(3)
            key = make_key(prefix, year, num)
            target_pid = num_index.get(key)
            if not target_pid:
                out_of_vault += 1
                continue
            if target_pid == from_pid:
                self_refs += 1
                continue
            # sibling 过滤
            if base_id(target_pid) == from_base:
                sibling_refs += 1
                continue
            # 同文号不同 id 过滤(同政策两次入库)
            target_official = normalize_doc_number(meta[target_pid]["official"])
            if from_official and target_official and from_official == target_official:
                same_doc_refs += 1
                continue

            # 上下文 30 字
            cs = max(0, match.start() - 30)
            ce = min(len(body), match.end() + 10)
            context = body[cs:ce].strip()
            context = re.sub(r"\s+", " ", context)

            rel, conf = detect_relation(context)

            # supersedes sanity check: from.date > to.date
            if rel == "supersedes":
                to_date = meta[target_pid]["date"]
                if from_date and to_date and from_date <= to_date:
                    rel = "references"
                    conf = 0.5  # 降级,标低 confidence

            pair = (from_pid, target_pid, rel)
            # 同一对在同一政策里出现多次 → 记 evidence_count,不重复 emit
            pair_evidence[pair].append({
                "context": context[:120],
                "doc_num_matched": match.group(0),
                "confidence": conf,
            })

    print(f"  total doc-num matches: {total_matches}")
    print(f"  self-refs: {self_refs}")
    print(f"  sibling-refs(_a/_b/_c): {sibling_refs}")
    print(f"  same-doc-num-refs(数据重复): {same_doc_refs}")
    print(f"  out-of-vault refs: {out_of_vault}")

    # 按 (from_base, to_base, rel) 去重 — 把 _a/_c/_d 副本合并
    base_pair_evidence = defaultdict(list)  # (from_base, to_base, rel) → [(from_pid, to_pid, ev)]
    for (from_pid, to_pid, rel), evs in pair_evidence.items():
        base_key = (base_id(from_pid), base_id(to_pid), rel)
        for ev in evs:
            base_pair_evidence[base_key].append({
                "from_pid_actual": from_pid,
                "to_pid_actual": to_pid,
                **ev,
            })

    # 写文件
    extracted_at = datetime.now().isoformat(timespec="seconds")
    sup_count = 0
    ref_count = 0
    sup_path = RELATIONS / "supersedes.jsonl"
    ref_path = RELATIONS / "references.jsonl"

    # references-only 模式:supersedes 写到 /dev/null(不动现有 supersedes.jsonl)
    sup_target = "/dev/null" if args.references_only else sup_path

    with open(sup_target, "w", encoding="utf-8") as fsup, \
         open(ref_path, "w", encoding="utf-8") as fref:
        for (from_base, to_base, rel), evidences in base_pair_evidence.items():
            best = max(evidences, key=lambda e: e["confidence"])
            # 用 _a 副本作 representative(若存在)
            from_repr = best["from_pid_actual"]
            to_repr = best["to_pid_actual"]
            row = {
                "from": from_repr,
                "to": to_repr,
                "rel": rel,
                "evidence": best["context"],
                "doc_num_matched": best["doc_num_matched"],
                "evidence_count": len(evidences),
                "confidence": best["confidence"],
                "extracted_by": "regex",
                "extracted_at": extracted_at,
            }
            line = json.dumps(row, ensure_ascii=False)
            if rel == "supersedes":
                fsup.write(line + "\n")
                sup_count += 1
            else:
                fref.write(line + "\n")
                ref_count += 1

    # 汇总
    sup_pairs = [(p, evs) for p, evs in pair_evidence.items() if p[2] == "supersedes"]
    ref_pairs = [(p, evs) for p, evs in pair_evidence.items() if p[2] == "references"]

    # Top 被引用最多的政策(被多少其他政策 reference)
    inbound = defaultdict(int)
    for (f, t, r), evs in pair_evidence.items():
        inbound[t] += 1
    top_inbound = sorted(inbound.items(), key=lambda kv: -kv[1])[:15]

    summary = []
    summary.append("---")
    summary.append("title: Step 6a 政策关系抽取 (regex)")
    summary.append("date: 2026-04-25")
    summary.append("---")
    summary.append("")
    summary.append("# Step 6a · 政策↔政策关系 (regex)")
    summary.append("")
    summary.append(f"- 输入政策: **{len(meta)}**")
    summary.append(f"- 文号唯一索引: **{len(num_index)}** (重复版本 {len(multi)} 组)")
    summary.append(f"- 总文号匹配: **{total_matches}**")
    summary.append(f"- 自引用过滤: {self_refs}")
    summary.append(f"- vault 外引用过滤: {out_of_vault}")
    summary.append(f"- **supersedes**: {sup_count}")
    summary.append(f"- **references**: {ref_count}")
    summary.append("")
    summary.append("## Top 15 被引用最多的政策")
    summary.append("")
    summary.append("| # | 政策 id | 标题 | 入度(被引数) |")
    summary.append("|---|--------|------|:----:|")
    for i, (pid, count) in enumerate(top_inbound, 1):
        title = meta.get(pid, {}).get("title", "?")[:40]
        summary.append(f"| {i} | `{pid}` | {title} | {count} |")
    summary.append("")
    summary.append("## supersedes 样本(前 10)")
    summary.append("")
    for (f, t, r), evs in sup_pairs[:10]:
        ftitle = meta.get(f, {}).get("title", "?")[:30]
        ttitle = meta.get(t, {}).get("title", "?")[:30]
        ev = max(evs, key=lambda e: e["confidence"])
        summary.append(f"- `{f}` → `{t}`")
        summary.append(f"  - {ftitle}  ⟶  {ttitle}")
        summary.append(f"  - evidence: {ev['context']}")
        summary.append("")

    SUMMARY.write_text("\n".join(summary), encoding="utf-8")

    print(f"\n=== Done ===")
    print(f"supersedes: {sup_count} → {sup_path}")
    print(f"references: {ref_count} → {ref_path}")
    print(f"summary: {SUMMARY}")


if __name__ == "__main__":
    main()
