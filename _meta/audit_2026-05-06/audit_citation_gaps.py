#!/usr/bin/env python3
"""
引用反扫审计(本地无 API,可立刻跑)
扫 vault 全部 raw policies + commentaries body,提取被引用的"政策名称/文号",
对比已收 vault,找出"引用了但 vault 没收"的政策 → 补抓清单

逻辑:
  1. 扫 vault 已收政策的 official_number 集合 + title 集合 = vault_known
  2. 扫 vault 全部 raw body 找文号引用模式 〔YYYY〕N号
  3. 引用集合 - vault_known = 引用-收录差(citation gap)
"""
import os
import re
import yaml
import json
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR = Path(__file__).resolve().parent


def parse_frontmatter(content):
    if not content.startswith("---\n"):
        return {}
    try:
        end = content.index("\n---\n", 4)
        fm = content[4:end]
        return yaml.safe_load(fm) or {}
    except Exception:
        return {}


def main():
    raw_pol = ROOT / "0_raw" / "policies"
    raw_com = ROOT / "0_raw" / "commentaries"

    # Step 1: vault 已收文号集合
    known_official = set()
    known_titles = set()
    for f in sorted(os.listdir(raw_pol)):
        if not f.endswith(".md"):
            continue
        content = (raw_pol / f).read_text()
        fm = parse_frontmatter(content)
        on = fm.get("official_number") or fm.get("official")
        title = fm.get("title", "")
        if on:
            # normalize: 去空格
            known_official.add(re.sub(r"\s+", "", on))
        if title:
            known_titles.add(title.strip())

    print(f"vault 已收文号 unique: {len(known_official)}")
    print(f"vault 已收 title unique: {len(known_titles)}")

    # Step 2: 扫全 vault body 中的文号引用
    cited_official = Counter()  # 文号 → 出现次数
    citation_sources = defaultdict(set)  # 文号 → 在哪些文件被引用

    PATTERN = re.compile(r"([一-龥A-Z]{2,8}?)〔(\d{4})〕\s*(\d{1,5})\s*号")

    for src_dir, src_label in [(raw_pol, "policy"), (raw_com, "commentary")]:
        if not src_dir.exists():
            continue
        for f in sorted(os.listdir(src_dir)):
            if not f.endswith(".md"):
                continue
            try:
                content = (src_dir / f).read_text()
            except Exception:
                continue
            for m in PATTERN.finditer(content):
                full = re.sub(r"\s+", "", m.group(0))
                cited_official[full] += 1
                citation_sources[full].add(f"{src_label}/{f}")

    print(f"vault body 引用文号 unique: {len(cited_official)}")

    # Step 3: 引用-收录差
    gaps = []
    for cited, n in cited_official.most_common():
        if cited in known_official:
            continue
        # 模糊匹配: 文号格式可能空格不同
        normalized = cited.replace(" ", "")
        if normalized in known_official:
            continue
        gaps.append({
            "official_number": cited,
            "citation_count": n,
            "cited_in": list(citation_sources[cited])[:5],
            "status": "uncollected"
        })

    # 写出
    out_md = AUDIT_DIR / "citation_gaps.md"
    summary = []
    summary.append(f"# 引用反扫审计\n")
    summary.append(f"- vault 已收文号: {len(known_official)}")
    summary.append(f"- vault body 引用文号: {len(cited_official)}")
    summary.append(f"- **引用但未收(citation gap)**: {len(gaps)}\n")
    summary.append("## TOP 30 高频引用但未收文号(优先补抓)\n")
    summary.append("| 文号 | 引用次数 | 被引示例 |")
    summary.append("|---|---:|---|")
    for g in sorted(gaps, key=lambda x: -x["citation_count"])[:30]:
        sample = g["cited_in"][0] if g["cited_in"] else ""
        summary.append(f"| {g['official_number']} | {g['citation_count']} | {sample[:60]} |")
    out_md.write_text("\n".join(summary))

    out_json = AUDIT_DIR / "citation_gaps.json"
    out_json.write_text(json.dumps(gaps, ensure_ascii=False, indent=2))

    print(f"\n=== 引用反扫审计完成 ===")
    print(f"摘要 -> {out_md}")
    print(f"缺口清单 -> {out_json}")


if __name__ == "__main__":
    main()
