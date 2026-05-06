#!/usr/bin/env python3
"""
build_global_index.py
P1 — 生成 2_crystallized/_global_index.md 顶层数据仪表盘

按 schema §10:
- 总政策数 / 总评论数 / 总实体数
- 按 theme / region / issuer 的分布
- 近 30 天新增 Top N
- 关系网密度
- 链接到所有 themes/ + regions/
"""

import yaml, re, json
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
POL = VAULT / "0_raw/policies"
COM = VAULT / "0_raw/commentaries"
REG = VAULT / "1_extracted/entities/registry.yaml"
RELATIONS = VAULT / "1_extracted/relations"
OPINIONS = VAULT / "1_extracted/opinions"
THEMES = VAULT / "2_crystallized/themes"
REGIONS = VAULT / "2_crystallized/regions"
BUSINESS_VIEW = VAULT / "_meta/business_view"
OUT = VAULT / "2_crystallized/_global_index.md"

CST = timezone(timedelta(hours=8))
fm_re = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)


def load_importance_by_pid() -> dict:
    """读 _meta/business_view/{pid}.yaml 的「重要性」(L1.2 已迁移)。"""
    out = {}
    if not BUSINESS_VIEW.exists():
        return out
    for f in BUSINESS_VIEW.glob("*.yaml"):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            imp = data.get("重要性")
            if imp is not None:
                out[f.stem] = int(imp)
        except (yaml.YAMLError, ValueError, OSError):
            continue
    return out


_IMPORTANCE_CACHE = None


def get_importance(pid: str, fm: dict) -> int:
    """统一入口:优先 business_view yaml,fallback raw fm 的重要性"""
    global _IMPORTANCE_CACHE
    if _IMPORTANCE_CACHE is None:
        _IMPORTANCE_CACHE = load_importance_by_pid()
    if pid and pid in _IMPORTANCE_CACHE:
        return _IMPORTANCE_CACHE[pid]
    return fm.get("重要性") or 0


def cn_now_iso():
    return datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def main():
    # 1. policies
    policies = []
    for f in POL.glob('*.md'):
        text = f.read_text(encoding='utf-8')
        m = fm_re.match(text)
        if not m: continue
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            continue
        policies.append({
            'id': fm.get('id'),
            'title': fm.get('title', ''),
            'date': str(fm.get('date') or '')[:10],
            'importance': get_importance(fm.get('id'), fm),
            'tags': fm.get('tags') or [],
            'issuer': fm.get('issuer') or [],
            'issuer_canonical': fm.get('issuer_canonical') or [],
            'region': fm.get('region') or {},
            'filename': f.name,
            'fetched_at': str((fm.get('provenance') or {}).get('fetched_at') or '')[:10],
        })

    n_policies = len(policies)
    n_commentaries = sum(1 for _ in COM.glob('*.md'))

    # 2. entities
    entities = []
    for d in yaml.safe_load_all(REG.open(encoding='utf-8')):
        if isinstance(d, list): entities.extend(d)
        elif isinstance(d, dict): entities.append(d)
    n_entities = len(entities)
    type_counter = Counter()
    for e in entities:
        for t in e.get('type') or []:
            type_counter[t] += 1

    # 3. relations
    rel_counts = {}
    for ef in ['supersedes', 'iterates', 'extends', 'clarifies', 'references',
               'aligns_with', 'conflicts_with', 'cites_basis']:
        path = RELATIONS / f"{ef}.jsonl"
        if path.exists():
            with path.open() as f:
                rel_counts[ef] = sum(1 for line in f if line.strip())
        else:
            rel_counts[ef] = 0
    total_edges = sum(rel_counts.values())
    n_index_pages = sum(1 for _ in (RELATIONS / "_index_by_policy").glob('*.md')) if (RELATIONS / "_index_by_policy").exists() else 0
    density = total_edges / max(1, n_policies * (n_policies - 1))

    # 4. opinions
    n_opinions = sum(1 for _ in OPINIONS.glob('_op_P_*.md'))
    opinion_pct = n_opinions / max(1, n_policies) * 100

    # 5. tags / region / issuer 分布
    tag_counter = Counter()
    region_level_counter = Counter()
    region_name_counter = Counter()
    issuer_canonical_counter = Counter()
    for p in policies:
        for t in p['tags']:
            tag_counter[t] += 1
        region_level_counter[p['region'].get('level', '?')] += 1
        region_name_counter[p['region'].get('name', '?')] += 1
        for ic in p['issuer_canonical']:
            issuer_canonical_counter[ic] += 1

    # 6. 近 30 天新增(基于 fetched_at)
    today = datetime.now(CST).date()
    last_30 = []
    for p in policies:
        fa = p['fetched_at']
        if not fa or len(fa) < 10: continue
        try:
            d = datetime.strptime(fa[:10], '%Y-%m-%d').date()
            if (today - d).days <= 30:
                last_30.append(p)
        except ValueError:
            continue
    last_30.sort(key=lambda p: -p['importance'])

    # 7. themes 列表
    theme_dirs = sorted([d for d in THEMES.iterdir() if d.is_dir()])
    region_dirs = sorted([d for d in REGIONS.iterdir() if d.is_dir()])

    # 8. 渲染
    lines = ['---',
             f'title: 政策分析全局大盘',
             f'last_updated: {cn_now_iso()}',
             f'policy_count: {n_policies}',
             f'commentary_count: {n_commentaries}',
             f'entity_count: {n_entities}',
             f'edge_count: {total_edges}',
             f'opinion_coverage_pct: {opinion_pct:.1f}',
             '---', '',
             '# 政策分析全局大盘', '',
             f'**最后更新**: {cn_now_iso()}', '', '---', '', '## 1. 数据规模', '',
             '| 类型 | 数量 |',
             '|---|:-:|',
             f'| 政策原文 (policies/) | **{n_policies}** |',
             f'| 评论 (commentaries/) | **{n_commentaries}** |',
             f'| 规范化实体 (entities/registry) | **{n_entities}** |',
             f'| 关系网总边数 | **{total_edges}** |',
             f'| 反链页 (_index_by_policy) | **{n_index_pages}** |',
             f'| 政策舆论矩阵 (opinions) | **{n_opinions}** ({opinion_pct:.1f}% 覆盖率) |',
             f'| 演进差异页 (diffs) | **{sum(1 for _ in (VAULT/"1_extracted/diffs").glob("*.md"))}** |',
             '', '---', '', '## 2. 关系网分布', '',
             '| 关系类型 | 边数 | 含义 |',
             '|---|:-:|---|',
             f'| supersedes | {rel_counts.get("supersedes", 0)} | 显式废止 |',
             f'| iterates | {rel_counts.get("iterates", 0)} | 版本升级 |',
             f'| extends | {rel_counts.get("extends", 0)} | 范围扩展 |',
             f'| clarifies | {rel_counts.get("clarifies", 0)} | 实施细化 |',
             f'| references | {rel_counts.get("references", 0)} | 文号/标题引用 |',
             f'| aligns_with | {rel_counts.get("aligns_with", 0)} | 同向对齐 |',
             f'| conflicts_with | {rel_counts.get("conflicts_with", 0)} | 口径冲突 |',
             f'| cites_basis | {rel_counts.get("cites_basis", 0)} | 制定依据 |',
             '',
             f'**关系网密度**:{total_edges} / {n_policies}×({n_policies}-1) = {density*1000:.2f} ‰',
             '',
             '---', '', '## 3. 实体分布', '',
             '| type | 数量 |',
             '|---|:-:|']
    for t, n in type_counter.most_common():
        lines.append(f'| {t} | {n} |')

    lines.extend(['', '---', '', '## 4. region 分布', '',
                  '| level | 数量 |',
                  '|---|:-:|'])
    for lv, n in sorted(region_level_counter.items(), key=lambda x: -x[1]):
        lines.append(f'| {lv} | {n} |')

    lines.extend(['', '### Top 10 region.name(按政策数)', ''])
    for name, n in sorted(region_name_counter.items(), key=lambda x: -x[1])[:10]:
        lines.append(f'- {name}: {n} 篇')

    lines.extend(['', '---', '', '## 5. 主题(theme)结晶页', '',
                  f'共 {len(theme_dirs)} 个主题已结晶,详见 [`themes/`](themes/):', ''])
    for d in theme_dirs:
        lines.append(f'- [[{d.name}]]')

    lines.extend(['', '---', '', '## 6. region 索引页', '',
                  f'共 {len(region_dirs)} 个区域索引(≥3 篇政策的省/市/区),详见 [`regions/`](regions/):', ''])
    for d in region_dirs:
        lines.append(f'- [[{d.name}]]')

    lines.extend(['', '---', '', '## 7. Top 10 issuer_canonical(按政策数)', ''])
    for ic, n in issuer_canonical_counter.most_common(10):
        lines.append(f'- `{ic}`: {n}')

    lines.extend(['', '---', '', '## 8. Top 15 tags', ''])
    for t, n in tag_counter.most_common(15):
        lines.append(f'- {t}: {n}')

    lines.extend(['', '---', '', f'## 9. 近 30 天新增 Top 10(按重要性排序)', ''])
    if last_30:
        for p in last_30[:10]:
            star = '⭐' * (p['importance'] or 0) if p['importance'] else '—'
            lines.append(f"- {p['date']}  {star}  [[{p['filename'].replace('.md', '')}|{p['title']}]]")
    else:
        lines.append('(近 30 天无新增,或 fetched_at 字段缺失)')

    lines.extend(['', '---', '', '## 10. 数据健康指标', '',
                  f'- **opinion 覆盖率**: {opinion_pct:.1f}% ({n_opinions}/{n_policies}) {"⚠️" if opinion_pct < 30 else "✓"}',
                  f'- **issuer_canonical 覆盖**: {sum(1 for p in policies if p["issuer_canonical"])}/{n_policies}',
                  f'- **5 星政策(高重要性)**: {sum(1 for p in policies if p["importance"] == 5)}',
                  f'- **冲突边密度**: {rel_counts.get("conflicts_with", 0)}/{total_edges} {"⚠️ 0 条" if rel_counts.get("conflicts_with", 0) == 0 else ""}',
                  ])

    OUT.write_text('\n'.join(lines), encoding='utf-8')
    print(f'[done] {OUT.relative_to(VAULT)}')


if __name__ == "__main__":
    main()
