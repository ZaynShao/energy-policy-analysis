#!/usr/bin/env python3
"""
oneshot: 把 9 主题 opinions-summary.md 的 §1/§2/§3 段落里 naked P_xxx
转成 [[P_xxx]] wiki link 形式。

§5 未覆盖政策清单已经规范用 [[]],不动。
frontmatter / fenced code block 不动(避免破坏 yaml/code)。

用途:
  - A2b 即时止血(pre trigger B 重生成)
  - 后置兜底(trigger B 重生成后再跑一次,防 LLM 偶发再 naked)

run:
  python3 _meta/scripts/oneshot_wrap_naked_pids_in_opinions_summary.py [--dry-run]
"""
from __future__ import annotations
import argparse
import re
from pathlib import Path

PID_RE = re.compile(r'(?<!\[\[)(?<!\[)\bP_\d{4}_[A-Za-z0-9_]+\b(?!\]\])')


def wrap_naked(text: str) -> tuple[str, int]:
    """对 §1-§3 段落范围内的 naked P_xxx 加 [[]],其余不动。"""
    # 切 frontmatter
    fm_end = -1
    if text.startswith('---'):
        m = re.search(r'\n---\s*\n', text[3:])
        if m:
            fm_end = m.end() + 3
    fm = text[:fm_end] if fm_end >= 0 else ''
    body = text[fm_end:] if fm_end >= 0 else text

    # 在 body 里找 §1 起点 ~ §4 终点(§5 不动)
    s1 = re.search(r'^##\s+1\.\s+共识', body, re.MULTILINE)
    s4_or_5 = re.search(r'^##\s+(?:4|5)\.\s+', body, re.MULTILINE)
    if not s1:
        # 没有 §1 段就不改
        return text, 0
    target_start = s1.start()
    target_end = s4_or_5.start() if s4_or_5 else len(body)

    target_block = body[target_start:target_end]

    # 在 target_block 里跳过 fenced code block
    out_chunks: list[str] = []
    cursor = 0
    code_re = re.compile(r'```.*?```', re.DOTALL)
    n_replaced = 0
    for cm in code_re.finditer(target_block):
        # 处理 cursor → cm.start()
        chunk = target_block[cursor:cm.start()]
        new_chunk, n = _replace_in_chunk(chunk)
        n_replaced += n
        out_chunks.append(new_chunk)
        # code block 原样
        out_chunks.append(target_block[cm.start():cm.end()])
        cursor = cm.end()
    # tail
    tail = target_block[cursor:]
    new_tail, n = _replace_in_chunk(tail)
    n_replaced += n
    out_chunks.append(new_tail)

    new_target = ''.join(out_chunks)
    new_body = body[:target_start] + new_target + body[target_end:]
    return fm + new_body, n_replaced


def _replace_in_chunk(chunk: str) -> tuple[str, int]:
    n = 0
    def sub(m):
        nonlocal n
        n += 1
        return f'[[{m.group(0)}]]'
    return PID_RE.sub(sub, chunk), n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--vault-root', default='.')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    root = Path(args.vault_root).resolve()
    summaries = sorted(root.glob('2_crystallized/themes/*/opinions-summary.md'))
    if not summaries:
        print('no opinions-summary.md found')
        return 1

    total_replaced = 0
    files_changed = 0
    for f in summaries:
        text = f.read_text(encoding='utf-8')
        new, n = wrap_naked(text)
        if n > 0:
            files_changed += 1
            total_replaced += n
            tag = '[DRY]' if args.dry_run else '[WROTE]'
            print(f'{tag} {f.parent.name}: +{n} wraps')
            if not args.dry_run:
                f.write_text(new, encoding='utf-8')
        else:
            print(f'[SKIP] {f.parent.name}: 0 naked')
    print()
    print(f'TOTAL: {total_replaced} naked → wrapped across {files_changed} files'
          + (' (dry-run, not written)' if args.dry_run else ''))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
