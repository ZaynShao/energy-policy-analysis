#!/usr/bin/env python3
"""
validate_l1.py — L1 frontmatter lint(政策 + 评论)

扫 0_raw/policies/*.md + 0_raw/commentaries/*.md(跳过 _archive / _duplicates / .archive),
按 schema_v3 + handoff T1 规则校验 frontmatter。

退出码(对齐 _meta/scripts/lint.py):
  0 = clean
  1 = warnings only
  2 = errors(critical,可作 pre-commit 阻断)

Usage:
  python3 validate_l1.py
  python3 validate_l1.py --strict             # warnings 升级为 errors
  python3 validate_l1.py --quiet              # 只打印 errors
  python3 validate_l1.py --policies-only
  python3 validate_l1.py --commentaries-only
  python3 validate_l1.py --json               # 输出 JSON,供 pre-commit / CI 解析
"""

from __future__ import annotations

import argparse
import datetime as _dt
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

# ─── 规则常量 ─────────────────────────────────────────────────────────────────

POLICY_REQUIRED = ("id", "title", "date", "region")
POLICY_REQUIRED_NESTED = (("provenance", "url"),)
POLICY_SOURCE_TYPE_ENUM = {"A", "B", "C", "D", "E"}
POLICY_REGION_LEVEL_ENUM = {"国家", "省", "市", "区"}

# 评论 v3 必填字段 → 接受的 v2 别名(若 v3 字段缺,fallback 到 v2 别名)
COMMENTARY_REQUIRED_WITH_ALIASES: dict[str, tuple[str, ...]] = {
    "title": ("title",),
    "source_url": ("source_url", "url"),          # v2 用 url
    "date_published": ("date_published", "date"),  # v2 用 date
}
COMMENTARY_TYPE_ENUM = {"A", "B", "C", "D", "unknown"}
RELATED_POLICY_SOURCE_PATTERN = re.compile(r"^(B[1-4]_|manual_).+$")

ISO_TS_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}"
    r"([T ]\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:?\d{2}|Z)?)?$"
)

POLICY_AUDIT_TS_FIELDS = (
    ("provenance", "fetched_at"),
    ("provenance", "body_refetched_at"),
    ("dedup_at",),
)
COMMENTARY_AUDIT_TS_FIELDS = (
    ("fetched_at",),
    ("related_policy_matched_at",),
)

# ─── 数据结构 ─────────────────────────────────────────────────────────────────


@dataclass
class Violation:
    file: str
    kind: str  # "policy" | "commentary"
    level: str  # "error" | "warn"
    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "file": self.file,
            "kind": self.kind,
            "level": self.level,
            "code": self.code,
            "message": self.message,
        }


@dataclass
class Report:
    scanned_policies: int = 0
    scanned_commentaries: int = 0
    violations: list[Violation] = field(default_factory=list)

    def add(self, v: Violation) -> None:
        self.violations.append(v)

    @property
    def errors(self) -> list[Violation]:
        return [v for v in self.violations if v.level == "error"]

    @property
    def warns(self) -> list[Violation]:
        return [v for v in self.violations if v.level == "warn"]


# ─── 解析 ────────────────────────────────────────────────────────────────────


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(\n|$)", re.DOTALL)


def parse_frontmatter(path: Path) -> dict[str, Any] | None:
    """读出 yaml frontmatter dict;无 frontmatter / 解析失败返回 None。"""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    try:
        loaded = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None
    return loaded if isinstance(loaded, dict) else None


def get_nested(d: Any, path: tuple[str, ...]) -> Any:
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def is_iso_ts(value: Any) -> bool:
    """接受 str(YYYY-MM-DD[T ]hh:mm:ss[.us][±hh:mm|Z]) / date / datetime。"""
    if isinstance(value, (_dt.datetime, _dt.date)):
        return True
    if isinstance(value, str):
        return bool(ISO_TS_PATTERN.match(value.strip()))
    return False


def is_date_like(value: Any) -> bool:
    """date 字段:接受 YYYY-MM-DD 或 datetime/date 对象。"""
    if isinstance(value, (_dt.datetime, _dt.date)):
        return True
    if isinstance(value, str):
        return bool(re.match(r"^\d{4}-\d{2}-\d{2}", value.strip()))
    return False


# ─── 校验 ────────────────────────────────────────────────────────────────────


def validate_policy(path: Path, fm: dict[str, Any], report: Report) -> None:
    rel = str(path.relative_to(VAULT))

    def add(level: str, code: str, msg: str) -> None:
        report.add(Violation(rel, "policy", level, code, msg))

    # required top-level
    for key in POLICY_REQUIRED:
        if fm.get(key) in (None, "", []):
            add("error", "missing_required", f"缺必填字段 `{key}`")

    # required nested
    for path_keys in POLICY_REQUIRED_NESTED:
        if get_nested(fm, path_keys) in (None, "", []):
            add(
                "error",
                "missing_required",
                f"缺必填字段 `{'.'.join(path_keys)}`",
            )

    # date 形态
    if "date" in fm and fm["date"] not in (None, "") and not is_date_like(fm["date"]):
        add("error", "bad_date_format", f"`date` 非合法日期: {fm['date']!r}")

    # source_type enum
    st = get_nested(fm, ("provenance", "source_type"))
    if st is not None and st not in POLICY_SOURCE_TYPE_ENUM:
        add(
            "error",
            "enum_violation",
            f"`provenance.source_type` 取值 {st!r} 不在 {sorted(POLICY_SOURCE_TYPE_ENUM)}",
        )

    # region.level enum
    region = fm.get("region")
    if isinstance(region, dict):
        level = region.get("level")
        if level is not None and level not in POLICY_REGION_LEVEL_ENUM:
            add(
                "error",
                "enum_violation",
                f"`region.level` 取值 {level!r} 不在 {sorted(POLICY_REGION_LEVEL_ENUM)}",
            )
        code = region.get("code")
        if code is not None and not (
            isinstance(code, str) and re.match(r"^\d{6}$", code)
        ):
            add(
                "warn",
                "bad_region_code",
                f"`region.code` 非 6 位数字字符串: {code!r}",
            )
    elif region is not None:
        add("error", "bad_region_type", f"`region` 必须是 dict,实际 {type(region).__name__}")

    # audit ts ISO 格式
    for fpath in POLICY_AUDIT_TS_FIELDS:
        v = get_nested(fm, fpath)
        if v is not None and not is_iso_ts(v):
            add(
                "warn",
                "bad_iso_ts",
                f"`{'.'.join(fpath)}` 非 ISO 时间戳: {v!r}",
            )


def validate_commentary(path: Path, fm: dict[str, Any], report: Report) -> None:
    rel = str(path.relative_to(VAULT))

    def add(level: str, code: str, msg: str) -> None:
        report.add(Violation(rel, "commentary", level, code, msg))

    # required(支持 v2 别名兜底,触发 schema_v2_alias warn)
    for v3_key, alias_chain in COMMENTARY_REQUIRED_WITH_ALIASES.items():
        # 找第一个非空字段
        present_key = None
        for k in alias_chain:
            if fm.get(k) not in (None, "", []):
                present_key = k
                break
        if present_key is None:
            add("error", "missing_required", f"缺必填字段 `{v3_key}`(及别名 {list(alias_chain)})")
        elif present_key != v3_key:
            add(
                "warn",
                "schema_v2_alias",
                f"使用 v2 字段 `{present_key}`,建议迁移到 v3 字段 `{v3_key}`",
            )

    # date_published / 其 v2 别名 date 形态
    for date_key in ("date_published", "date"):
        if date_key in fm and fm[date_key] not in (None, ""):
            if not is_date_like(fm[date_key]):
                add(
                    "error",
                    "bad_date_format",
                    f"`{date_key}` 非合法日期: {fm[date_key]!r}",
                )
            break  # 只校验第一个存在的

    # not_policy_related 类型
    if "not_policy_related" in fm and not isinstance(fm["not_policy_related"], bool):
        add(
            "error",
            "bad_type",
            f"`not_policy_related` 必须是 boolean,实际 {fm['not_policy_related']!r}",
        )

    # commentary_type enum (T1 仅 warn,T12 收紧)
    if "commentary_type" in fm and fm["commentary_type"] is not None:
        ct = fm["commentary_type"]
        if ct not in COMMENTARY_TYPE_ENUM:
            add(
                "warn",
                "enum_violation",
                f"`commentary_type` 取值 {ct!r} 不在 {sorted(COMMENTARY_TYPE_ENUM)}",
            )

    # related_policy_source 命名格式
    rps = fm.get("related_policy_source")
    if rps is not None and rps != "":
        if not (isinstance(rps, str) and RELATED_POLICY_SOURCE_PATTERN.match(rps)):
            add(
                "warn",
                "bad_pattern",
                f"`related_policy_source` 不符合 `^(B[1-4]_|manual_).+$`: {rps!r}",
            )

    # related_policy 是 list[str] 才合法
    rp = fm.get("related_policy")
    if rp is not None:
        if not isinstance(rp, list) or not all(isinstance(x, str) for x in rp):
            add(
                "error",
                "bad_type",
                f"`related_policy` 必须是 list[str],实际 {type(rp).__name__}",
            )

    # audit ts ISO 格式
    for fpath in COMMENTARY_AUDIT_TS_FIELDS:
        v = get_nested(fm, fpath)
        if v is not None and not is_iso_ts(v):
            add(
                "warn",
                "bad_iso_ts",
                f"`{'.'.join(fpath)}` 非 ISO 时间戳: {v!r}",
            )


# ─── 扫描入口 ─────────────────────────────────────────────────────────────────


def iter_md_files(root: Path) -> Iterable[Path]:
    """遍历 root 下的 *.md,跳过 SKIP_DIR_NAMES。"""
    if not root.is_dir():
        return
    for p in sorted(root.rglob("*.md")):
        if any(part in SKIP_DIR_NAMES for part in p.relative_to(root).parts):
            continue
        if not p.is_file():
            continue
        yield p


def scan(
    *, do_policies: bool, do_commentaries: bool
) -> Report:
    rep = Report()

    if do_policies:
        for p in iter_md_files(POLICIES_DIR):
            rep.scanned_policies += 1
            fm = parse_frontmatter(p)
            if fm is None:
                rep.add(
                    Violation(
                        str(p.relative_to(VAULT)),
                        "policy",
                        "error",
                        "no_frontmatter",
                        "无法解析 frontmatter(缺失或 yaml 损坏)",
                    )
                )
                continue
            validate_policy(p, fm, rep)

    if do_commentaries:
        for p in iter_md_files(COMMENTARIES_DIR):
            rep.scanned_commentaries += 1
            fm = parse_frontmatter(p)
            if fm is None:
                rep.add(
                    Violation(
                        str(p.relative_to(VAULT)),
                        "commentary",
                        "error",
                        "no_frontmatter",
                        "无法解析 frontmatter(缺失或 yaml 损坏)",
                    )
                )
                continue
            validate_commentary(p, fm, rep)

    return rep


# ─── 输出 ────────────────────────────────────────────────────────────────────


def print_text_report(rep: Report, *, quiet: bool) -> None:
    sep = "─" * 72
    print(f"validate_l1 — scanned policies={rep.scanned_policies}, "
          f"commentaries={rep.scanned_commentaries}")
    print(f"  errors={len(rep.errors)}  warns={len(rep.warns)}")
    print(sep)

    items = rep.errors if quiet else rep.violations
    if not items:
        print("✓ no violations")
        return

    # 按 (level desc, kind, code, file) 排序输出
    level_rank = {"error": 0, "warn": 1}
    items_sorted = sorted(
        items,
        key=lambda v: (level_rank.get(v.level, 9), v.kind, v.code, v.file),
    )

    cur_section: tuple[str, str, str] | None = None
    for v in items_sorted:
        section = (v.level, v.kind, v.code)
        if section != cur_section:
            print()
            print(f"[{v.level.upper()}] {v.kind} / {v.code}")
            cur_section = section
        print(f"  {v.file}: {v.message}")


def print_json_report(rep: Report) -> None:
    out = {
        "scanned": {
            "policies": rep.scanned_policies,
            "commentaries": rep.scanned_commentaries,
        },
        "summary": {
            "errors": len(rep.errors),
            "warns": len(rep.warns),
        },
        "violations": [v.to_dict() for v in rep.violations],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


# ─── CLI ─────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="L1 frontmatter lint(政策 + 评论)")
    ap.add_argument("--strict", action="store_true", help="warnings 升级为 errors")
    ap.add_argument("--quiet", action="store_true", help="只打印 errors")
    ap.add_argument("--policies-only", action="store_true")
    ap.add_argument("--commentaries-only", action="store_true")
    ap.add_argument("--json", dest="as_json", action="store_true",
                    help="JSON 输出(供 pre-commit / CI 解析)")
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

    if rep.errors:
        return 2
    if rep.warns and args.strict:
        return 2
    if rep.warns:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
