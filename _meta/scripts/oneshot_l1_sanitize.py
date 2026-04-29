#!/usr/bin/env python3
"""
oneshot_l1_sanitize.py — L1.2 历史污染净化(2026-04-29 一次性)

把 0_raw/policies/ 263 篇政策的 L2 派生字段 + 业务侧段落迁出到
_meta/business_view/{pid}.yaml,L1 frontmatter/body 保留 raw。

frontmatter 迁出: scores / 重要性 / 行动分类 / 价值标签 / archive
body 删段(到下一个 ## 为止): ## 初步影响分析 / ## 六维评分

跑完即删脚本。原文件备份到 /tmp/l1_sanitize.bak/。
"""

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import yaml

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
RAW = VAULT / "0_raw" / "policies"
BUSINESS_VIEW = VAULT / "_meta" / "business_view"
BACKUP_DIR = Path("/tmp/l1_sanitize.bak")

BUSINESS_FIELDS = ["scores", "重要性", "行动分类", "价值标签", "archive"]

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
H2_RE = re.compile(r"^## ", re.MULTILINE)


def cut_section(body: str, header_re: str):
    """剪掉匹配 header_re 的 H2 段落(到下一个 ## 之前)。返回 (段落内容文本, 剩余 body)。"""
    pat = re.compile(header_re, re.MULTILINE)
    m = pat.search(body)
    if not m:
        return None, body
    h2_start = m.start()
    h2_end = m.end()
    next_h2 = H2_RE.search(body, h2_end)
    sec_end = next_h2.start() if next_h2 else len(body)
    section_text = body[h2_end:sec_end].strip("\n")
    new_body = body[:h2_start] + body[sec_end:]
    return section_text, new_body


def parse_business_section(content: str) -> dict:
    """`**加油业务**: xxx` 三行解析成 dict。"""
    if not content:
        return {}
    out = {}
    for line in content.split("\n"):
        line = line.strip()
        m = re.match(r"\*\*([一-鿿]+业务)\*\*\s*[::]\s*(.+?)\s*$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def collapse_blank_lines(body: str) -> str:
    """删段后合并 3+ 连续空行为 2 个。"""
    return re.sub(r"\n{3,}", "\n\n", body)


def sanitize_file(p: Path) -> dict:
    text = p.read_text(encoding="utf-8")
    m = FM_RE.match(text)
    if not m:
        return {"path": p.name, "skipped": "no frontmatter"}
    fm_text, body = m.group(1), m.group(2)
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as e:
        return {"path": p.name, "error": f"yaml parse: {e}"}

    pid = fm.get("id") or p.stem

    business = {"pid": pid}
    fields_migrated = []
    for k in BUSINESS_FIELDS:
        if k in fm:
            business[k] = fm.pop(k)
            fields_migrated.append(k)

    impact_text, body = cut_section(body, r"^## 初步影响分析\s*$")
    score_text, body = cut_section(body, r"^## 六维评分\s*$")

    if impact_text:
        parsed = parse_business_section(impact_text)
        if parsed:
            business["影响分析"] = parsed
        else:
            business["影响分析_raw"] = impact_text

    business["sanitized_at"] = datetime.now().strftime("%Y-%m-%d")
    business["sanitized_from"] = str(p.relative_to(VAULT))

    body = collapse_blank_lines(body)

    BUSINESS_VIEW.mkdir(parents=True, exist_ok=True)
    bv_path = BUSINESS_VIEW / f"{pid}.yaml"
    bv_path.write_text(
        yaml.safe_dump(business, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )

    new_fm = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, default_flow_style=False)
    new_text = f"---\n{new_fm}---\n{body}"
    p.write_text(new_text, encoding="utf-8")

    return {
        "path": p.name,
        "pid": pid,
        "fm_fields_migrated": fields_migrated,
        "impact_cut": impact_text is not None,
        "score_cut": score_text is not None,
    }


def main():
    dry_run = "--dry-run" in sys.argv
    sample = "--sample" in sys.argv

    if not dry_run and not sample:
        if BACKUP_DIR.exists():
            print(f"⚠️  备份已存在: {BACKUP_DIR}")
            print("   如要重跑,请先 rm -rf 备份或换路径。")
            sys.exit(1)
        print(f"备份 {RAW} → {BACKUP_DIR} ...")
        shutil.copytree(RAW, BACKUP_DIR)

    files = sorted(RAW.glob("*.md"))
    if sample:
        files = files[:3]
    print(f"待处理: {len(files)} 篇" + (" (sample 模式)" if sample else "") + (" (dry-run,不写)" if dry_run else ""))

    if dry_run:
        # 只读不写
        ok = 0
        for p in files[:5]:
            text = p.read_text(encoding="utf-8")
            m = FM_RE.match(text)
            if not m:
                print(f"  [no FM] {p.name}")
                continue
            fm = yaml.safe_load(m.group(1)) or {}
            cut = [k for k in BUSINESS_FIELDS if k in fm]
            print(f"  {p.name[:60]:<60} → 待迁字段: {cut}")
            ok += 1
        print(f"\ndry-run 完成: 检查了 {ok} 篇")
        return

    results = []
    for p in files:
        try:
            r = sanitize_file(p)
            results.append(r)
        except Exception as e:
            results.append({"path": p.name, "error": str(e)})

    ok = sum(1 for r in results if "error" not in r and "skipped" not in r)
    err = sum(1 for r in results if "error" in r)
    skipped = sum(1 for r in results if "skipped" in r)
    impact_cut = sum(1 for r in results if r.get("impact_cut"))
    score_cut = sum(1 for r in results if r.get("score_cut"))

    print(f"\n✅ 完成: ok={ok} error={err} skipped={skipped}")
    print(f"   ## 初步影响分析 段已删: {impact_cut}/{ok}")
    print(f"   ## 六维评分 段已删: {score_cut}/{ok}")

    if err:
        print("\n=== 错误 ===")
        for r in results:
            if "error" in r:
                print(f"  {r['path']}: {r['error']}")


if __name__ == "__main__":
    main()
