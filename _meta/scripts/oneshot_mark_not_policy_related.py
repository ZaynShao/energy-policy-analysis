#!/usr/bin/env python3
"""
oneshot_mark_not_policy_related.py — A1 评论批量标记(2026-04-29 一次性)

按 4 条规则给 0_raw/commentaries/*.md frontmatter 加 not_policy_related: true:
  R1 标题命中 JUNK_TITLE(化工油气行情/价格行情/月报/库存产销/订单招投标/法律新闻)
  R2 source_account ∈ {隆众资讯订阅号, 卓创资讯, 人民网研究院}
  R3 business_tag=gas AND 标题含化工油气词
  R4 兜底:无政策核心词 AND 无垃圾词 AND source_account 不在 17 号白名单

frontmatter 写入(关系网例外允许,见 CLAUDE.md L48-57 + SOP Step 6.5):
  not_policy_related: true
  not_policy_related_reason: R1|R2|R3|R4

跑完即删脚本。原文件备份到 _meta/backup/2026-04-29-mark-npr/。

用法:
  python oneshot_mark_not_policy_related.py --dry-run            # 只统计 + 抽样
  python oneshot_mark_not_policy_related.py --dry-run --r4-mode skip   # R4 跳过
  python oneshot_mark_not_policy_related.py --apply              # 实写(R1-R4 全开)
  python oneshot_mark_not_policy_related.py --apply --r4-mode skip
"""
from __future__ import annotations

import argparse
import random
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import yaml

# 共享正则模块
sys.path.insert(0, str(Path(__file__).parent))
from _noise_patterns import (  # noqa: E402
    BLACKLIST_ACCOUNTS,
    GAS_CHEM_TITLE,
    POLICY_WORDS,
    junk_title_bucket,
)

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
COMMENTARIES = VAULT / "0_raw" / "commentaries"
BACKUP_DIR = VAULT / "_meta" / "backup" / "2026-04-29-mark-npr"

# wewe_rss_to_commentaries.py L41-67 ACCOUNT_BUSINESS_MAP 的 17 号白名单
WHITELIST_ACCOUNTS: set[str] = {
    "中能传媒研究院",
    "中国电力企业联合会",
    "储能与电力市场",
    "电力市场与价格洞察",
    "高工储能",
    "国网能源研究院有限公司",
    "落基山研究所",
    "电动汽车观察家",
    "中国石油经济技术研究院",
    "中石油经研院 智库研究中心",
    "卓创资讯",
    "隆众资讯",
    "隆众资讯订阅号",
    "36碳",
    "金杜律师事务所",
    "金杜研究",
    "中央财经大学绿色金融国际研究院",
    "中央财经大学IIGF",
    "中国(深圳)综合开发研究院",
    "综合开发研究院",
    "人民网研究院",
    "能源评论",
    "能源评论•首席能源观",
}

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def parse_frontmatter(p: Path) -> tuple[dict | None, str | None, str | None]:
    """返回 (fm dict, fm_text, body) 或 (None, None, None) 解析失败。"""
    text = p.read_text(encoding="utf-8")
    m = FM_RE.match(text)
    if not m:
        return None, None, None
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None, None, None
    return fm, m.group(1), m.group(2)


def is_already_linked(fm: dict) -> bool:
    rp = fm.get("related_policy")
    return rp not in (None, "", [], "~")


def classify(fm: dict, title: str, r4_mode: str) -> tuple[str | None, str]:
    """
    返回 (rule_id, detail)。rule_id 命中 R1/R2/R3/R4 之一,或 None(放行)。
    r4_mode: "apply"(R4 全标) | "skip"(跳过 R4)
    """
    account = (fm.get("source_account") or "").strip()
    btag = (fm.get("business_tag") or "").strip().lower()

    # R1: 标题命中 JUNK_TITLE
    bucket = junk_title_bucket(title)
    if bucket:
        return "R1", bucket

    # R2: 三号黑名单
    if account in BLACKLIST_ACCOUNTS:
        return "R2", account

    # R3: gas + 化工油气标题词
    if btag == "gas" and GAS_CHEM_TITLE.search(title or ""):
        return "R3", "gas+化工词"

    # R4: 兜底
    if r4_mode == "skip":
        return None, ""
    has_policy = bool(POLICY_WORDS.search(title or ""))
    if not has_policy and account not in WHITELIST_ACCOUNTS:
        return "R4", "no_policy_signal+非白名单号"

    return None, ""


def write_frontmatter(p: Path, fm: dict, body: str) -> None:
    new_fm = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, default_flow_style=False)
    p.write_text(f"---\n{new_fm}---\n{body}", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true", help="只统计 + 抽样,不写")
    g.add_argument("--apply", action="store_true", help="实写 frontmatter")
    ap.add_argument(
        "--r4-mode",
        choices=["apply", "skip"],
        default="apply",
        help="R4 兜底规则:apply=直接全标 / skip=跳过(默认 apply)",
    )
    ap.add_argument("--samples-per-reason", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    if args.apply:
        if BACKUP_DIR.exists():
            print(f"⚠️  备份已存在: {BACKUP_DIR}")
            print("   如要重跑,请先 rm -rf 备份或换路径。")
            sys.exit(1)
        print(f"备份 {COMMENTARIES} → {BACKUP_DIR} ...")
        BACKUP_DIR.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(COMMENTARIES, BACKUP_DIR)

    files = sorted(COMMENTARIES.glob("*.md"))
    print(
        f"待处理: {len(files)} 篇 | r4_mode={args.r4_mode} | "
        f"模式={'dry-run' if args.dry_run else 'apply'}"
    )

    rng = random.Random(args.seed)
    counts: dict[str, int] = defaultdict(int)
    detail_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    samples: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    skipped_already_linked = 0
    skipped_already_npr = 0
    skipped_no_fm = 0
    written = 0
    errors: list[str] = []

    # 第一遍:分类(reservoir 抽样)
    classified: list[tuple[Path, dict, str, str]] = []
    for p in files:
        fm, _, body = parse_frontmatter(p)
        if fm is None:
            skipped_no_fm += 1
            continue
        if is_already_linked(fm):
            skipped_already_linked += 1
            continue
        if fm.get("not_policy_related") is True:
            skipped_already_npr += 1
            continue

        title = (fm.get("title") or p.stem).strip()
        rule, detail = classify(fm, title, args.r4_mode)

        if rule is None:
            counts["放行(留给 A2 LLM)"] += 1
            samples["放行"].append((p.name, fm.get("source_account") or "", title))
            continue

        counts[rule] += 1
        detail_counts[rule][detail] += 1
        if len(samples[rule]) < args.samples_per_reason * 4:  # reservoir 留多再抽
            samples[rule].append((p.name, fm.get("source_account") or "", title))
        elif rng.random() < 0.1:
            samples[rule][rng.randrange(len(samples[rule]))] = (
                p.name,
                fm.get("source_account") or "",
                title,
            )
        classified.append((p, fm, rule, body))

    # 总览
    print("\n=== 分类统计 ===")
    print(f"  跳过(已 linked): {skipped_already_linked}")
    print(f"  跳过(已标 not_policy_related): {skipped_already_npr}")
    print(f"  跳过(无 frontmatter): {skipped_no_fm}")
    for rule in ("R1", "R2", "R3", "R4"):
        n = counts.get(rule, 0)
        print(f"  {rule}: {n}")
        for d, c in sorted(detail_counts[rule].items(), key=lambda x: -x[1]):
            print(f"      {d}: {c}")
    pas = counts.get("放行(留给 A2 LLM)", 0)
    print(f"  放行(留给 A2 LLM): {pas}")

    total_flagged = sum(counts.get(r, 0) for r in ("R1", "R2", "R3", "R4"))
    expected_total = (
        skipped_already_linked + skipped_already_npr + skipped_no_fm + total_flagged + pas
    )
    print(f"\n  合计标 not_policy_related: {total_flagged}")
    print(f"  分母校验: {expected_total} == {len(files)}? {expected_total == len(files)}")

    # 关联率预测
    new_npr = skipped_already_npr + total_flagged
    if (len(files) - new_npr) > 0:
        rate = skipped_already_linked / (len(files) - new_npr) * 100
        print(
            f"\n  预期关联率: {skipped_already_linked} / "
            f"({len(files)} - {new_npr}) = {rate:.1f}%"
        )

    # 抽样
    print("\n=== 每规则抽样 ===")
    for rule in ("R1", "R2", "R3", "R4", "放行"):
        sams = samples.get(rule, [])
        if not sams:
            continue
        print(f"\n[{rule}] (随机 {min(args.samples_per_reason, len(sams))} / 总 {counts.get(rule if rule != '放行' else '放行(留给 A2 LLM)', 0)}):")
        for fname, acc, title in sams[: args.samples_per_reason]:
            print(f"  • [{acc}] {title[:80]}")

    if args.dry_run:
        print("\n(dry-run,未写文件)")
        return

    # 第二遍:实写 frontmatter
    today = datetime.now().strftime("%Y-%m-%d")
    for p, fm, rule, body in classified:
        try:
            fm["not_policy_related"] = True
            fm["not_policy_related_reason"] = rule
            fm["not_policy_related_marked_at"] = today
            write_frontmatter(p, fm, body)
            written += 1
        except Exception as e:
            errors.append(f"{p.name}: {e}")

    print(f"\n✅ 实写完成: written={written} errors={len(errors)}")
    if errors:
        print("\n=== 错误 ===")
        for e in errors[:10]:
            print(f"  {e}")


if __name__ == "__main__":
    main()
