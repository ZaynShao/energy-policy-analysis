#!/usr/bin/env python3
"""
oneshot_l1_body_audit.py — L1 raw body 质量全库 audit

目的:扫 271 篇政策原文 body,识别采集异常(PDF 二进制残留 / HTML 残留 /
过短 / 异常长 / title-body 错配),输出可疑政策清单 + 建议处理路径
(重抓 vs 接受)。

检查项:
  1. pdf_binary       body 含 PDF 二进制标记 %PDF / endobj / endstream / stream\n
  2. html_residue     body HTML 标签 > 5(warn 级,firecrawl 残留 <br> 常见,
                       不影响信息完整性,但建议清洗)
  3. body_too_short   < 200 字符
  4. body_too_long    > 1 MB(可能含 base64 图片)
  5. title_body_mismatch
                       jieba 切 title 关键词(前 5)与 body 前 1000 字关键词,
                       title 关键词在 body 关键词中的 recall < 阈值则可疑
                       (P_2024_TJ_01010970 错配类;recall 不受 body 词集大小
                       影响,优于 Jaccard)

退出码:
  0 = clean
  1 = 仅 warn(过长/过短/html_residue)
  2 = 有可疑(pdf_binary / title_body_mismatch)

Usage:
  python3 oneshot_l1_body_audit.py
  python3 oneshot_l1_body_audit.py --json
  python3 oneshot_l1_body_audit.py --quiet
  python3 oneshot_l1_body_audit.py --recall-threshold 0.5
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import yaml

try:
    import jieba
    jieba.setLogLevel(40)  # WARNING+
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False

# ─── 路径 / 阈值 ─────────────────────────────────────────────────────────────

VAULT = Path(__file__).resolve().parents[2]
POLICIES_DIR = VAULT / "0_raw" / "policies"
SKIP_DIR_NAMES = {"_archive", "_duplicates", ".archive"}

BODY_TOO_SHORT = 200            # 字符
BODY_TOO_LONG = 1_048_576       # 1 MB
HTML_TAG_THRESHOLD = 5          # HTML tag 数 > 5 即提示(降为 warn)
DEFAULT_RECALL_THRESHOLD = 0.50  # title 关键词在 body 中命中率 < 此值算错配
TITLE_TOP_K = 5
BODY_PREFIX_FOR_MATCH = 1000     # 用 body 前 N 字符切词
BODY_TOP_K = 30                  # body 关键词集大,提高 recall 命中精度

# PDF 二进制标记
PDF_BINARY_MARKERS = (r"%PDF-", r"endobj", r"endstream", r"\nstream\n")

# HTML 标签 regex(完整开/闭标签)
HTML_TAG_RE = re.compile(r"<(/?\w+)(?:\s[^>]*)?\s*/?>")

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(\n|$)", re.DOTALL)

# 中文停用词(切完后过滤,简洁集合 — 不追求完备)
STOPWORDS = {
    "的", "和", "与", "及", "等", "或", "在", "为", "对", "是", "有", "到",
    "从", "于", "由", "向", "把", "被", "其", "之", "了", "都", "也",
    "本", "该", "此", "其他", "并", "且", "但", "以", "通过", "进行",
    "关于", "根据", "按照", "依据", "针对",
    "通知", "意见", "办法", "方案", "规定", "指南", "细则", "条例",
    "印发", "发布", "实施", "管理", "工作",
}

# ─── 数据结构 ─────────────────────────────────────────────────────────────────


@dataclass
class Issue:
    file: str
    pid: str | None
    title: str | None
    level: str           # suspicious | warn
    code: str
    detail: str
    suggestion: str

    def to_dict(self) -> dict[str, str | None]:
        return {
            "file": self.file,
            "pid": self.pid,
            "title": self.title,
            "level": self.level,
            "code": self.code,
            "detail": self.detail,
            "suggestion": self.suggestion,
        }


@dataclass
class Report:
    scanned: int = 0
    items: list[Issue] = field(default_factory=list)

    @property
    def suspicious(self) -> list[Issue]:
        return [i for i in self.items if i.level == "suspicious"]

    @property
    def warns(self) -> list[Issue]:
        return [i for i in self.items if i.level == "warn"]


# ─── 解析 ────────────────────────────────────────────────────────────────────


def split_frontmatter_body(text: str) -> tuple[dict | None, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, text
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        fm = None
    return (fm if isinstance(fm, dict) else None), text[m.end():]


def iter_md_files(root: Path) -> Iterable[Path]:
    if not root.is_dir():
        return
    for p in sorted(root.rglob("*.md")):
        if any(part in SKIP_DIR_NAMES for part in p.relative_to(root).parts):
            continue
        if p.is_file():
            yield p


# ─── 检查 ────────────────────────────────────────────────────────────────────


def cut_keywords(text: str, top_k: int) -> set[str]:
    """jieba 切词 → 去停用词 → 取前 top_k(按出现顺序去重)。"""
    if not HAS_JIEBA:
        # fallback:简单 2-gram 中文滑窗
        cleaned = re.sub(r"[\s\W_]+", "", text)
        return {cleaned[i:i + 2] for i in range(min(len(cleaned), top_k * 2))}
    seen: list[str] = []
    for w in jieba.cut(text, cut_all=False):
        w = w.strip()
        if not w or w in STOPWORDS:
            continue
        # 单字默认丢弃(信息量低)
        if len(w) < 2:
            continue
        if w in seen:
            continue
        seen.append(w)
        if len(seen) >= top_k:
            break
    return set(seen)


def title_recall(title_kw: set[str], body_kw: set[str]) -> float:
    """title 关键词在 body 关键词中的命中率。

    用 recall 而非 Jaccard:title 通常 3-5 词,body 关键词集大(20-30 词);
    Jaccard 会因分母 |union| 过大而压低分数(假阳性);recall 只关心 title 是否
    被 body "覆盖",对 P_2024_TJ_01010970 这类 title-body 完全不沾的真错配
    依然敏感(recall ≈ 0)。"""
    if not title_kw:
        return 1.0  # 无 title 关键词时不可判,默认通过
    return len(title_kw & body_kw) / len(title_kw)


def check_pdf_binary(body: str) -> str | None:
    """命中返回命中标记列表的字符串,否则 None。"""
    hits = []
    if "%PDF-" in body:
        hits.append("%PDF-")
    if "endobj" in body and "endstream" in body:
        hits.append("endobj+endstream")
    # \nstream\n 后跟疑似 binary(由 chr 0-31 出现)
    if re.search(r"\nstream\n[^\n]*[\x00-\x08\x0e-\x1f]", body):
        hits.append("stream+binary")
    return ", ".join(hits) if hits else None


def check_html_residue(body: str) -> tuple[int, str | None]:
    """
    返回 (tag_count, sample_tags 或 None)。
    tag_count > HTML_TAG_THRESHOLD 才算可疑。
    """
    tags = HTML_TAG_RE.findall(body)
    if len(tags) <= HTML_TAG_THRESHOLD:
        return len(tags), None
    # 取最常见 5 个标签作为样本
    from collections import Counter
    common = Counter(tags).most_common(5)
    sample = ", ".join(f"<{t}>×{n}" for t, n in common)
    return len(tags), sample


def audit_file(
    path: Path, *, recall_threshold: float
) -> list[Issue]:
    """对单个政策做所有检查,返回 issue 列表。"""
    rel = str(path.relative_to(VAULT))
    issues: list[Issue] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return [Issue(rel, None, None, "suspicious", "io_error",
                      f"读取失败: {e}", "检查文件权限/编码")]

    fm, body = split_frontmatter_body(text)
    pid = (fm or {}).get("id") if isinstance(fm, dict) else None
    title = (fm or {}).get("title") if isinstance(fm, dict) else None

    # 1. PDF binary
    pdf_hit = check_pdf_binary(body)
    if pdf_hit:
        issues.append(Issue(
            rel, pid, title, "suspicious", "pdf_binary",
            f"body 含 PDF 二进制标记: {pdf_hit}",
            "PDF 抓取乱码,走 SKILL.md 重抓重入协议"
            "(_archive 备份 + body_refetched_at audit)"
        ))

    # 2. HTML residue (warn 级:firecrawl 残留 <br> 常见,不影响信息完整性)
    tag_count, sample = check_html_residue(body)
    if sample:
        issues.append(Issue(
            rel, pid, title, "warn", "html_residue",
            f"body 含 {tag_count} 个 HTML tag,样本: {sample}",
            "建议批量 strip <br> 等无信息标签;不阻断派生"
        ))

    # 3. body 过短
    if len(body) < BODY_TOO_SHORT:
        issues.append(Issue(
            rel, pid, title, "warn", "body_too_short",
            f"body 仅 {len(body)} 字符(< {BODY_TOO_SHORT})",
            "可能采集失败,人工核 raw 原文 url 后决定重抓"
        ))

    # 4. body 异常长
    if len(body) > BODY_TOO_LONG:
        issues.append(Issue(
            rel, pid, title, "warn", "body_too_long",
            f"body {len(body)} 字符(> {BODY_TOO_LONG}),可能含 base64 图片",
            "用脚本 strip 图片 base64 / 重抓"
        ))

    # 5. title-body 错配(用 recall 替代 Jaccard,避免大小不平衡假阳性)
    if title and body and len(body) >= 50:
        title_kw = cut_keywords(title, TITLE_TOP_K)
        body_kw = cut_keywords(body[:BODY_PREFIX_FOR_MATCH], BODY_TOP_K)
        recall = title_recall(title_kw, body_kw)
        if recall < recall_threshold and title_kw:
            missing = sorted(title_kw - body_kw)
            issues.append(Issue(
                rel, pid, title, "suspicious", "title_body_mismatch",
                (f"title 关键词 body recall {recall:.2f} < {recall_threshold:.2f}; "
                 f"title kw {sorted(title_kw)} | "
                 f"body 中缺失 {missing}"),
                "人工 audit:title 是否对应 body 内容(P_2024_TJ_01010970 类错配),"
                "如错配走 SKILL.md 重抓协议"
            ))

    return issues


# ─── 扫描入口 ─────────────────────────────────────────────────────────────────


def scan(*, recall_threshold: float) -> Report:
    rep = Report()
    for p in iter_md_files(POLICIES_DIR):
        rep.scanned += 1
        rep.items.extend(audit_file(p, recall_threshold=recall_threshold))
    return rep


# ─── 输出 ────────────────────────────────────────────────────────────────────


def print_text_report(rep: Report, *, quiet: bool) -> None:
    sep = "─" * 72
    print(f"oneshot_l1_body_audit — scanned policies={rep.scanned}")
    print(f"  suspicious={len(rep.suspicious)}  warns={len(rep.warns)}")
    if not HAS_JIEBA:
        print("  WARNING: jieba 未安装,title-body 错配用 fallback 2-gram(精度更低)")
    print(sep)

    items = rep.suspicious if quiet else rep.items
    if not items:
        print("✓ no suspicious raw body detected")
        return

    rank = {"suspicious": 0, "warn": 1}
    items_sorted = sorted(items, key=lambda i: (rank.get(i.level, 9), i.code, i.file))

    cur: tuple[str, str] | None = None
    for it in items_sorted:
        sec = (it.level, it.code)
        if sec != cur:
            print()
            print(f"[{it.level.upper()}] {it.code}")
            cur = sec
        head = f"  {it.file}"
        if it.pid:
            head += f"  (pid={it.pid})"
        print(head)
        print(f"    detail: {it.detail}")
        print(f"    suggest: {it.suggestion}")


def print_json_report(rep: Report) -> None:
    out = {
        "scanned": rep.scanned,
        "summary": {
            "suspicious": len(rep.suspicious),
            "warns": len(rep.warns),
            "has_jieba": HAS_JIEBA,
        },
        "items": [i.to_dict() for i in rep.items],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


# ─── CLI ─────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="L1 raw body 质量全库 audit")
    ap.add_argument("--quiet", action="store_true", help="只打 suspicious")
    ap.add_argument("--json", dest="as_json", action="store_true")
    ap.add_argument(
        "--recall-threshold", type=float, default=DEFAULT_RECALL_THRESHOLD,
        help=f"title 关键词在 body 中 recall 阈值,默认 {DEFAULT_RECALL_THRESHOLD}",
    )
    args = ap.parse_args(argv)

    if not (0.0 <= args.recall_threshold <= 1.0):
        print("ERROR: --recall-threshold 须在 [0,1]", file=sys.stderr)
        return 2

    rep = scan(recall_threshold=args.recall_threshold)

    if args.as_json:
        print_json_report(rep)
    else:
        print_text_report(rep, quiet=args.quiet)

    if rep.suspicious:
        return 2
    if rep.warns:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
