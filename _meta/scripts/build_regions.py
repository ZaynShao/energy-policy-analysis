#!/usr/bin/env python3
"""
build_regions.py
P2 — 为 ≥3 篇政策的省/市级 region 生成 2_crystallized/regions/<region>/<region>.md

每个 region 页含:
- yaml frontmatter (region_name / level / policy_count / last_updated)
- 政策清单(按 date 倒序,wikilink + importance + tags 摘要)
- 主题分布(基于 tags 聚合)
- 时间分布(按年份)
"""

import yaml, re
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timezone, timedelta

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
POL = VAULT / "0_raw/policies"
OUT = VAULT / "2_crystallized/regions"
OUT.mkdir(parents=True, exist_ok=True)

CST = timezone(timedelta(hours=8))
fm_re = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)


def cn_now_iso():
    return datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def safe_filename(s):
    """region 名转文件夹名(去标点 + 空格)"""
    return re.sub(r'[^\w一-鿿]', '_', s)


def main():
    by_region = defaultdict(list)
    for f in POL.glob('*.md'):
        text = f.read_text(encoding='utf-8')
        m = fm_re.match(text)
        if not m: continue
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            continue
        region = fm.get('region') or {}
        level = region.get('level', '')
        name = region.get('name', '')
        if level not in ('省', '市', '区'):
            continue
        by_region[(level, name)].append({
            'id': fm.get('id'),
            'title': fm.get('title', '').strip(),
            'date': str(fm.get('date') or '')[:10],
            'importance': fm.get('重要性') or 0,
            'tags': fm.get('tags') or [],
            'issuer': fm.get('issuer') or [],
            'filename': f.name,
        })

    written = 0
    for (level, name), policies in by_region.items():
        if len(policies) < 3:
            continue
        policies.sort(key=lambda p: p['date'], reverse=True)

        # tags 分布
        tag_counter = Counter()
        for p in policies:
            for t in p['tags']:
                tag_counter[t] += 1

        # 年份分布
        year_counter = Counter()
        for p in policies:
            yr = p['date'][:4] if p['date'] else '?'
            year_counter[yr] += 1

        # 重要性分布
        imp_counter = Counter()
        for p in policies:
            imp_counter[p['importance']] += 1

        slug = safe_filename(name)
        region_dir = OUT / slug
        region_dir.mkdir(exist_ok=True)
        out_file = region_dir / f"{slug}.md"

        fm_out = {
            'region_name': name,
            'region_level': level,
            'policy_count': len(policies),
            'top_tags_5': [t for t, _ in tag_counter.most_common(5)],
            'last_updated': cn_now_iso(),
        }

        lines = ['---',
                 yaml.safe_dump(fm_out, allow_unicode=True, default_flow_style=False, sort_keys=False).rstrip(),
                 '---', '',
                 f'# {name} 政策索引', '',
                 f'共 **{len(policies)}** 篇政策', '',
                 '## 主题分布(Top 10)', '']
        for t, n in tag_counter.most_common(10):
            lines.append(f'- {t}: {n}')

        lines.extend(['', '## 年份分布', ''])
        for yr in sorted(year_counter.keys(), reverse=True):
            lines.append(f'- {yr}: {year_counter[yr]} 篇')

        lines.extend(['', '## 重要性分布', ''])
        for imp in sorted(imp_counter.keys(), reverse=True):
            lines.append(f'- {imp} 星: {imp_counter[imp]} 篇')

        lines.extend(['', '## 政策清单(按发布日期倒序)', ''])
        for p in policies:
            base = p['filename'].replace('.md', '')
            tags_short = ', '.join(p['tags'][:3]) if p['tags'] else ''
            star = '⭐' * (p['importance'] or 0) if p['importance'] else '—'
            lines.append(f"- {p['date']}  [[{base}|{p['title']}]]")
            lines.append(f"  - {star} · {tags_short}")

        out_file.write_text('\n'.join(lines), encoding='utf-8')
        written += 1
        print(f"  ✓ {level}/{name:20s}  {len(policies):3d} 篇 → {out_file.relative_to(VAULT)}")

    print(f"\n[done] {written} region pages written")


if __name__ == "__main__":
    main()
