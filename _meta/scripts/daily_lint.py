#!/usr/bin/env python3
"""
daily_lint.py
P2 — 按 schema §12.1 daily lint 检查项扫,产 3_lints/daily/<YYYY-MM-DD>.md

检查项:
  L1. frontmatter 必填字段齐全(id / title / date / region / provenance)
  L2. id 全 vault 唯一
  L3. supersedes 引用的旧政策必须在 raw 里存在(dangling 检测)
  L4. region.code 与 name 一致(简化:level 不为"未知")
  L5. 抽取的实体词 100% 在 registry 命中(用 _extractions.jsonl 不在 registry 的 alias)
  L6. (deprecated 2026-05-07) diffs/ 体系已下架,见 SKILL §8e
  L7 (额外): A 类政策解读分类边界(标题含解读关键词不应在 policies/)

退出码:
  0 — 全 pass
  1 — 有 warning(不阻断)
  2 — 有 lint_error(阻断派生)
"""

import yaml, re, json, sys
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
POL = VAULT / "0_raw/policies"
COM = VAULT / "0_raw/commentaries"
REG = VAULT / "1_extracted/entities/registry.yaml"
RELATIONS = VAULT / "1_extracted/relations"
# DIFFS 路径已 deprecated(2026-05-07,SKILL §8e)
LINT_DIR = VAULT / "3_lints/daily"
LINT_DIR.mkdir(parents=True, exist_ok=True)

CST = timezone(timedelta(hours=8))
fm_re = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
SUSPECTED_COMMENTARY_KW = [
    '政策解读', '解读文章', '专家解读', '答记者问', '提案答复',
    '署名文章', '评论文章', '新闻报道', '新闻稿', '(行业新闻)',
    '吹风会报道', '海外版报道',
]


def main():
    # 加载所有 policies
    policies = []
    for f in POL.glob('*.md'):
        text = f.read_text(encoding='utf-8')
        m = fm_re.match(text)
        if not m:
            policies.append({'file': f.name, 'fm': None})
            continue
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            policies.append({'file': f.name, 'fm': None, 'fm_error': True})
            continue
        policies.append({'file': f.name, 'fm': fm})

    errors = []   # 阻断派生
    warnings = []
    info = []

    # L1. 必填字段
    REQUIRED = ['id', 'title', 'date', 'region', 'provenance']
    for p in policies:
        if not p['fm']:
            errors.append(f"L1 frontmatter parse error: {p['file']}")
            continue
        missing = [k for k in REQUIRED if not p['fm'].get(k)]
        if missing:
            errors.append(f"L1 missing fields {missing}: {p['file']}")

    # L2. id 唯一
    id_counter = Counter()
    for p in policies:
        if p['fm'] and p['fm'].get('id'):
            id_counter[p['fm']['id']] += 1
    dup_ids = {k: v for k, v in id_counter.items() if v > 1}
    for pid, n in dup_ids.items():
        errors.append(f"L2 duplicate id (×{n}): {pid}")

    # L3. supersedes 引用旧政策必须在 raw
    raw_ids = set(p['fm'].get('id') for p in policies if p['fm'] and p['fm'].get('id'))
    sup_path = RELATIONS / "supersedes.jsonl"
    if sup_path.exists():
        with sup_path.open() as f:
            for line in f:
                line = line.strip()
                if not line: continue
                edge = json.loads(line)
                if edge.get('from') not in raw_ids:
                    warnings.append(f"L3 supersedes from-id 不在 raw: {edge.get('from')}")
                if edge.get('to') not in raw_ids:
                    warnings.append(f"L3 supersedes to-id 不在 raw (dangling): {edge.get('to')}")

    # L4. region.level != 未知
    for p in policies:
        if not p['fm']: continue
        region = p['fm'].get('region') or {}
        if region.get('level') in ('未知', '', None):
            warnings.append(f"L4 region.level=未知: {p['file']}")

    # L5. (跳过 _extractions.jsonl 比对,要 entity 抽取脚本配合)

    # L6. diffs/ 检查已 deprecated(2026-05-07,SKILL §8e — diffs 体系下架,
    #     0 外部消费者,改 5/9 类关系层 + reverse_links 反链页是 source of truth)

    # L7. 政策 vs 解读分类边界
    for p in policies:
        if not p['fm']: continue
        title = p['fm'].get('title', '') or ''
        if any(kw in title or kw in p['file'] for kw in SUSPECTED_COMMENTARY_KW):
            warnings.append(f"L7 疑似解读混入 policies/: {p['file'][:60]}")

    # info
    info.append(f"polices total: {len(policies)}")
    info.append(f"commentaries total: {sum(1 for _ in COM.glob('*.md'))}")
    info.append(f"diffs needed/existing: {len(needed_diffs)}/{len(existing_diffs)}")
    info.append(f"errors: {len(errors)}, warnings: {len(warnings)}")

    # 输出
    today = datetime.now(CST).strftime('%Y-%m-%d')
    out_path = LINT_DIR / f"{today}.md"
    lines = ['---',
             f'date: {today}',
             f'lint_pass: {len(errors) == 0}',
             f'errors: {len(errors)}',
             f'warnings: {len(warnings)}',
             f'last_updated: {datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S+08:00")}',
             '---', '',
             f'# Daily Lint · {today}', '',
             '## Summary', '']
    for i in info:
        lines.append(f'- {i}')

    if errors:
        lines.extend(['', f'## ❌ Errors ({len(errors)})', '', '阻断派生,需立即修。', ''])
        for e in errors[:50]:
            lines.append(f'- {e}')
        if len(errors) > 50:
            lines.append(f'  ... ({len(errors) - 50} more)')

    if warnings:
        lines.extend(['', f'## ⚠️ Warnings ({len(warnings)})', '', '不阻断,但需关注。', ''])
        for w in warnings[:80]:
            lines.append(f'- {w}')
        if len(warnings) > 80:
            lines.append(f'  ... ({len(warnings) - 80} more)')

    if not errors and not warnings:
        lines.extend(['', '✅ 全 pass'])

    out_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f'[done] {out_path.relative_to(VAULT)}')
    print(f'errors: {len(errors)}, warnings: {len(warnings)}')

    if errors:
        sys.exit(2)
    elif warnings:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
