#!/usr/bin/env python3
"""
extract_relations_heuristic.py
Step 6b — 启发式抽 clarifies / iterates / extends / aligns_with。
conflicts_with 留 LLM 单独做。

输入:
  - 0_raw/policies/*.md (357 篇 frontmatter)
  - 1_extracted/entities/_extractions.jsonl
  - 1_extracted/relations/references.jsonl  (Step 6a 输出)

输出:
  - 1_extracted/relations/clarifies.jsonl
  - 1_extracted/relations/iterates.jsonl
  - 1_extracted/relations/extends.jsonl
  - 1_extracted/relations/aligns_with.jsonl
  - 1_extracted/relations/_summary_heuristic.md

策略:
  - 候选对生成:共享 ≥2 entity 的政策对(过滤掉 sibling)
  - clarifies:A 标题含"实施细则/操作指引/工作指南/解读/操作办法"+ A 在 refs 里引用 B
  - iterates:同 issuer + 标题 jaccard ≥0.5 + A.date > B.date
  - extends:region 跳变(国家↔省↔市↔区)+ 共享 entity ≥3 + 时间相近
  - aligns_with:同 region 级别 + 不同 issuer + 共享 entity ≥3
"""

import re
import json
import yaml
from pathlib import Path
from datetime import datetime
from collections import defaultdict

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
POLICIES = VAULT / "0_raw" / "policies"
EXTRACTIONS = VAULT / "1_extracted" / "entities" / "_extractions.jsonl"
RELATIONS = VAULT / "1_extracted" / "relations"
REFS = RELATIONS / "references.jsonl"
SUMMARY = RELATIONS / "_summary_heuristic.md"

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

CLARIFY_KW = ["实施细则", "操作指引", "操作细则", "操作办法",
              "工作指南", "解读", "工作要点", "执行细则",
              "实施方案", "工作方案"]

LEVEL_RANK = {"国家": 4, "省": 3, "市": 2, "区": 1}


def parse_frontmatter(text):
    m = FM_RE.match(text)
    if not m:
        return None, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None, text
    return fm, text[m.end():]


def base_id(pid):
    return re.sub(r"_[a-z]$", "", pid)


def title_tokens(title):
    """简单分词,2 字以上 token 集合"""
    return set(t for t in re.findall(r"[一-鿿A-Za-z0-9]{2,}", title) if t)


def jaccard(a, b):
    a, b = set(a), set(b)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def date_distance_months(d1, d2):
    """两个 YYYY-MM-DD 字符串的月份差"""
    try:
        y1, m1 = int(d1[:4]), int(d1[5:7])
        y2, m2 = int(d2[:4]), int(d2[5:7])
        return abs((y1 - y2) * 12 + (m1 - m2))
    except (ValueError, IndexError):
        return None


def load_policies():
    policies = {}
    for f in sorted(POLICIES.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        fm, _ = parse_frontmatter(text)
        if fm is None:
            continue
        pid = fm.get("id")
        if not pid:
            continue
        policies[pid] = {
            "id": pid,
            "title": fm.get("title", ""),
            "date": str(fm.get("date") or ""),
            "issuer_short": pid.split("_")[2] if pid.count("_") >= 2 else "?",
            "region_level": (fm.get("region") or {}).get("level", ""),
            "region_name": (fm.get("region") or {}).get("name", ""),
            "importance": fm.get("重要性", 0) or 0,
        }
    return policies


def load_entity_links():
    entity_to_policies = defaultdict(set)
    policy_to_entities = defaultdict(set)
    with open(EXTRACTIONS, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            entity_to_policies[d["canonical_id"]].add(d["policy_id"])
            policy_to_entities[d["policy_id"]].add(d["canonical_id"])
    return entity_to_policies, policy_to_entities


def load_refs():
    refs = set()
    if not REFS.exists():
        return refs
    with open(REFS, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            refs.add((d["from"], d["to"]))
    return refs


def build_candidate_pairs(entity_to_policies, min_shared=2):
    """共享 ≥min_shared entity 的政策对(过滤 sibling)"""
    pair_shared = defaultdict(set)
    for ent, pids in entity_to_policies.items():
        pids_list = sorted(pids)
        for i, p1 in enumerate(pids_list):
            for p2 in pids_list[i + 1:]:
                if base_id(p1) == base_id(p2):
                    continue
                pair = (p1, p2) if p1 < p2 else (p2, p1)
                pair_shared[pair].add(ent)
    return {p: ents for p, ents in pair_shared.items() if len(ents) >= min_shared}


def detect_clarifies(a, b, refs_set):
    if not any(kw in a["title"] for kw in CLARIFY_KW):
        return None
    if (a["id"], b["id"]) not in refs_set:
        return None
    if a["date"] and b["date"] and a["date"] < b["date"]:
        return None  # A 比 B 早,不可能是 clarifies
    matched_kw = next((kw for kw in CLARIFY_KW if kw in a["title"]), "?")
    return {"confidence": 0.88, "matched_kw": matched_kw}


def detect_iterates(a, b):
    if a["issuer_short"] != b["issuer_short"]:
        return None
    if not a["date"] or not b["date"] or a["date"] <= b["date"]:
        return None
    sim = jaccard(title_tokens(a["title"]), title_tokens(b["title"]))
    # 副本噪声过滤:title 几乎相同(≥0.95)+ 时差 <3 月 → 不算 iterates(数据重复)
    if sim >= 0.95:
        return None
    if sim < 0.5:
        return None
    months = date_distance_months(a["date"], b["date"])
    if months is None or months > 60:
        return None
    # 真 iterates 要求时差 ≥3 个月(同一年的小幅修订也算)
    if months < 3:
        return None
    return {"confidence": round(min(0.9, 0.55 + sim * 0.35), 2),
            "title_sim": round(sim, 2),
            "months_apart": months}


def detect_extends(a, b, shared):
    # 阈值:共享 entity ≥6,过滤"两篇都提 nev/国务院"这种弱关联
    if len(shared) < 6:
        return None
    al = LEVEL_RANK.get(a["region_level"], 0)
    bl = LEVEL_RANK.get(b["region_level"], 0)
    if al == bl or al == 0 or bl == 0:
        return None
    if not a["date"] or not b["date"]:
        return None
    months = date_distance_months(a["date"], b["date"])
    if months is None or months > 36:
        return None
    if a["date"] <= b["date"]:
        return None
    # 标题主题相似度 ≥0.1(避免无关跨域政策被误标 extends)
    title_sim = jaccard(title_tokens(a["title"]), title_tokens(b["title"]))
    if title_sim < 0.1:
        return None
    # confidence 与 shared 数 + title sim 相关
    conf = round(min(0.9, 0.55 + (len(shared) - 6) * 0.02 + title_sim * 0.2), 2)
    return {"confidence": conf,
            "direction": f"{b['region_level']}→{a['region_level']}",
            "shared": len(shared),
            "title_sim": round(title_sim, 2),
            "months_apart": months}


def detect_aligns_with(a, b, shared):
    # 阈值:共享 entity ≥4 + title sim ≥0.2
    if len(shared) < 4:
        return None
    if a["region_level"] != b["region_level"]:
        return None
    if a["issuer_short"] == b["issuer_short"]:
        return None
    if not a["date"] or not b["date"]:
        return None
    months = date_distance_months(a["date"], b["date"])
    if months is None or months > 18:
        return None
    title_sim = jaccard(title_tokens(a["title"]), title_tokens(b["title"]))
    if title_sim < 0.2:
        return None
    return {"confidence": round(min(0.85, 0.5 + title_sim * 0.5 + (len(shared) - 4) * 0.02), 2),
            "shared": len(shared),
            "title_sim": round(title_sim, 2),
            "months_apart": months}


def main():
    print("Loading policies, entities, refs...")
    policies = load_policies()
    entity_to_policies, policy_to_entities = load_entity_links()
    refs_set = load_refs()
    print(f"  {len(policies)} policies, {len(entity_to_policies)} entities, {len(refs_set)} refs")

    print("Generating candidate pairs (shared ≥2 entities)...")
    candidates = build_candidate_pairs(entity_to_policies, min_shared=2)
    print(f"  {len(candidates)} candidate pairs")

    out_clarifies = []
    out_iterates = []
    out_extends = []
    out_aligns = []

    extracted_at = datetime.now().isoformat(timespec="seconds")

    for (p1, p2), shared in candidates.items():
        a = policies.get(p1)
        b = policies.get(p2)
        if not a or not b:
            continue

        # clarifies (双向尝试)
        for fr, to in [(a, b), (b, a)]:
            r = detect_clarifies(fr, to, refs_set)
            if r:
                out_clarifies.append({
                    "from": fr["id"], "to": to["id"], "rel": "clarifies",
                    "evidence": f"标题含'{r['matched_kw']}' 且引用 {to['id']}",
                    "confidence": r["confidence"],
                    "extracted_by": "heuristic",
                    "extracted_at": extracted_at,
                })

        # iterates (双向尝试,只 emit 一个方向)
        for fr, to in [(a, b), (b, a)]:
            r = detect_iterates(fr, to)
            if r:
                out_iterates.append({
                    "from": fr["id"], "to": to["id"], "rel": "iterates",
                    "evidence": f"同部委 + 标题相似度 {r['title_sim']} + 时差 {r['months_apart']} 月",
                    "title_sim": r["title_sim"],
                    "months_apart": r["months_apart"],
                    "confidence": r["confidence"],
                    "extracted_by": "heuristic",
                    "extracted_at": extracted_at,
                })
                break

        # extends (双向尝试)
        for fr, to in [(a, b), (b, a)]:
            r = detect_extends(fr, to, shared)
            if r:
                out_extends.append({
                    "from": fr["id"], "to": to["id"], "rel": "extends",
                    "evidence": f"region 跳变 {r['direction']} + 共享 {r['shared']} entity + 时差 {r['months_apart']} 月",
                    "direction": r["direction"],
                    "shared_entities": r["shared"],
                    "months_apart": r["months_apart"],
                    "confidence": r["confidence"],
                    "extracted_by": "heuristic",
                    "extracted_at": extracted_at,
                })
                break

        # aligns_with (对称,只 emit 一次)
        r = detect_aligns_with(a, b, shared)
        if r:
            out_aligns.append({
                "from": a["id"], "to": b["id"], "rel": "aligns_with",
                "evidence": f"同 {a['region_level']} + 不同 issuer + 共享 {r['shared']} entity + 时差 {r['months_apart']} 月",
                "shared_entities": r["shared"],
                "title_sim": r["title_sim"],
                "months_apart": r["months_apart"],
                "confidence": r["confidence"],
                "extracted_by": "heuristic",
                "extracted_at": extracted_at,
            })

    # 写文件
    for rel_name, rel_list in [("clarifies", out_clarifies),
                                ("iterates", out_iterates),
                                ("extends", out_extends),
                                ("aligns_with", out_aligns)]:
        path = RELATIONS / f"{rel_name}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for r in rel_list:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"  {rel_name}: {len(rel_list)} → {path}")

    # 汇总
    summary = []
    summary.append("---")
    summary.append("title: Step 6b 启发式关系抽取")
    summary.append("date: 2026-04-25")
    summary.append("---")
    summary.append("")
    summary.append("# Step 6b · 启发式关系抽取")
    summary.append("")
    summary.append(f"- 候选对(共享 ≥2 entity): **{len(candidates)}**")
    summary.append(f"- clarifies: **{len(out_clarifies)}**")
    summary.append(f"- iterates: **{len(out_iterates)}**")
    summary.append(f"- extends: **{len(out_extends)}**")
    summary.append(f"- aligns_with: **{len(out_aligns)}**")
    summary.append("")

    for rel_name, rel_list in [("clarifies", out_clarifies),
                                ("iterates", out_iterates),
                                ("extends", out_extends),
                                ("aligns_with", out_aligns)]:
        summary.append(f"## {rel_name} 样本(前 5,按 confidence 降序)")
        summary.append("")
        for r in sorted(rel_list, key=lambda x: -x["confidence"])[:5]:
            from_t = policies.get(r["from"], {}).get("title", "?")[:30]
            to_t = policies.get(r["to"], {}).get("title", "?")[:30]
            summary.append(f"- `{r['from']}` ({from_t})")
            summary.append(f"  → `{r['to']}` ({to_t})")
            summary.append(f"  - {r['evidence']}  ·  conf {r['confidence']}")
        summary.append("")

    SUMMARY.write_text("\n".join(summary), encoding="utf-8")
    print(f"  summary: {SUMMARY}")
    print("\n=== Done ===")


if __name__ == "__main__":
    main()
