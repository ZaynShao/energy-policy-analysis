#!/usr/bin/env python3
"""
extract_entities.py
Step 5 — 357 政策正文 alias substring 匹配 → canonical entity 链接。

输入:
  - 0_raw/policies/*.md
  - 1_extracted/entities/registry.yaml

输出:
  - 1_extracted/entities/_extractions.jsonl  (行级:每条 = 一个 policy↔entity 链接 + hit_count)
  - 1_extracted/entities/_summary.md         (汇总报告)
  注:旧版生成 entities/<type>/<id>.md 反链页已 deprecated(2026-05-07,
       SKILL §8e — 0 外部消费者,registry.yaml 已 self-contained)

策略:
  - alias substring 匹配(中文无词边界,直接 find)
  - 长 alias 优先,匹配后位置 mask(避免短 alias 重复吃)
  - LLM 补抽留给 daily-scan 增量(本步只做 alias 召回)
"""

import re
import json
import yaml
from pathlib import Path
from collections import defaultdict, Counter

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
POLICIES = VAULT / "0_raw" / "policies"
ENTITIES = VAULT / "1_extracted" / "entities"
REGISTRY = ENTITIES / "registry.yaml"
EXTRACTIONS = ENTITIES / "_extractions.jsonl"
SUMMARY = ENTITIES / "_summary.md"

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text):
    m = FM_RE.match(text)
    if not m:
        return None, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None, text
    return fm, text[m.end():]


def load_registry():
    text = REGISTRY.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    entries = yaml.safe_load(parts[2])
    return entries


def build_alias_index(entries):
    """alias → (canonical_id, type, canonical_name)
    aliases 按长度降序,匹配时长的优先(防"虚拟电厂"吃"虚拟电厂运营商")
    跳过 review_needed: true 的 entry(避免占位词如"其他"误命中)"""
    pairs = []
    skipped = 0
    for e in entries:
        if e.get("review_needed"):
            skipped += 1
            continue
        eid = e["id"]
        types = e.get("type", [])
        if isinstance(types, str):
            types = [types]
        primary_type = types[0] if types else "unknown"
        cname = e.get("canonical_name", eid)
        for a in e.get("aliases", []):
            pairs.append((a, eid, primary_type, cname))
    # 按 alias 长度降序排,匹配时优先长 alias
    pairs.sort(key=lambda p: -len(p[0]))
    if skipped:
        print(f"  ({skipped} review_needed entries skipped)")
    return pairs


def match_aliases(body, alias_pairs):
    """对正文做 alias substring 匹配,返回 {canonical_id: (count, matched_alias_set, types, cname)}"""
    # 用 mask 数组标记已匹配位置,避免短 alias 重复吃
    mask = bytearray(len(body))
    hits = defaultdict(lambda: {"count": 0, "matched": set(), "type": None, "name": None})

    for alias, cid, ctype, cname in alias_pairs:
        if len(alias) < 2:
            continue  # 单字 alias 噪声大跳过
        start = 0
        while True:
            idx = body.find(alias, start)
            if idx < 0:
                break
            # 检查 mask:若该区间已被更长 alias 命中,跳过
            if any(mask[i] for i in range(idx, idx + len(alias))):
                start = idx + 1
                continue
            # 命中!打 mask
            for i in range(idx, idx + len(alias)):
                mask[i] = 1
            hits[cid]["count"] += 1
            hits[cid]["matched"].add(alias)
            hits[cid]["type"] = ctype
            hits[cid]["name"] = cname
            start = idx + len(alias)

    return hits


def extract_one(path, alias_pairs):
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    if fm is None:
        return None
    pid = fm.get("id", "")
    title = fm.get("title", "")
    importance = fm.get("重要性", 0)
    region = (fm.get("region") or {}).get("name", "")
    if not pid:
        return None
    hits = match_aliases(body, alias_pairs)
    return {
        "policy_id": pid,
        "title": title,
        "importance": importance,
        "region": region,
        "filename": path.name,
        "hits": {cid: {"count": h["count"], "matched": sorted(h["matched"]), "type": h["type"], "name": h["name"]} for cid, h in hits.items()},
    }


def write_entity_pages(canonical_to_policies, entries_by_id):
    """[DEPRECATED 2026-05-07] 早期生成 entities/<type>/<id>.md 反链页,但实测
    0 外部 [[]] 引用 + 0 脚本消费(只 entity 内部互引 parent 链)。registry.yaml
    + _extractions.jsonl 是 self-contained 数据源,.md 是冗余渲染。详见 SKILL §8e
    「派生 .md 必须有消费者」契约。本函数保留但 main() 不再调用。"""
    return 0
    # 旧实现(保留为参考,如未来要复活实体页 + 加显式引用让其入图):
    type_dirs = {
        "org": ENTITIES / "orgs",
        "stakeholder": ENTITIES / "stakeholders",
        "concept": ENTITIES / "concepts",
        "theme": ENTITIES / "themes",
        "region": ENTITIES / "regions",
    }
    for d in type_dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    written = 0
    for cid, policies in canonical_to_policies.items():
        e = entries_by_id.get(cid)
        if not e:
            continue
        types = e.get("type", [])
        if isinstance(types, str):
            types = [types]
        primary = types[0] if types else "unknown"
        out_dir = type_dirs.get(primary)
        if not out_dir:
            continue

        page_fm = {
            "id": cid,
            "canonical_name": e.get("canonical_name", cid),
            "type": types,
            "aliases": e.get("aliases", []),
            "examples": e.get("examples", []),
            "parent": e.get("parent", ""),
            "desc": e.get("desc", ""),
            "linked_policies": len(policies),
            "generated_by": "extract_entities.py",
            "schema_version": 3.0,
        }
        # sort policies by importance desc, then by date desc
        policies_sorted = sorted(policies, key=lambda p: (-(p.get("importance", 0) or 0), p.get("policy_id", "")))

        lines = []
        lines.append("---")
        lines.append(yaml.dump(page_fm, allow_unicode=True, default_flow_style=False, sort_keys=False).rstrip())
        lines.append("---")
        lines.append("")
        lines.append(f"# {e.get('canonical_name', cid)}")
        lines.append("")
        if e.get("desc"):
            lines.append(f"> {e['desc']}")
            lines.append("")
        lines.append(f"**类型**: {' / '.join(types)}  ")
        if e.get("parent"):
            lines.append(f"**上位实体**: [[{e['parent']}]]  ")
        if e.get("examples"):
            lines.append(f"**典型实例**: {', '.join(e['examples'])}")
        lines.append("")
        lines.append(f"## 别名({len(e.get('aliases', []))})")
        for a in e.get("aliases", []):
            lines.append(f"- {a}")
        lines.append("")
        lines.append(f"## 被引用政策({len(policies)})")
        lines.append("")
        lines.append("| # | 政策 id | 标题 | 重要性 | 命中次数 | 匹配 alias |")
        lines.append("|---|--------|------|:------:|:------:|------|")
        for i, p in enumerate(policies_sorted[:50], 1):  # 前 50 篇,完整列表见 _extractions.jsonl
            t = (p.get("title") or "")[:50]
            imp = p.get("importance", 0) or 0
            cnt = p.get("count", 0)
            matched = ", ".join((p.get("matched") or [])[:3])  # 前 3 alias
            lines.append(f"| {i} | `{p['policy_id']}` | {t} | {imp} | {cnt} | {matched} |")
        if len(policies) > 50:
            lines.append(f"| ... | ({len(policies)-50} 篇略) |  |  |  |  |")
        lines.append("")

        out_path = out_dir / f"{cid}.md"
        out_path.write_text("\n".join(lines), encoding="utf-8")
        written += 1
    return written


def main():
    print("Loading registry...")
    entries = load_registry()
    entries_by_id = {e["id"]: e for e in entries}
    alias_pairs = build_alias_index(entries)
    print(f"  {len(entries)} canonical entities, {len(alias_pairs)} aliases")

    print("Scanning policies...")
    files = sorted(POLICIES.glob("*.md"))
    print(f"  {len(files)} policies")

    EXTRACTIONS.parent.mkdir(parents=True, exist_ok=True)
    canonical_to_policies = defaultdict(list)
    policy_entity_count = Counter()

    with open(EXTRACTIONS, "w", encoding="utf-8") as out:
        for f in files:
            r = extract_one(f, alias_pairs)
            if r is None:
                continue
            for cid, hit in r["hits"].items():
                row = {
                    "policy_id": r["policy_id"],
                    "title": r["title"],
                    "importance": r["importance"],
                    "region": r["region"],
                    "canonical_id": cid,
                    "canonical_name": hit["name"],
                    "canonical_type": hit["type"],
                    "count": hit["count"],
                    "matched": hit["matched"],
                }
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                canonical_to_policies[cid].append({
                    "policy_id": r["policy_id"],
                    "title": r["title"],
                    "importance": r["importance"],
                    "count": hit["count"],
                    "matched": hit["matched"],
                })
            policy_entity_count[r["policy_id"]] = len(r["hits"])

    print(f"  extractions written → {EXTRACTIONS}")

    # entity .md 反链页生成已 deprecated(2026-05-07,SKILL §8e)
    # registry.yaml + _extractions.jsonl 已是 self-contained 数据源,无需 .md 渲染

    # 汇总报告
    print("Writing summary...")
    type_count_with_links = Counter()
    for cid, ps in canonical_to_policies.items():
        e = entries_by_id.get(cid)
        if not e:
            continue
        types = e.get("type", [])
        if isinstance(types, str):
            types = [types]
        for t in types:
            type_count_with_links[t] += 1

    orphans = [e["id"] for e in entries if e["id"] not in canonical_to_policies]
    top_entities = sorted(canonical_to_policies.items(), key=lambda kv: -len(kv[1]))[:20]

    avg_entities = sum(policy_entity_count.values()) / max(1, len(policy_entity_count))
    no_entity = [pid for pid, c in policy_entity_count.items() if c == 0]

    summary = []
    summary.append("---")
    summary.append("title: Step 5 实体抽取汇总")
    summary.append("date: 2026-04-25")
    summary.append("---")
    summary.append("")
    summary.append("# Step 5 · 实体抽取汇总")
    summary.append("")
    summary.append(f"- 输入政策: **{len(files)}**")
    summary.append(f"- registry 实体: **{len(entries)}**")
    summary.append(f"- 命中实体的政策: **{len(policy_entity_count) - len(no_entity)}**")
    summary.append(f"- 零实体命中政策: **{len(no_entity)}**(召回缺口,LLM 补抽 candidate)")
    summary.append(f"- 平均每政策命中实体: **{avg_entities:.1f}**")
    summary.append(f"- 已被引用的 canonical: **{len(canonical_to_policies)}/{len(entries)}**")
    summary.append(f"- 孤儿 canonical(0 政策引用): **{len(orphans)}**")
    summary.append("")
    summary.append("## type 分布(有政策引用的)")
    for t, c in type_count_with_links.most_common():
        summary.append(f"- {t}: {c}")
    summary.append("")
    summary.append("## Top 20 引用最多的实体")
    summary.append("")
    summary.append("| # | canonical_id | 名称 | type | 引用政策数 |")
    summary.append("|---|--------------|------|------|:-----:|")
    for i, (cid, ps) in enumerate(top_entities, 1):
        e = entries_by_id.get(cid, {})
        types = e.get("type", [])
        if isinstance(types, str):
            types = [types]
        summary.append(f"| {i} | `{cid}` | {e.get('canonical_name', '?')} | {' / '.join(types)} | {len(ps)} |")
    summary.append("")
    summary.append("## 孤儿 canonical(0 政策引用,可能是 backup 残余)")
    summary.append("")
    for o in orphans[:30]:
        e = entries_by_id.get(o, {})
        summary.append(f"- `{o}` ({e.get('canonical_name', '?')})")
    if len(orphans) > 30:
        summary.append(f"- ... 共 {len(orphans)} 条")
    summary.append("")
    summary.append("## 零实体命中政策(召回缺口)")
    summary.append("")
    summary.append("这些政策正文里没有任何 alias 命中,LLM 补抽时优先处理。")
    summary.append("")
    for pid in no_entity[:20]:
        summary.append(f"- `{pid}`")
    if len(no_entity) > 20:
        summary.append(f"- ... 共 {len(no_entity)} 条")

    SUMMARY.write_text("\n".join(summary), encoding="utf-8")
    print(f"  summary → {SUMMARY}")
    print()
    print("=== Done ===")
    print(f"政策命中: {len(policy_entity_count) - len(no_entity)}/{len(files)}")
    print(f"实体被引: {len(canonical_to_policies)}/{len(entries)}")
    print(f"孤儿实体: {len(orphans)}")
    print(f"零命中政策: {len(no_entity)}")


if __name__ == "__main__":
    main()
