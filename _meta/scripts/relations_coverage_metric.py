#!/usr/bin/env python3
"""
relations_coverage_metric.py — L2 关系层覆盖率 metric

scope: 0_raw/policies/ 政策集合 + 1_extracted/relations/*.jsonl 活跃关系
        (跳过 _archive_*.jsonl;跳过 raw 中 _archive/_duplicates)

输出 markdown 报告(默认 stdout),含:
  - 概览:政策数 / 总边数 / conflicts_with=0
  - 每类关系:边数 + inbound/outbound 唯一政策数 + to=null 占比
  - 入度 / 出度分布:min / p50 / p90 / max + isolated 政策数
  - 4 象限分类(schema_v3.md §6.5):双向 / 仅入向 / 仅出向 / 真孤立
  - 上位政策反向边覆盖:T4 候选 10 个的 inbound 边数(诊断反向 cites_basis 缺失)
  - derives_from to=null 详情:占比 + to_title 频次 top 10(诊断 vault 缺上位)
  - isolated 政策清单(默认折叠,--isolated-list 全列)

退出码:始终 0(metric 工具不阻断)

Usage:
  python3 relations_coverage_metric.py
  python3 relations_coverage_metric.py --json           # 结构化输出
  python3 relations_coverage_metric.py --isolated-list  # 列出所有 isolated 政策
  python3 relations_coverage_metric.py --out report.md  # 写文件
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median
from typing import Any, Iterable

import yaml

# ─── 路径 ─────────────────────────────────────────────────────────────────────

VAULT = Path(__file__).resolve().parents[2]
POLICIES_DIR = VAULT / "0_raw" / "policies"
RELATIONS_DIR = VAULT / "1_extracted" / "relations"
SKIP_DIR_NAMES = {"_archive", "_duplicates", ".archive"}

# 9 类关系(schema_v3 §6)— 含 conflicts_with(可能 0 边,占位也要列)
ALL_RELATIONS = (
    "supersedes",
    "iterates",
    "extends",
    "clarifies",
    "references",
    "aligns_with",
    "conflicts_with",
    "cites_basis",
    "derives_from",
)

# T4 反向 cites_basis 候选上位政策(handoff 列出)
UPSTREAM_CANDIDATES = (
    "P_2024_GO_L775",          # 暂行条例 775 令
    "P_2024_NDRC_15",           # 电力市场基本规则 15 号令(已被 20 supersede)
    "P_2024_NDRC_20",           # 电力市场基本规则 20 号令
    "P_2023_GO_19_b",           # 国办发 19 号 充电基础设施
    "P_2023_NDRC_545",          # 充电下乡 545 号
    "P_2020_GO_39_b",           # 新能源汽车产业规划 国办 39 号
    "P_2018_NDRC_364",          # 电力系统调节能力指导意见 364 号
    "P_2024_NDRC_0806117c",     # 新型电力系统行动方案
    "P_2022_NDRC_032146fe",     # 十四五新型储能方案
    "P_2021_SC_23",             # 2030 前碳达峰行动方案
)

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(\n|$)", re.DOTALL)


# ─── 数据结构 ─────────────────────────────────────────────────────────────────


@dataclass
class RelStats:
    rel: str
    edge_count: int = 0
    inbound_pids: set[str] = field(default_factory=set)   # 不含 to=null
    outbound_pids: set[str] = field(default_factory=set)
    to_null_count: int = 0
    to_null_titles: Counter = field(default_factory=Counter)


# ─── 加载 ────────────────────────────────────────────────────────────────────


def iter_policy_files(root: Path) -> Iterable[Path]:
    if not root.is_dir():
        return
    for p in sorted(root.rglob("*.md")):
        if any(part in SKIP_DIR_NAMES for part in p.relative_to(root).parts):
            continue
        if p.is_file():
            yield p


def load_policy_pids() -> set[str]:
    """读 0_raw/policies/ 全部 fm.id 集合。"""
    pids: set[str] = set()
    for p in iter_policy_files(POLICIES_DIR):
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        m = FRONTMATTER_RE.match(text)
        if not m:
            continue
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            continue
        if isinstance(fm, dict) and isinstance(fm.get("id"), str):
            pids.add(fm["id"])
    return pids


def load_relation_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def load_all_relations() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for rel in ALL_RELATIONS:
        out[rel] = load_relation_jsonl(RELATIONS_DIR / f"{rel}.jsonl")
    return out


# ─── metric 计算 ─────────────────────────────────────────────────────────────


def compute_rel_stats(rel: str, rows: list[dict[str, Any]]) -> RelStats:
    s = RelStats(rel=rel)
    s.edge_count = len(rows)
    for r in rows:
        frm = r.get("from")
        to = r.get("to")
        if isinstance(frm, str) and frm:
            s.outbound_pids.add(frm)
        if to is None or to == "":
            s.to_null_count += 1
            t_title = r.get("to_title") or "(无 to_title)"
            s.to_null_titles[t_title] += 1
        elif isinstance(to, str):
            s.inbound_pids.add(to)
    return s


def compute_degree_distribution(
    relations: dict[str, list[dict[str, Any]]],
) -> tuple[Counter, Counter]:
    """返回 (out_degree, in_degree) — 按 pid 累计所有关系类的边数。"""
    out_deg: Counter = Counter()
    in_deg: Counter = Counter()
    for rel, rows in relations.items():
        for r in rows:
            frm = r.get("from")
            to = r.get("to")
            if isinstance(frm, str) and frm:
                out_deg[frm] += 1
            if isinstance(to, str) and to:
                in_deg[to] += 1
    return out_deg, in_deg


def quadrant_classify(
    pids: set[str], out_deg: Counter, in_deg: Counter
) -> dict[str, list[str]]:
    """4 象限(schema_v3.md §6.5):
        ◆ 双向:    out≥1 in≥1
        ←  仅入向:  out=0 in≥1
        →  仅出向:  out≥1 in=0
        ✗  真孤立:  out=0 in=0
    """
    quads: dict[str, list[str]] = {
        "bidirectional": [],
        "inbound_only": [],
        "outbound_only": [],
        "isolated": [],
    }
    for pid in sorted(pids):
        o, i = out_deg.get(pid, 0), in_deg.get(pid, 0)
        if o and i:
            quads["bidirectional"].append(pid)
        elif i:
            quads["inbound_only"].append(pid)
        elif o:
            quads["outbound_only"].append(pid)
        else:
            quads["isolated"].append(pid)
    return quads


def percentile(sorted_vals: list[int], p: float) -> int:
    if not sorted_vals:
        return 0
    idx = min(len(sorted_vals) - 1, int(len(sorted_vals) * p))
    return sorted_vals[idx]


def upstream_inbound(
    upstream: tuple[str, ...], in_deg_per_rel: dict[str, Counter]
) -> list[dict[str, Any]]:
    """每个上位政策候选,列其 inbound 边数 (按关系类型拆分)。"""
    out = []
    for pid in upstream:
        per_rel = {rel: cnt.get(pid, 0) for rel, cnt in in_deg_per_rel.items()}
        out.append({
            "pid": pid,
            "total_inbound": sum(per_rel.values()),
            "per_rel": per_rel,
        })
    return out


def per_rel_in_degree(
    relations: dict[str, list[dict[str, Any]]],
) -> dict[str, Counter]:
    out: dict[str, Counter] = {rel: Counter() for rel in relations}
    for rel, rows in relations.items():
        for r in rows:
            to = r.get("to")
            if isinstance(to, str) and to:
                out[rel][to] += 1
    return out


# ─── 渲染 ────────────────────────────────────────────────────────────────────


def render_markdown(
    pids: set[str],
    relations: dict[str, list[dict[str, Any]]],
    rel_stats: dict[str, RelStats],
    out_deg: Counter,
    in_deg: Counter,
    quads: dict[str, list[str]],
    upstream_data: list[dict[str, Any]],
    *,
    isolated_list: bool,
) -> str:
    lines: list[str] = []
    push = lines.append

    # 概览
    push("# L2 关系层覆盖率 metric\n")
    total_edges = sum(s.edge_count for s in rel_stats.values())
    push(f"- 政策总数(去 `_archive`/`_duplicates`):**{len(pids)}**")
    push(f"- 关系总边数(8 活跃类 + conflicts_with):**{total_edges}**")
    push(f"- 4 象限:双向 **{len(quads['bidirectional'])}** / "
         f"仅入向 **{len(quads['inbound_only'])}** / "
         f"仅出向 **{len(quads['outbound_only'])}** / "
         f"真孤立 **{len(quads['isolated'])}**")
    expected = len(quads['bidirectional']) + len(quads['inbound_only'])
    if expected:
        push(f"- 反链页期望覆盖(双向 + 仅入向):**{expected}**")
    push("")

    # 每类关系
    push("## 每类关系\n")
    push("| 关系 | 边数 | 唯一 from | 唯一 to (非 null) | to=null | to=null 占比 |")
    push("|---|---:|---:|---:|---:|---:|")
    for rel in ALL_RELATIONS:
        s = rel_stats[rel]
        ratio = (s.to_null_count / s.edge_count * 100) if s.edge_count else 0.0
        push(f"| `{rel}` | {s.edge_count} | {len(s.outbound_pids)} | "
             f"{len(s.inbound_pids)} | {s.to_null_count} | {ratio:.1f}% |")
    push("")

    # 入度 / 出度分布
    push("## 入度 / 出度分布\n")
    out_vals = sorted(out_deg.values())
    in_vals = sorted(in_deg.values())
    push("| 度 | 政策数(>0) | min | p50 | p90 | p99 | max |")
    push("|---|---:|---:|---:|---:|---:|---:|")
    if out_vals:
        push(f"| 出度 | {len(out_vals)} | {out_vals[0]} | {int(median(out_vals))} | "
             f"{percentile(out_vals, 0.9)} | {percentile(out_vals, 0.99)} | {out_vals[-1]} |")
    if in_vals:
        push(f"| 入度 | {len(in_vals)} | {in_vals[0]} | {int(median(in_vals))} | "
             f"{percentile(in_vals, 0.9)} | {percentile(in_vals, 0.99)} | {in_vals[-1]} |")
    push("")

    # 上位政策反向边覆盖
    push("## 上位政策反向 inbound 覆盖(T4 候选)\n")
    push("反向 cites_basis 缺口诊断:候选上位政策的 inbound 边应集中在 "
         "`cites_basis` / `clarifies` / `derives_from`。若 inbound 总数低,"
         "意味着 vault 内派生 / 引用它的政策没被 LLM judge 抽到。\n")
    push("| pid | total | cites_basis | clarifies | derives_from | references | other |")
    push("|---|---:|---:|---:|---:|---:|---:|")
    for ud in sorted(upstream_data, key=lambda x: -x["total_inbound"]):
        per = ud["per_rel"]
        other = sum(v for k, v in per.items()
                    if k not in ("cites_basis", "clarifies", "derives_from", "references"))
        push(f"| `{ud['pid']}` | **{ud['total_inbound']}** | "
             f"{per.get('cites_basis', 0)} | "
             f"{per.get('clarifies', 0)} | "
             f"{per.get('derives_from', 0)} | "
             f"{per.get('references', 0)} | "
             f"{other} |")
    push("")

    # derives_from to=null
    df = rel_stats["derives_from"]
    push("## derives_from to=null 详情(T13)\n")
    push(f"- 总边 {df.edge_count} / to=null **{df.to_null_count}** "
         f"({(df.to_null_count / df.edge_count * 100 if df.edge_count else 0):.1f}%)")
    push("")
    if df.to_null_titles:
        push("### to=null 时 to_title 频次(top 15)\n")
        push("| 频次 | to_title 片段(截 80 字) |")
        push("|---:|---|")
        for title, n in df.to_null_titles.most_common(15):
            t = title.replace("|", "/")[:80]
            push(f"| {n} | {t} |")
        push("")

    # 真孤立政策
    iso = quads["isolated"]
    push(f"## 真孤立政策 (out=0, in=0):{len(iso)} 篇\n")
    if isolated_list and iso:
        push("```")
        for pid in iso:
            push(pid)
        push("```")
    elif iso:
        push("(传 `--isolated-list` 列出全部;前 10:)")
        push("```")
        for pid in iso[:10]:
            push(pid)
        push("```")
    push("")

    return "\n".join(lines)


def render_json(
    pids: set[str],
    rel_stats: dict[str, RelStats],
    out_deg: Counter,
    in_deg: Counter,
    quads: dict[str, list[str]],
    upstream_data: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "summary": {
            "policies": len(pids),
            "total_edges": sum(s.edge_count for s in rel_stats.values()),
            "quadrants": {k: len(v) for k, v in quads.items()},
        },
        "per_relation": {
            rel: {
                "edge_count": s.edge_count,
                "outbound_pids": len(s.outbound_pids),
                "inbound_pids_excluding_null": len(s.inbound_pids),
                "to_null_count": s.to_null_count,
                "to_null_top_titles": s.to_null_titles.most_common(15),
            }
            for rel, s in rel_stats.items()
        },
        "degree_distribution": {
            "out": dict(Counter(out_deg).most_common(20)),
            "in": dict(Counter(in_deg).most_common(20)),
        },
        "quadrants": quads,
        "upstream_inbound": upstream_data,
    }


# ─── CLI ─────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="L2 关系层覆盖率 metric (T6 + T13)")
    ap.add_argument("--json", dest="as_json", action="store_true")
    ap.add_argument("--isolated-list", action="store_true",
                    help="markdown 输出含全部 isolated 政策清单")
    ap.add_argument("--out", type=str, default=None, help="写文件而非 stdout")
    ap.add_argument("--reverse-cites-suggest", action="store_true",
                    help="输出 trigger E 候选清单(上位政策 inbound 偏低,适合反向 cites_basis 全扫)")
    ap.add_argument("--trigger-f-candidates", action="store_true",
                    help="输出 trigger F 候选清单(isolated ∪ 2025+ inbound_only build_legacy)")
    args = ap.parse_args(argv)

    pids = load_policy_pids()
    relations = load_all_relations()
    rel_stats = {rel: compute_rel_stats(rel, rows) for rel, rows in relations.items()}
    out_deg, in_deg = compute_degree_distribution(relations)
    quads = quadrant_classify(pids, out_deg, in_deg)
    in_per_rel = per_rel_in_degree(relations)
    upstream_data = upstream_inbound(UPSTREAM_CANDIDATES, in_per_rel)

    # trigger E 候选建议
    if args.reverse_cites_suggest:
        # cites_basis inbound 中,inbound 个数排名后 30% 的上位政策候选
        cb_inbound = in_per_rel.get("cites_basis", {})
        sorted_pids = sorted(UPSTREAM_CANDIDATES, key=lambda p: cb_inbound.get(p, 0))
        suggest = [p for p in sorted_pids if cb_inbound.get(p, 0) <= 3]
        print(",".join(suggest))
        return 0

    # trigger F 候选建议
    if args.trigger_f_candidates:
        # 加载 rel_judge_history(若有)
        from pathlib import Path
        hist = {}
        hpath = VAULT / "_meta" / "audit" / "rel_judge_history.jsonl"
        if hpath.exists():
            for line in hpath.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        r = json.loads(line); hist[r["pid"]] = r
                    except (json.JSONDecodeError, KeyError):
                        pass

        def pid_year(p):
            try:
                return int(p.split("_")[1])
            except (ValueError, IndexError):
                return 0

        # year >= 2017 过滤(P_1900 等占位 pid + 太古老的政策不进)
        isolated_modern = [p for p in quads.get("isolated", []) if pid_year(p) >= 2017]
        inbound_only_unaudited = [
            p for p in quads.get("inbound_only", [])
            if hist.get(p, {}).get("trigger") == "build_phase_legacy"
            and pid_year(p) >= 2025
        ]
        candidates = sorted(set(isolated_modern + inbound_only_unaudited))
        print(",".join(candidates))
        return 0

    if args.as_json:
        out = render_json(pids, rel_stats, out_deg, in_deg, quads, upstream_data)
        text = json.dumps(out, ensure_ascii=False, indent=2)
    else:
        text = render_markdown(
            pids, relations, rel_stats, out_deg, in_deg, quads, upstream_data,
            isolated_list=args.isolated_list,
        )

    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote: {args.out}", file=sys.stderr)
    else:
        print(text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
