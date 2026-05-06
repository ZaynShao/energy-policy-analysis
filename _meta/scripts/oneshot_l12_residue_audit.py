#!/usr/bin/env python3
"""
oneshot_l12_residue_audit.py — L1.2 净化残留 audit

目的:核查 LLM Wiki §1 (raw immutable) + §2 (派生分层) 是否还有破口。

扫描:
  • 0_raw/policies/*.md  + 0_raw/commentaries/*.md
  • 跳过 _archive / _duplicates / .archive 目录(已知例外)

检查项:
  A. frontmatter 违规字段(LLM 派生业务字段不得在 raw fm)
       scores / 重要性 / 影响分析 / 价值标签 / 行动分类 /
       didi_impact_one_liner / 行动建议
  B. body 品牌词(政策侧)
       滴滴 / 能链 / 小桔 / 滴滴能源
       — 政策 body 命中: high(异常,政策原文一般不点名企业)
       — 评论 body 命中: info(评论讨论企业属正常)
  C. body 派生 section 标题残留
       ## 影响分析 / ## 业务影响 / ## 打分 / ## 重要性 / ## 滴滴

退出码:
  0 = clean
  1 = 仅 info
  2 = 有 violation(fm 违规字段或政策 body 派生段残留)

Usage:
  python3 oneshot_l12_residue_audit.py
  python3 oneshot_l12_residue_audit.py --json
  python3 oneshot_l12_residue_audit.py --quiet              # 只打 violation
  python3 oneshot_l12_residue_audit.py --policies-only
  python3 oneshot_l12_residue_audit.py --commentaries-only
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml

# ─── 路径 ─────────────────────────────────────────────────────────────────────

VAULT = Path(__file__).resolve().parents[2]
POLICIES_DIR = VAULT / "0_raw" / "policies"
COMMENTARIES_DIR = VAULT / "0_raw" / "commentaries"
SKIP_DIR_NAMES = {"_archive", "_duplicates", ".archive"}

# ─── 规则 ────────────────────────────────────────────────────────────────────

# A. fm 违规字段(LLM 派生业务字段)
FM_FORBIDDEN_FIELDS = (
    "scores",
    "重要性",
    "影响分析",
    "价值标签",
    "行动分类",
    "didi_impact_one_liner",
    "行动建议",
)

# B. body 品牌词
BRAND_KEYWORDS = (
    "滴滴能源",  # 长串先匹配
    "滴滴",
    "能链",
    "小桔",
)

# C. body 派生 section 标题
BODY_DERIVED_SECTIONS = (
    "## 影响分析",
    "## 业务影响",
    "## 打分",
    "## 重要性",
    "## 滴滴",
    "## 业务标签",
    "## 价值标签",
)

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(\n|$)", re.DOTALL)

# ─── 数据结构 ─────────────────────────────────────────────────────────────────


@dataclass
class Violation:
    file: str
    kind: str           # policy | commentary
    level: str          # violation | info
    code: str           # fm_forbidden_field | body_brand | body_derived_section
    detail: str
    suggestion: str

    def to_dict(self) -> dict[str, str]:
        return {
            "file": self.file,
            "kind": self.kind,
            "level": self.level,
            "code": self.code,
            "detail": self.detail,
            "suggestion": self.suggestion,
        }


@dataclass
class Report:
    scanned_policies: int = 0
    scanned_commentaries: int = 0
    items: list[Violation] = field(default_factory=list)

    @property
    def violations(self) -> list[Violation]:
        return [v for v in self.items if v.level == "violation"]

    @property
    def infos(self) -> list[Violation]:
        return [v for v in self.items if v.level == "info"]


# ─── 解析 ────────────────────────────────────────────────────────────────────


def split_frontmatter_body(text: str) -> tuple[dict[str, Any] | None, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, text
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        fm = None
    body = text[m.end():]
    return (fm if isinstance(fm, dict) else None), body


def iter_md_files(root: Path) -> Iterable[Path]:
    if not root.is_dir():
        return
    for p in sorted(root.rglob("*.md")):
        if any(part in SKIP_DIR_NAMES for part in p.relative_to(root).parts):
            continue
        if not p.is_file():
            continue
        yield p


# ─── 检查 ────────────────────────────────────────────────────────────────────


def _migrated_hint(fm: dict[str, Any]) -> str:
    """如果是 migrated 评论(带 _migrated_from),给针对性建议。"""
    if "_migrated_from" in fm:
        src = fm.get("_migrated_from") or "?"
        return (f"该 commentary 由政策 {src!r} 迁移而来,scores/重要性等业务字段应"
                f"已迁出;请走 oneshot_l1_sanitize 系列脚本删除这些 fm 字段")
    return "走 oneshot_l1_sanitize 系列脚本删除这些 fm 字段(scores 等属 _meta/business_view/)"


def check_frontmatter(
    rel: str, kind: str, fm: dict[str, Any], rep: Report
) -> None:
    hits = [k for k in FM_FORBIDDEN_FIELDS if k in fm]
    if not hits:
        return
    detail = f"含 LLM 派生业务字段 {hits}"
    suggestion = _migrated_hint(fm)
    rep.items.append(Violation(rel, kind, "violation", "fm_forbidden_field", detail, suggestion))


def check_body_brand(rel: str, kind: str, body: str, rep: Report) -> None:
    found: list[tuple[str, int]] = []
    for kw in BRAND_KEYWORDS:
        n = body.count(kw)
        if n:
            found.append((kw, n))
    if not found:
        return

    if kind == "policy":
        # 政策 body 出现品牌词:可疑(政策原文极少点名企业)
        detail = "政策 body 含品牌词: " + ", ".join(f"{k}×{n}" for k, n in found)
        suggestion = "人工审:是否真政策原文(试点企业名单/附录可接受);否则可能 raw 被派生层污染"
        rep.items.append(Violation(rel, kind, "violation", "body_brand", detail, suggestion))
    else:
        # 评论 body 含品牌词:正常(评论本来就讨论企业)
        detail = "评论 body 含品牌词: " + ", ".join(f"{k}×{n}" for k, n in found)
        rep.items.append(Violation(rel, kind, "info", "body_brand", detail, "无需处理(评论讨论企业属正常)"))


def check_body_derived_sections(
    rel: str, kind: str, body: str, rep: Report
) -> None:
    hits: list[str] = []
    for marker in BODY_DERIVED_SECTIONS:
        # 行首匹配 (^marker)
        if re.search(rf"^{re.escape(marker)}\b", body, re.MULTILINE):
            hits.append(marker)
    if not hits:
        return
    detail = f"body 含派生 section 标题: {hits}"
    suggestion = "人工审 raw body 是否被回灌派生内容,需移到派生层并从 raw 删段"
    rep.items.append(Violation(rel, kind, "violation", "body_derived_section", detail, suggestion))


# ─── 扫描入口 ─────────────────────────────────────────────────────────────────


def scan(*, do_policies: bool, do_commentaries: bool) -> Report:
    rep = Report()
    spec = []
    if do_policies:
        spec.append((POLICIES_DIR, "policy"))
    if do_commentaries:
        spec.append((COMMENTARIES_DIR, "commentary"))

    for root, kind in spec:
        for p in iter_md_files(root):
            if kind == "policy":
                rep.scanned_policies += 1
            else:
                rep.scanned_commentaries += 1
            try:
                text = p.read_text(encoding="utf-8")
            except OSError:
                continue
            rel = str(p.relative_to(VAULT))
            fm, body = split_frontmatter_body(text)
            if fm is not None:
                check_frontmatter(rel, kind, fm, rep)
            check_body_brand(rel, kind, body, rep)
            check_body_derived_sections(rel, kind, body, rep)

    return rep


# ─── 输出 ────────────────────────────────────────────────────────────────────


def print_text_report(rep: Report, *, quiet: bool) -> None:
    sep = "─" * 72
    print("oneshot_l12_residue_audit — "
          f"scanned policies={rep.scanned_policies}, "
          f"commentaries={rep.scanned_commentaries}")
    print(f"  violations={len(rep.violations)}  infos={len(rep.infos)}")
    print(sep)

    items = rep.violations if quiet else rep.items
    if not items:
        print("✓ no residue detected")
        return

    rank = {"violation": 0, "info": 1}
    items_sorted = sorted(
        items,
        key=lambda v: (rank.get(v.level, 9), v.kind, v.code, v.file),
    )

    cur: tuple[str, str, str] | None = None
    for v in items_sorted:
        section = (v.level, v.kind, v.code)
        if section != cur:
            print()
            print(f"[{v.level.upper()}] {v.kind} / {v.code}")
            cur = section
        print(f"  {v.file}")
        print(f"    detail: {v.detail}")
        print(f"    suggest: {v.suggestion}")


def print_json_report(rep: Report) -> None:
    out = {
        "scanned": {
            "policies": rep.scanned_policies,
            "commentaries": rep.scanned_commentaries,
        },
        "summary": {
            "violations": len(rep.violations),
            "infos": len(rep.infos),
        },
        "items": [v.to_dict() for v in rep.items],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


# ─── CLI ─────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="L1.2 净化残留 audit(raw fm 违规字段 + body 品牌词)")
    ap.add_argument("--quiet", action="store_true", help="只打 violation")
    ap.add_argument("--policies-only", action="store_true")
    ap.add_argument("--commentaries-only", action="store_true")
    ap.add_argument("--json", dest="as_json", action="store_true")
    args = ap.parse_args(argv)

    if args.policies_only and args.commentaries_only:
        print("ERROR: --policies-only 与 --commentaries-only 互斥", file=sys.stderr)
        return 2

    do_policies = not args.commentaries_only
    do_commentaries = not args.policies_only

    rep = scan(do_policies=do_policies, do_commentaries=do_commentaries)

    if args.as_json:
        print_json_report(rep)
    else:
        print_text_report(rep, quiet=args.quiet)

    if rep.violations:
        return 2
    if rep.infos:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
