#!/usr/bin/env python3
"""
oneshot_b3_review_unlinked_candidates.py — A2 评论复审(subagent 路线,2026-04-29)

A1 跑完后,剩余 ~583 篇评论既未关联政策也未标 not_policy_related。
本脚本配合 Claude Code subagent 把它们三类分流:
  linked → 回填 related_policy(confidence ≥ 0.80)
  not_policy_related → 同 A1 标 true(reason=R5_llm_judge)
  l1_upgrade_candidate → 写 _meta/tmp/l1_upgrade_candidates.jsonl(交下次 L1.3 缺口补采)

工作流:
  1. python3 ... --dump-batches      生成 _meta/tmp/b3_input/batch_NN.md(N 批,自动分)
  2. 主 session 启 N 个 subagent 并行,各看 batch md,输出 JSONL code block
  3. 主 session 合并所有 JSONL → _meta/tmp/b3_unlinked_review.jsonl
  4. python3 ... --apply-from-jsonl  从 jsonl 回写 frontmatter + l1_upgrade.jsonl

用法:
  python3 oneshot_b3_review_unlinked_candidates.py --dry-run        # 预览 + 批次/批数
  python3 oneshot_b3_review_unlinked_candidates.py --dump-batches   # dump batch md 给 subagent
  python3 oneshot_b3_review_unlinked_candidates.py --apply-from-jsonl   # 回写

依赖:stdlib + pyyaml(无 requests / 无 ANTHROPIC_API_KEY)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
COMMENTARIES = VAULT / "0_raw" / "commentaries"
POLICIES = VAULT / "0_raw" / "policies"
TMP_DIR = VAULT / "_meta" / "tmp"
B3_INPUT_DIR = TMP_DIR / "b3_input"
RESULTS_JSONL = TMP_DIR / "b3_unlinked_review.jsonl"
L1_UPGRADE_JSONL = TMP_DIR / "l1_upgrade_candidates.jsonl"

# subagent 一次能 reasonably 处理的批量(单 prompt 内,不耗尽 context):
# ~100 评论 × 600 chars body + 14k catalog ≈ 75k chars ≈ 38k tokens 输入
BATCH_SIZE = 100
BODY_TRUNCATE = 600
CONFIDENCE_THRESHOLD = 0.80
CST = timezone(timedelta(hours=8))

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


SYSTEM_PROMPT = """你是政策评论关联判定器。

输入:一批评论(每条含 slug / title / source_account / body 摘要)+ 一份政策清单(263 篇,L1 raw 政策)。
输出:严格 JSON array,无 markdown 包裹,无任何解释。

对每条评论判定 decision:

1. **linked** — 评论明确解读 / 引用 / 评论了政策清单中的某一篇或多篇政策。
   - related_policy 列出对应政策 pid(P_xxx 格式),允许多个
   - confidence 0-1,反映匹配强度。confidence ≥ 0.80 才会被回填到 vault

2. **not_policy_related** — 评论与政策清单中所有政策都无明确关联。包括:
   - 行业新闻 / 项目动态 / 产品发布 / 公司业绩 / 投资融资
   - 数据分析 / 行情走势 / 市场观察(没有明确政策对标)
   - 法律案例 / 海外政策 / 学术研究 / 个人观点
   - 即使主题相关(储能、电力、新能源等),只要没引用具体政策也算 not_policy_related

3. **l1_upgrade_candidate** — 评论本身是政策原文转载 / 官方答记者问 / 官方解读 / 政策吹风会内容。
   - 这些应该作为 L1 政策入库,不是评论。pid 候选可填(如政策清单已有则相关 pid)
   - 这类需要交给后续 L1.3 缺口补采流程,不直接回填评论

输出 schema(每条评论一个对象):
{{
  "slug": "<input slug>",
  "decision": "linked" | "not_policy_related" | "l1_upgrade_candidate",
  "related_policy": ["P_xxx", ...],
  "confidence": 0.0-1.0,
  "reason": "1 句 < 30 字"
}}

字段规则:
- related_policy: decision=linked 时必填,其他为 []
- confidence: decision=linked 必填,其他可省

只输出 JSON array,不要任何其他内容。

---

# 政策清单(263 篇 L1 raw)

格式:`pid | official_number | title`

{policy_catalog}
"""


def parse_fm(p: Path) -> tuple[dict | None, str | None]:
    """返回 (fm dict, body)。失败返回 (None, None)。"""
    text = p.read_text(encoding="utf-8", errors="ignore")
    m = FM_RE.match(text)
    if not m:
        return None, None
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None, None
    return fm, m.group(2)


def build_policy_catalog() -> tuple[str, dict[str, str]]:
    """读 263 篇政策,生成 catalog 字符串 + pid -> file stem 映射。"""
    lines = []
    pid_to_stem: dict[str, str] = {}
    for p in sorted(POLICIES.glob("*.md")):
        fm, _ = parse_fm(p)
        if not fm:
            continue
        pid = fm.get("id") or p.stem
        title = (fm.get("title") or p.stem).strip()
        official = (fm.get("official_number") or "").strip()
        lines.append(f"{pid} | {official} | {title}")
        pid_to_stem[pid] = p.stem
    catalog = "\n".join(lines)
    return catalog, pid_to_stem


def collect_unlinked_targets() -> list[tuple[Path, dict, str]]:
    """返回未链 + 未标 npr 的评论列表 [(path, fm, body)]。"""
    out = []
    for p in sorted(COMMENTARIES.glob("*.md")):
        fm, body = parse_fm(p)
        if fm is None:
            continue
        if fm.get("related_policy") not in (None, "", [], "~"):
            continue
        if fm.get("not_policy_related") is True:
            continue
        out.append((p, fm, body or ""))
    return out


def render_batch_md(batch_no: int, total_batches: int, batch: list[tuple[Path, dict, str]], catalog_text: str) -> str:
    """生成给 subagent 看的 batch markdown 文件内容。"""
    parts = [
        f"# B3 批次 {batch_no}/{total_batches} — 评论关联判定输入",
        "",
        f"本批 {len(batch)} 条评论。",
        "",
        SYSTEM_PROMPT.replace("{policy_catalog}", catalog_text),
        "",
        "---",
        "",
        f"# 待判定评论({len(batch)} 条)",
        "",
    ]
    for i, (p, fm, body) in enumerate(batch, 1):
        slug = p.stem
        title = (fm.get("title") or slug).strip()
        account = (fm.get("source_account") or "").strip()
        biz = (fm.get("business_tag") or "").strip()
        body_clean = re.sub(r"\s+", " ", body[:BODY_TRUNCATE]).strip()
        parts.append(f"## {i}. slug={slug}")
        parts.append("")
        parts.append(f"- title: {title}")
        parts.append(f"- source_account: {account}")
        parts.append(f"- business_tag: {biz}")
        parts.append(f"- body_excerpt: {body_clean}")
        parts.append("")
    return "\n".join(parts)


def write_back_results(results: list[dict], pid_to_stem: dict[str, str]) -> dict:
    """把 LLM 结果写回评论 frontmatter / l1_upgrade.jsonl。返回统计。"""
    stats = {
        "linked": 0,
        "linked_low_conf": 0,
        "not_policy_related": 0,
        "l1_upgrade_candidate": 0,
        "missing_file": 0,
        "errors": 0,
    }
    today_iso = datetime.now(CST).isoformat(timespec="seconds")

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    l1_upgrades = []

    for res in results:
        slug = res.get("slug", "")
        decision = res.get("decision", "")
        p = COMMENTARIES / f"{slug}.md"
        if not p.exists():
            stats["missing_file"] += 1
            continue

        try:
            fm, body = parse_fm(p)
            if fm is None:
                stats["errors"] += 1
                continue

            if decision == "linked":
                related = res.get("related_policy") or []
                confidence = float(res.get("confidence") or 0)
                # 只接受 catalog 里的 pid
                valid = [pid for pid in related if pid in pid_to_stem]
                if not valid or confidence < CONFIDENCE_THRESHOLD:
                    stats["linked_low_conf"] += 1
                    continue
                fm["related_policy"] = valid
                fm["related_policy_source"] = "B3_llm_unlinked_review"
                fm["related_policy_confidence"] = round(confidence, 2)
                fm["related_policy_matched_at"] = today_iso
                stats["linked"] += 1

            elif decision == "not_policy_related":
                fm["not_policy_related"] = True
                fm["not_policy_related_reason"] = "R5_llm_judge"
                fm["not_policy_related_marked_at"] = datetime.now(CST).strftime("%Y-%m-%d")
                stats["not_policy_related"] += 1

            elif decision == "l1_upgrade_candidate":
                l1_upgrades.append(
                    {
                        "slug": slug,
                        "title": (fm.get("title") or slug),
                        "source_account": fm.get("source_account") or "",
                        "source_url": fm.get("source_url") or "",
                        "candidate_pids": res.get("related_policy") or [],
                        "reason": res.get("reason") or "",
                        "logged_at": today_iso,
                    }
                )
                # 也标 not_policy_related 防止再次进入复审池(reason=R6 区别开)
                fm["not_policy_related"] = True
                fm["not_policy_related_reason"] = "R6_l1_upgrade"
                fm["not_policy_related_marked_at"] = datetime.now(CST).strftime("%Y-%m-%d")
                stats["l1_upgrade_candidate"] += 1
            else:
                stats["errors"] += 1
                continue

            new_fm = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, default_flow_style=False)
            p.write_text(f"---\n{new_fm}---\n{body}", encoding="utf-8")
        except Exception as e:
            stats["errors"] += 1
            print(f"  [error] {slug[:50]}: {e}", file=sys.stderr)

    if l1_upgrades:
        with L1_UPGRADE_JSONL.open("a", encoding="utf-8") as f:
            for r in l1_upgrades:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    return stats


def cmd_dry_run(targets: list, n_batches: int, batch_size: int, catalog_text: str) -> None:
    """仅打印批次概览,不写文件。"""
    print(f"\n=== dry-run ===")
    for i, start in enumerate(range(0, len(targets), batch_size)):
        batch = targets[start : start + batch_size]
        print(f"\n[batch {i+1}/{n_batches}] {len(batch)} 条")
        for p, fm, _ in batch[:3]:
            print(f"  • {p.stem[:70]} | {fm.get('source_account') or ''}")
        if len(batch) > 3:
            print(f"  ... 其余 {len(batch)-3} 条")
        if i >= 1:
            print(f"\n  ... 共 {n_batches} 批,略")
            break

    sys_chars = len(SYSTEM_PROMPT.replace("{policy_catalog}", catalog_text))
    print(f"\nsystem prompt + catalog: {sys_chars} 字符 / 估算 ~{sys_chars // 2} tokens / 批")
    print(f"每批 ~{batch_size} 评论 × 600 chars = ~{batch_size * 600} chars / ~{batch_size * 300} tokens")


def cmd_dump_batches(targets: list, batch_size: int, catalog_text: str) -> None:
    """把 batch md dump 到 _meta/tmp/b3_input/ 给 subagent 用。"""
    B3_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    n_batches = (len(targets) + batch_size - 1) // batch_size
    written = []
    for i, start in enumerate(range(0, len(targets), batch_size), 1):
        batch = targets[start : start + batch_size]
        md = render_batch_md(i, n_batches, batch, catalog_text)
        out = B3_INPUT_DIR / f"batch_{i:02d}.md"
        out.write_text(md, encoding="utf-8")
        written.append((out.relative_to(VAULT), len(batch), len(md)))
    print(f"\n=== dump 完成 ===")
    for path, n, chars in written:
        print(f"  {path} | {n} 条 | {chars} chars")
    print(f"\n下一步:派 {n_batches} 个 subagent 并行,各看一份 batch md,输出 JSONL code block")


def cmd_apply_from_jsonl(jsonl_path: Path, pid_to_stem: dict[str, str]) -> None:
    """从合并好的 jsonl 读 LLM 结果,回写 vault。"""
    if not jsonl_path.exists():
        print(f"[fatal] 找不到 {jsonl_path}", file=sys.stderr)
        sys.exit(1)
    results = []
    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"  [skip] bad jsonl line: {e}")
    print(f"加载 {len(results)} 条 LLM 结果")
    decisions: dict[str, int] = {}
    for r in results:
        d = r.get("decision", "unknown")
        decisions[d] = decisions.get(d, 0) + 1
    print(f"\n  按 decision 分布:")
    for d, n in sorted(decisions.items(), key=lambda x: -x[1]):
        print(f"    {d}: {n}")

    print(f"\n=== 回写 vault ===")
    stats = write_back_results(results, pid_to_stem)
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"\n  L1 upgrade candidates → {L1_UPGRADE_JSONL.relative_to(VAULT)}")


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true", help="预览批次")
    g.add_argument("--dump-batches", action="store_true", help="dump batch md 给 subagent")
    g.add_argument("--apply-from-jsonl", help="从指定 JSONL 文件读结果,回写 vault")
    ap.add_argument("--limit", type=int, default=0, help="只取前 N 篇(0=全部)")
    ap.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    args = ap.parse_args()

    print(f"加载政策 catalog ...")
    catalog_text, pid_to_stem = build_policy_catalog()
    print(f"  263 政策 → catalog {len(catalog_text)} 字符 / {len(pid_to_stem)} pid")

    if args.apply_from_jsonl:
        cmd_apply_from_jsonl(Path(args.apply_from_jsonl), pid_to_stem)
        return

    targets = collect_unlinked_targets()
    if args.limit:
        targets = targets[: args.limit]
    n_batches = (len(targets) + args.batch_size - 1) // args.batch_size
    print(f"待复审评论: {len(targets)} → {n_batches} 批 × {args.batch_size}")

    if args.dry_run:
        cmd_dry_run(targets, n_batches, args.batch_size, catalog_text)
        return

    if args.dump_batches:
        cmd_dump_batches(targets, args.batch_size, catalog_text)
        return


if __name__ == "__main__":
    main()
