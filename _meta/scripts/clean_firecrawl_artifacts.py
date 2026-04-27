#!/usr/bin/env python3
"""
clean_firecrawl_artifacts.py
清理 firecrawl 抓取留下的页面装饰污染(整行匹配,不动嵌入正文的)。

清理模式:
  A. ![alt](<Base64-Image-Removed>)        # 图片占位符(空/有 alt 都删)
  B. [alt](<Base64-Image-Removed>)         # 链接占位符
  C. [](http(s)://...)                     # 空 alt 装饰图链接(99% 是政府网站模板)
  D. [](data:...)                          # 空 alt 内联 data url
  E. [alt](data:image/...)                 # 内联 base64 图片链接

安全规则:
  - 整行 trim 后必须只剩匹配模式,行内有其他内容则不动
  - 政策原文里没有这些 firecrawl 副产品,删了不丢信息

输入: 0_raw/policies/*.md, 0_raw/commentaries/*.md
输出: 原地修改 + summary

用法:
  python3 clean_firecrawl_artifacts.py --dry-run   # 报告但不动文件
  python3 clean_firecrawl_artifacts.py             # 正式跑
"""

import re
import sys
import argparse
from pathlib import Path
from collections import Counter

VAULT_ROOT = Path.home() / "Documents/Zayn Main/政策分析"
TARGET_DIRS = [
    VAULT_ROOT / "0_raw/policies",
    VAULT_ROOT / "0_raw/commentaries",
    VAULT_ROOT / "0_raw/_duplicates",   # dedup 档案区,与 policies 同性质
]

IMG_URL_RE = r'https?://[^)]+\.(?:png|jpg|jpeg|gif|svg|ico|webp|bmp)(?:\?[^)]*)?'

PATTERNS = [
    (re.compile(r'^\s*!\[[^\]]*\]\(<Base64-Image-Removed>\)\s*$'), "A_img_b64_placeholder"),
    (re.compile(r'^\s*\[[^\]]*\]\(<Base64-Image-Removed>\)\s*$'), "B_link_b64_placeholder"),
    (re.compile(rf'^\s*!\[[^\]]*\]\({IMG_URL_RE}\)\s*$'), "C_decoration_image"),
    (re.compile(rf'^\s*\[!\[[^\]]*\]\({IMG_URL_RE}\)\]\([^)]+\)\s*$'), "D_decoration_image_linked"),
    (re.compile(r'^\s*\[\]\(https?://[^)]+\)\s*$'), "E_empty_alt_http_link"),
    (re.compile(r'^\s*!?\[[^\]]*\]\(data:image[^)]+\)\s*$'), "F_inline_base64_image"),
]


def clean_file(path: Path, dry_run: bool):
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    kept = []
    removed = []
    for i, line in enumerate(lines, 1):
        match_label = None
        for regex, label in PATTERNS:
            if regex.match(line):
                match_label = label
                break
        if match_label:
            removed.append((i, match_label, line.strip()[:80]))
        else:
            kept.append(line)

    if removed and not dry_run:
        path.write_text("\n".join(kept), encoding="utf-8")

    return removed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="不动文件,只报告改动量")
    parser.add_argument("--show-samples", type=int, default=0,
                        help="显示前 N 行样本(每个 pattern)")
    args = parser.parse_args()

    files_changed = 0
    total_removed = 0
    by_pattern = Counter()
    samples = {}

    for d in TARGET_DIRS:
        if not d.exists():
            print(f"[warn] dir missing: {d}", file=sys.stderr)
            continue
        for f in sorted(d.rglob("*.md")):
            removed = clean_file(f, args.dry_run)
            if removed:
                files_changed += 1
                total_removed += len(removed)
                for line_no, label, content in removed:
                    by_pattern[label] += 1
                    if args.show_samples and label not in samples:
                        samples[label] = []
                    if args.show_samples and len(samples.get(label, [])) < args.show_samples:
                        samples[label].append(f"  {f.name}:{line_no}  {content}")

    print(f"[summary] {'(dry-run, no files modified)' if args.dry_run else '(files modified)'}")
    print(f"  files changed:        {files_changed}")
    print(f"  total lines removed:  {total_removed}")
    print(f"  by pattern:")
    for label, n in sorted(by_pattern.items()):
        print(f"    {label}: {n}")

    if args.show_samples:
        print(f"\n[samples] (前 {args.show_samples} 条/pattern)")
        for label, lines in samples.items():
            print(f"\n  {label}:")
            for line in lines:
                print(line)


if __name__ == "__main__":
    main()
