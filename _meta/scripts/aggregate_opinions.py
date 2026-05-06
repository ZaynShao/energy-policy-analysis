#!/usr/bin/env python3
"""
aggregate_opinions.py
Step 8b — 合并 5 个 agent 的 stance jsonl,按 policy_id 聚合 → 政策舆论矩阵 .md

输入:
  - _meta/stance_batches/agent_{1..5}_stances.jsonl

输出:
  - 1_extracted/opinions/_op_<policy_id>.md  (每政策一个舆论矩阵,_op_ 前缀避免与 raw 政策 alias 冲突)
  - 1_extracted/opinions/_summary.md     (整体统计)

聚合规则(schema_v3.md 第 8.3 节):
  - 共识:≥3 独立 source 持相同 polarity 且 aspect 接近(jaccard ≥0.4)→ 共识列
  - 分歧:同 aspect 出现 ≥2 不同 polarity → 分歧表
  - 中性观察:polarity = neutral 的独立条目
  - 待跟进:claim 含"?"/"待"/"未明"等开放问题(LLM 已标)
"""

import json
import re
from pathlib import Path
from collections import defaultdict, Counter

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
BATCHES = VAULT / "_meta" / "stance_batches"
OPINIONS = VAULT / "1_extracted" / "opinions"
OPINIONS.mkdir(parents=True, exist_ok=True)


def try_fix_inner_quotes(line):
    """LLM 偶尔在中文 string 里用 ASCII 双引号破坏 JSON,尝试用中文双引号替换"""
    # 简单规则:把 string value 内部的孤立 " 替换成 \\u201C/\\u201D
    # 用一个 stateful 解析:奇数次 " 是 string 边界,中间被 ASCII " 截断的视为内嵌
    # 简化:直接替换"汉字"" 这种相邻汉字的 ASCII 引号
    fixed = re.sub(r'(?<=[一-鿿])"(?=[一-鿿])', '”', line)
    fixed = re.sub(r'(?<=[一-鿿、])"(?=[一-鿿])', '“', fixed)
    return fixed


def load_all_stances():
    """合并 5 个 agent jsonl,容错解析"""
    by_policy = defaultdict(list)
    type_dist = Counter()
    polarity_dist = Counter()
    total_comments = 0
    total_stances = 0
    parse_errs = 0

    for i in range(1, 6):
        p = BATCHES / f"agent_{i}_stances.jsonl"
        if not p.exists():
            print(f"  ⚠️  {p.name} 缺失")
            continue
        with open(p, encoding="utf-8") as f:
            for ln, line in enumerate(f, 1):
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    # 尝试修复内嵌 ASCII 引号
                    try:
                        d = json.loads(try_fix_inner_quotes(line))
                    except json.JSONDecodeError as e:
                        parse_errs += 1
                        print(f"  ⚠️  agent_{i} L{ln} 解析失败,跳过: {str(e)[:60]}")
                        continue
                total_comments += 1
                pid = d.get("target_policy_id")
                ctype = d.get("comment_type", "unknown")
                type_dist[ctype] += 1
                if not pid:
                    continue
                source = d.get("source", "")
                fname = d.get("comment_filename", "")
                for s in d.get("stances", []) or []:
                    polarity_dist[s.get("polarity", "?")] += 1
                    by_policy[pid].append({
                        "comment": fname,
                        "source": source,
                        "comment_type": ctype,
                        **s,
                    })
                    total_stances += 1
    if parse_errs:
        print(f"  total parse errors: {parse_errs}")
    return by_policy, type_dist, polarity_dist, total_comments, total_stances


def aspect_similarity(a, b):
    """两 aspect 短语的 jaccard 相似度(字符 bigram)"""
    def bigrams(s):
        return set(s[i:i + 2] for i in range(len(s) - 1)) if len(s) >= 2 else {s}
    A, B = bigrams(a), bigrams(b)
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


def cluster_by_aspect(stances, sim_threshold=0.4):
    """把 stance 按 aspect 相似度聚类"""
    clusters = []
    for s in stances:
        aspect = s.get("aspect", "")
        placed = False
        for c in clusters:
            if any(aspect_similarity(aspect, x.get("aspect", "")) >= sim_threshold for x in c):
                c.append(s)
                placed = True
                break
        if not placed:
            clusters.append([s])
    return clusters


def render_opinion_page(policy_id, stances, raw_policy_filename=None):
    """生成单个政策的舆论矩阵 .md

    raw_policy_filename: raw 政策的真实文件名(stem,不含 .md)。提供时在 body
    顶部加显式 [[]] link 到 raw 政策,确保 Obsidian Graph view 显示
    raw 政策不孤立(alias resolution 在 graph view 不一定可靠,真实文件名
    [[]] 是 100% 可靠的边来源)。
    """
    # 按 aspect 聚类
    clusters = cluster_by_aspect(stances)

    consensus = []  # ≥3 同 polarity
    conflicts = []  # 同 aspect 多 polarity
    neutral_obs = []
    open_questions = []

    for c in clusters:
        # 同 aspect cluster
        polarity_counts = Counter(s.get("polarity") for s in c)
        sources_by_polarity = defaultdict(set)
        for s in c:
            sources_by_polarity[s.get("polarity")].add(s.get("source", "?"))

        # consensus
        for pol, n in polarity_counts.items():
            if pol in ("supportive", "critical") and len(sources_by_polarity[pol]) >= 3:
                main_aspect = c[0].get("aspect", "?")
                consensus.append({
                    "polarity": pol,
                    "aspect": main_aspect,
                    "sources": sorted(sources_by_polarity[pol]),
                    "claims": [s["claim"] for s in c if s.get("polarity") == pol][:3],
                })

        # conflicts
        polarities_present = [p for p in ("supportive", "critical") if polarity_counts.get(p, 0) >= 1]
        if len(polarities_present) >= 2:
            conflicts.append({
                "aspect": c[0].get("aspect", "?"),
                "supportive": [s for s in c if s.get("polarity") == "supportive"][:2],
                "critical": [s for s in c if s.get("polarity") == "critical"][:2],
            })

        # neutral
        for s in c:
            if s.get("polarity") == "neutral":
                neutral_obs.append(s)

    # open questions:简化版,看 claim 含"?"
    for s in stances:
        claim = s.get("claim", "")
        if "?" in claim or "?" in claim:
            open_questions.append(s)

    lines = []
    lines.append("---")
    lines.append(f"policy_id: {policy_id}")
    lines.append(f"stance_total: {len(stances)}")
    lines.append(f"consensus_total: {len(consensus)}")
    lines.append(f"conflicts_total: {len(conflicts)}")
    lines.append(f"neutral_total: {len(neutral_obs)}")
    lines.append("schema_version: 3.0")
    lines.append("---")
    lines.append("")
    # 顶部显式 [[]] 链接到 raw 政策(用真实文件名 stem,graph view 100% 可靠)
    if raw_policy_filename:
        lines.append(f"> 政策原文:[[{raw_policy_filename}|{policy_id}]]")
        lines.append("")
    lines.append(f"# {policy_id} 舆论矩阵")
    lines.append("")
    lines.append(f"**stance 数:** {len(stances)}  ·  **来源数:** {len(set(s.get('source') for s in stances))}")
    lines.append("")

    if consensus:
        lines.append(f"## 🟢 共识(≥3 独立来源同向)")
        lines.append("")
        for c in consensus:
            icon = "🟢" if c["polarity"] == "supportive" else "🔴"
            lines.append(f"- {icon} **{c['aspect']}**({c['polarity']}, {len(c['sources'])} 源)")
            for src in c["sources"][:5]:
                lines.append(f"  - {src}")
            for cl in c["claims"][:2]:
                lines.append(f"  - 观点:{cl}")
        lines.append("")

    if conflicts:
        lines.append("## 分歧")
        lines.append("")
        lines.append("| 议题 | 支持方 | 反对方 |")
        lines.append("|------|-------|-------|")
        for cf in conflicts:
            sup_short = " / ".join(s.get("claim", "")[:30] + " (" + s.get("source", "")[:12] + ")"
                                    for s in cf["supportive"][:2])
            cri_short = " / ".join(s.get("claim", "")[:30] + " (" + s.get("source", "")[:12] + ")"
                                    for s in cf["critical"][:2])
            lines.append(f"| {cf['aspect']} | {sup_short} | {cri_short} |")
        lines.append("")

    if neutral_obs:
        lines.append("## 中性观察")
        lines.append("")
        for n in neutral_obs[:10]:
            lines.append(f"- ⚪ **{n.get('aspect')}**:{n.get('claim')}({n.get('source', '?')[:20]})")
        lines.append("")

    if open_questions:
        lines.append("## 待跟进")
        lines.append("")
        for q in open_questions[:5]:
            lines.append(f"- ❓ {q.get('claim')}({q.get('source', '?')[:20]})")
        lines.append("")

    # 全量 stance 表(末尾,完整可查)
    lines.append("---")
    lines.append("")
    lines.append(f"## 全量 stance({len(stances)})")
    lines.append("")
    lines.append("| polarity | aspect | claim | source | conf |")
    lines.append("|----------|--------|-------|--------|:----:|")
    for s in stances:
        cl = (s.get("claim") or "")[:50].replace("|", "\\|")
        src = (s.get("source") or "?")[:25].replace("|", "\\|")
        lines.append(f"| {s.get('polarity', '?')} | {s.get('aspect', '?')} | {cl} | {src} | {s.get('confidence', '?')} |")
    lines.append("")

    return "\n".join(lines)


def main():
    print("Loading 5 agent jsonl batches...")
    by_policy, type_dist, polarity_dist, total_comments, total_stances = load_all_stances()
    print(f"  {total_comments} comments processed across batches")
    print(f"  {total_stances} stances aggregated")
    print(f"  {len(by_policy)} unique policies got opinions")
    print(f"  comment type dist: {dict(type_dist)}")
    print(f"  polarity dist: {dict(polarity_dist)}")

    print("\nWriting per-policy opinion pages...")
    # cleanup 旧的 P_xxx.md(2026-05-06 改名前的同名命名,会与 raw 政策 alias 冲突)
    import re as _re
    # 严格 alias 模式:P_YYYY_xxx_yyy_zzz...(段间单下划线,无连续 __)
    # 匹配 P_2020_GO_39_b / P_2024_OTHER1B33_33 等真实 vault alias
    # 排除 P_xxx__from__P_yyy(diff 文件名,含 __)
    _alias_pat = _re.compile(r'^P_\d{4}_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*$')
    for old in OPINIONS.glob('P_*.md'):
        if _alias_pat.match(old.stem):
            old.unlink()
    # 加载 raw 政策 pid → 文件名 stem(给 render 加显式 [[]] link)
    import yaml as _yaml
    pid_to_stem = {}
    for p in (VAULT / "0_raw" / "policies").glob("*.md"):
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if not txt.startswith("---"):
            continue
        end = txt.find("---", 3)
        try:
            fm = _yaml.safe_load(txt[3:end]) or {}
        except _yaml.YAMLError:
            continue
        if fm.get("id"):
            pid_to_stem[fm["id"]] = p.stem
    written = 0
    for pid, stances in by_policy.items():
        page = render_opinion_page(pid, stances, raw_policy_filename=pid_to_stem.get(pid))
        # 文件名加 _op_ 前缀避免与 raw 政策 alias `P_xxx` 命名冲突。
        # 同 build_reverse_links.py 的 _rev_ 前缀处理。
        out = OPINIONS / f"_op_{pid}.md"
        out.write_text(page, encoding="utf-8")
        written += 1
    print(f"  {written} opinion pages → {OPINIONS}")

    # 整体统计
    summary = []
    summary.append("---")
    summary.append("title: Step 8 评论 stance 抽取汇总")
    summary.append("date: 2026-04-26")
    summary.append("---")
    summary.append("")
    summary.append("# Step 8 · 评论 stance 抽取汇总")
    summary.append("")
    summary.append(f"- 处理评论: **{total_comments}**")
    summary.append(f"- 抽出 stance: **{total_stances}**")
    summary.append(f"- 政策有 ≥1 stance: **{len(by_policy)}**")
    summary.append("")
    summary.append("## 评论类型分布")
    for k, v in type_dist.most_common():
        summary.append(f"- {k}: {v} ({v/max(1,total_comments)*100:.0f}%)")
    summary.append("")
    summary.append("## polarity 分布")
    for k, v in polarity_dist.most_common():
        summary.append(f"- {k}: {v}")
    summary.append("")
    summary.append("## 关键发现")
    rep_pct = type_dist.get("reposted_original", 0) / max(1, total_comments) * 100
    if rep_pct >= 40:
        summary.append(f"- ⚠️ **{rep_pct:.0f}% 评论是政策原文转载**(L1 step6_comments.py 召回质量需提升,真观点占比低)")
    sup_pct = polarity_dist.get("supportive", 0) / max(1, total_stances) * 100
    if sup_pct >= 70:
        summary.append(f"- ⚠️ supportive 占 {sup_pct:.0f}%,critical 仅 {polarity_dist.get('critical',0)/max(1,total_stances)*100:.0f}% — 评论选择偏官方/支持向(媒体覆盖偏差)")
    summary.append("")
    summary.append("## Top 政策(stance 最多)")
    summary.append("")
    top_pid = sorted(by_policy.items(), key=lambda kv: -len(kv[1]))[:10]
    for pid, ss in top_pid:
        polarities = Counter(s.get("polarity") for s in ss)
        summary.append(f"- `{pid}`:{len(ss)} stance,{dict(polarities)}")

    (OPINIONS / "_summary.md").write_text("\n".join(summary), encoding="utf-8")
    print(f"  summary → {OPINIONS / '_summary.md'}")
    print("\n=== Done ===")


if __name__ == "__main__":
    main()
