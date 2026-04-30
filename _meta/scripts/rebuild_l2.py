#!/usr/bin/env python3
"""
rebuild_l2.py — L1 → L2 全链路 incremental 重建编排器

3 类 L1 触发场景对应 3 套 L2 更新路径,本脚本统一编排:

  A. pid_change(新政策入库 / 现有 raw body 重抓)
     deterministic: extract_relations_regex --references-only + extract_entities
     LLM 任务: 5C 派生 + 关系 LLM judge(cites/iter/ext/clar/align)
     post-LLM deterministic: crystallize 9 主题 + regions + global_index + reverse_links

  B. commentary_change(评论 frontmatter 改 — 如 P4 LLM 重判)
     LLM 任务 1: stance 重抽
     deterministic 1: aggregate_opinions + crystallize 9 主题(刷新 _input.json 含 opinion_pids)
     LLM 任务 2: opinions-summary 9 主题重生成
     post-LLM deterministic: reverse_links

  C. full(全量重建,不区分 trigger)
     全跑 A + B

用法:

  # 场景 A 例:W3 加 3 篇政策
  python3 rebuild_l2.py prepare --trigger pid_change --pids P_2026_xxx,P_2026_yyy,P_2026_zzz
    # → 跑 deterministic 前置(references / entities)
    # → stage _l2_rebuild_state/5c/inputs.jsonl + 打印 subagent prompt
    # → stage _l2_rebuild_state/rel_judge/{inputs.jsonl, vault_index.jsonl} + 打印 prompt

  # 用户派 2 个 subagent 跑 5C 和 rel,results 写到对应 results/

  python3 rebuild_l2.py apply --stage 5c
    # → 应用 5C results → business_view yaml + summaries + derives_from
  python3 rebuild_l2.py apply --stage rel
    # → 应用 rel results → relations/{cites,iter,ext,clar,align}.jsonl
  python3 rebuild_l2.py deterministic --scope post-llm
    # → crystallize_theme --all + regions + global_index + reverse_links

  # 场景 B 例:P4 重判后
  python3 rebuild_l2.py prepare --trigger commentary_change --all-commentaries
    # → stage _l2_rebuild_state/stance/batch_{1..4}.jsonl + prompt

  # 用户派 4 subagent 跑 stance

  python3 rebuild_l2.py apply --stage stance
    # → split + write stance_batches + run aggregate_opinions
    # → run crystallize_theme --all (refresh _input.json with new opinion_pids)
    # → stage _l2_rebuild_state/opinions_summary/spec_{1..3}.json + prompt

  # 用户派 3 subagent 跑 opinions-summary,subagent 直接 Write 到 vault

  python3 rebuild_l2.py apply --stage opinions-summary
    # → 验证 9 个 opinions-summary.md 存在 + run reverse_links

  # 场景 C 例:全量重跑 deterministic 部分(不含 LLM)
  python3 rebuild_l2.py deterministic --scope all
"""
from __future__ import annotations
import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

VAULT = Path(__file__).resolve().parent.parent.parent
SCRIPTS = VAULT / "_meta" / "scripts"
THEMES_REGISTRY = VAULT / "_meta" / "themes_registry.yaml"
STATE_ROOT = Path.cwd() / "_l2_rebuild_state"

NOW_ISO = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
NOW_TS = datetime.now().strftime("%Y%m%d_%H%M%S")
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)

# ============================================================
# 共享 helpers
# ============================================================

def parse_fm(p: Path):
    text = p.read_text(encoding="utf-8", errors="ignore")
    m = FM_RE.match(text)
    if not m:
        return None, "", text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None, "", text
    return fm, m.group(2), text


def find_policy_file_by_pid(pid: str) -> Path | None:
    for p in (VAULT / "0_raw/policies").glob("*.md"):
        fm, _, _ = parse_fm(p)
        if fm and fm.get("id") == pid:
            return p
    return None


def run_script(script_name: str, args: list = None, ok_msg: str = ""):
    """跑 _meta/scripts/<script_name>.py,失败抛错"""
    cmd = ["python3", str(SCRIPTS / script_name)] + (args or [])
    print(f"\n→ {' '.join(cmd[1:])}")
    r = subprocess.run(cmd, cwd=str(VAULT))
    if r.returncode != 0:
        print(f"[fatal] {script_name} 退出码 {r.returncode}")
        sys.exit(r.returncode)
    if ok_msg:
        print(f"  ✓ {ok_msg}")


def ensure_state_dir(name: str) -> Path:
    d = STATE_ROOT / name
    (d / "results").mkdir(parents=True, exist_ok=True)
    return d


def load_themes_registry() -> list:
    return (yaml.safe_load(THEMES_REGISTRY.read_text(encoding="utf-8")) or {}).get("themes", [])


# ============================================================
# Prepare: pid_change (新政策 / body 重抓)
# ============================================================

def prepare_pid_change(pids: list[str]):
    """stage 5C + rel_judge inputs;deterministic 前置(references / entities)"""
    print(f"\n=== prepare pid_change for {len(pids)} pids ===")
    print(f"pids: {pids}\n")

    # 0. 校验 pid 存在
    for pid in pids:
        if find_policy_file_by_pid(pid) is None:
            print(f"[fatal] pid 不在 vault: {pid}")
            sys.exit(1)

    # 1. deterministic 前置(references regex + entities)
    print("--- step 1/3: deterministic 前置 ---")
    run_script("extract_relations_regex.py", ["--references-only"], "references 重抽")
    run_script("extract_entities.py", [], "entities 重抽")

    # 2. stage 5C inputs
    print("\n--- step 2/3: stage 5C LLM inputs ---")
    state_5c = ensure_state_dir("5c")
    rows_5c = []
    for pid in pids:
        f = find_policy_file_by_pid(pid)
        text = f.read_text(encoding="utf-8")
        fm, body, _ = parse_fm(f)
        rows_5c.append({"pid": pid, "title": fm.get("title", ""), "raw_md": text[:14000]})
    (state_5c / "inputs.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows_5c), encoding="utf-8"
    )
    (state_5c / "prompt.md").write_text(_5c_prompt_template(state_5c), encoding="utf-8")
    print(f"  ✓ {state_5c}/inputs.jsonl ({len(rows_5c)} rows)")
    print(f"  ✓ {state_5c}/prompt.md")

    # 3. stage rel_judge inputs
    print("\n--- step 3/3: stage rel_judge LLM inputs ---")
    state_rel = ensure_state_dir("rel_judge")
    vault_idx = []
    for p in (VAULT / "0_raw/policies").glob("*.md"):
        fm, _, _ = parse_fm(p)
        if not fm or not fm.get("id"):
            continue
        vault_idx.append({
            "pid": fm["id"], "title": fm.get("title", ""),
            "official": fm.get("official_number", "") or "",
            "date": str(fm.get("date", "") or "")[:10],
        })
    (state_rel / "vault_index.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in vault_idx), encoding="utf-8"
    )
    (state_rel / "inputs.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows_5c), encoding="utf-8"
    )
    (state_rel / "prompt.md").write_text(_rel_judge_prompt_template(state_rel), encoding="utf-8")
    print(f"  ✓ {state_rel}/inputs.jsonl ({len(rows_5c)} target pids)")
    print(f"  ✓ {state_rel}/vault_index.jsonl ({len(vault_idx)} candidates)")
    print(f"  ✓ {state_rel}/prompt.md")

    print("\n=== prepare pid_change 完成 ===")
    print("下一步:派 2 个 opus 4.7 subagent 跑 5C + rel_judge prompts(见对应 prompt.md),")
    print("results 写到 _l2_rebuild_state/{5c,rel_judge}/results/results.jsonl,")
    print("然后 python3 rebuild_l2.py apply --stage 5c && apply --stage rel")
    print("最后 python3 rebuild_l2.py deterministic --scope post-llm")


# ============================================================
# Prepare: commentary_change (评论 frontmatter 改)
# ============================================================

def prepare_commentary_change(commentary_files: list[str] | None):
    """stage stance inputs(4 batches);commentary_files=None 表示全 191 linked"""
    print(f"\n=== prepare commentary_change ===")

    state = ensure_state_dir("stance")
    # vault policy index for stance context
    pol_idx = {}
    for p in (VAULT / "0_raw/policies").glob("*.md"):
        fm, _, _ = parse_fm(p)
        if fm and fm.get("id"):
            pol_idx[fm["id"]] = {
                "title": fm.get("title", ""),
                "official": fm.get("official_number", "") or "",
                "date": str(fm.get("date", "") or "")[:10],
            }

    # 收集 linked commentaries(过滤 not_policy_related)
    rows = []
    com_dir = VAULT / "0_raw/commentaries"
    targets = set(commentary_files) if commentary_files else None
    for cf in sorted(com_dir.glob("*.md")):
        if targets is not None and cf.name not in targets:
            continue
        fm, body, _ = parse_fm(cf)
        if fm is None or fm.get("not_policy_related"):
            continue
        rp = fm.get("related_policy") or []
        if isinstance(rp, str):
            rp = [rp]
        rp = [x for x in rp if isinstance(x, str) and x in pol_idx]
        if not rp:
            continue
        body_n = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", body)
        body_n = re.sub(r"https?://\S+", "", body_n)
        body_n = re.sub(r"\n{3,}", "\n\n", body_n).strip()[:5000]

        from urllib.parse import urlparse
        domain = urlparse(fm.get("source_url", "") or "").netloc

        rows.append({
            "comment_filename": cf.name,
            "comment_type": fm.get("commentary_type", "unknown") or "unknown",
            "source_account": fm.get("source_account", "") or "",
            "source_domain": domain,
            "date_published": str(fm.get("date_published", "") or "")[:10],
            "related_policy_pids": rp,
            "policies_context": [{"pid": p, **pol_idx[p]} for p in rp],
            "body_excerpt": body_n,
        })

    print(f"linked commentaries to re-stance: {len(rows)}")

    # 切 4 batches
    for i in range(4):
        batch = rows[i::4]
        out = state / f"batch_{i+1}.jsonl"
        out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in batch), encoding="utf-8")
        print(f"  ✓ batch_{i+1}.jsonl: {len(batch)} rows")
    (state / "prompt.md").write_text(_stance_prompt_template(state), encoding="utf-8")
    print(f"  ✓ {state}/prompt.md")

    print("\n=== prepare commentary_change(stance 阶段)完成 ===")
    print("下一步:派 4 个 opus 4.7 subagent 各跑 1 个 batch(见 prompt.md),")
    print("results 写到 _l2_rebuild_state/stance/results/batch_{1..4}.jsonl,")
    print("然后 python3 rebuild_l2.py apply --stage stance")
    print("(stance apply 后会自动 stage opinions-summary 第 2 阶段 inputs)")


# ============================================================
# Apply: 5C / rel / stance / opinions-summary
# ============================================================

def apply_5c():
    """读 _l2_rebuild_state/5c/results/results.jsonl → 复制到 /tmp + 跑 oneshot_apply_5c"""
    state = STATE_ROOT / "5c"
    results = state / "results" / "results.jsonl"
    if not results.exists():
        print(f"[fatal] 缺 {results}")
        sys.exit(1)
    tmp = Path(f"/tmp/5c_results_rebuild_{NOW_TS}.jsonl")
    shutil.copy2(results, tmp)
    run_script("oneshot_apply_5c_subagent_results.py",
               ["--input-glob", str(tmp), "--no-skip-march"], "5C 应用")


def apply_rel():
    """读 rel_judge results → write to relations/<rel>.jsonl(防重)"""
    state = STATE_ROOT / "rel_judge"
    results = state / "results" / "results.jsonl"
    if not results.exists():
        print(f"[fatal] 缺 {results}")
        sys.exit(1)

    rows = [json.loads(l) for l in results.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"\n应用 {len(rows)} rel 边")

    by_rel = {}
    for r in rows:
        by_rel.setdefault(r["rel"], []).append(r)

    REL_DIR = VAULT / "1_extracted/relations"
    for rel, new_rows in by_rel.items():
        target = REL_DIR / f"{rel}.jsonl"
        existing = []
        if target.exists():
            for line in target.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        existing.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        existing_keys = {(r.get("from"), r.get("to")) for r in existing}
        added = 0
        for nr in new_rows:
            if (nr.get("from"), nr.get("to")) not in existing_keys:
                existing.append(nr)
                added += 1
        target.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in existing) + "\n", encoding="utf-8")
        print(f"  {rel}.jsonl: +{added}(now {len(existing)})")


def apply_stance():
    """合 4 batch results → 5 等份切回 stance_batches → aggregate_opinions → crystallize → stage opinions-summary"""
    state = STATE_ROOT / "stance"
    rows = []
    for i in range(1, 5):
        f = state / "results" / f"batch_{i}.jsonl"
        if not f.exists():
            print(f"[fatal] 缺 {f}")
            sys.exit(1)
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    print(f"\n收 stance {len(rows)} rows")

    # 备份 + 写回
    STANCE = VAULT / "_meta/stance_batches"
    backup = STANCE / "_pre_rebuild_l2_backup"
    backup.mkdir(parents=True, exist_ok=True)
    for f in STANCE.glob("agent_*_stances.jsonl"):
        shutil.copy2(f, backup / f"{f.stem}__{NOW_TS}.jsonl")
    for i in range(5):
        batch = rows[i::5]
        out = STANCE / f"agent_{i+1}_stances.jsonl"
        out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in batch) + ("\n" if batch else ""), encoding="utf-8")
        print(f"  agent_{i+1}_stances.jsonl: {len(batch)}")

    # aggregate + crystallize + stage opinions-summary
    run_script("aggregate_opinions.py", [], "opinions 重抽")
    # cleanup stale opinion files
    import time
    opn = VAULT / "1_extracted/opinions"
    cleaned = 0
    for f in opn.glob("P_*.md"):
        if time.time() - f.stat().st_mtime > 60:
            f.unlink()
            cleaned += 1
    print(f"  cleaned {cleaned} stale opinion .md")
    run_script("crystallize_theme.py", ["--all"], "9 主题 _input.json 刷新")

    # stage opinions-summary inputs
    print("\n--- 自动 stage opinions-summary LLM inputs ---")
    _stage_opinions_summary_inputs()


def _stage_opinions_summary_inputs():
    """切 9 主题 spec.json × 3 batches (opinions-summary 第 2 LLM 阶段)"""
    state = ensure_state_dir("opinions_summary")
    THEMES_DIR = VAULT / "2_crystallized/themes"
    OPN = VAULT / "1_extracted/opinions"

    theme_specs = []
    for tdir in sorted(THEMES_DIR.iterdir()):
        if not tdir.is_dir():
            continue
        inp = tdir / "_input.json"
        if not inp.exists():
            continue
        d = json.loads(inp.read_text(encoding="utf-8"))
        opinion_pids = d.get("opinion_policy_ids", [])
        opinions = {pid: (OPN / f"{pid}.md").read_text(encoding="utf-8") for pid in opinion_pids if (OPN / f"{pid}.md").exists()}
        all_pids = [p["id"] for p in d.get("policies", [])]
        uncovered = [p for p in all_pids if p not in set(opinion_pids)]
        theme_specs.append({
            "theme_id": d.get("theme"),
            "theme_dir_name": tdir.name,
            "theme_zh": d.get("theme_zh", ""),
            "aliases": d.get("aliases", []),
            "total_policies": d.get("policies_count", len(d.get("policies", []))),
            "opinion_policy_count": len(opinion_pids),
            "opinion_pids": opinion_pids,
            "opinions_md": opinions,
            "uncovered_pids": uncovered[:20],
            "uncovered_total": len(uncovered),
            "policies_brief": [{"id": p["id"], "title": p["title"][:60]} for p in d.get("policies", [])],
        })

    for i in range(3):
        batch = theme_specs[i::3]
        (state / f"spec_{i+1}.json").write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✓ spec_{i+1}.json: {len(batch)} themes")
    (state / "prompt.md").write_text(_opinions_summary_prompt_template(state), encoding="utf-8")
    print(f"  ✓ {state}/prompt.md")
    print("\n下一步:派 3 个 subagent 各 1 spec(见 prompt.md),subagent 直接 Write 到 vault opinions-summary.md。")
    print("完成后 python3 rebuild_l2.py apply --stage opinions-summary 验证 + 跑 reverse_links")


def apply_opinions_summary():
    """验证 9 个 opinions-summary.md 都已 fresh + 跑 reverse_links"""
    THEMES_DIR = VAULT / "2_crystallized/themes"
    import time
    fresh = 0
    stale = []
    for tdir in THEMES_DIR.iterdir():
        if not tdir.is_dir():
            continue
        f = tdir / "opinions-summary.md"
        if not f.exists():
            stale.append(f"missing: {tdir.name}")
            continue
        age_min = (time.time() - f.stat().st_mtime) / 60
        if age_min > 30:
            stale.append(f"stale ({age_min:.0f}min): {tdir.name}")
        else:
            fresh += 1
    print(f"opinions-summary fresh: {fresh}/{fresh+len(stale)}")
    for s in stale:
        print(f"  ⚠ {s}")
    run_script("build_reverse_links.py", [], "反链同步")


# ============================================================
# Deterministic
# ============================================================

def run_deterministic(scope: str):
    print(f"\n=== deterministic --scope {scope} ===\n")
    if scope in ("references", "all", "pre-llm"):
        run_script("extract_relations_regex.py", ["--references-only"], "references")
    if scope in ("entities", "all", "pre-llm"):
        run_script("extract_entities.py", [], "entities")
    if scope in ("themes", "all", "post-llm"):
        run_script("crystallize_theme.py", ["--all"], "9 主题 crystallize")
    if scope in ("regions", "all", "post-llm"):
        run_script("build_regions.py", [], "regions")
    if scope in ("global", "all", "post-llm"):
        run_script("build_global_index.py", [], "global_index")
    if scope in ("reverse-links", "all", "post-llm"):
        run_script("build_reverse_links.py", [], "reverse_links")


# ============================================================
# Prompt 模板
# ============================================================

def _5c_prompt_template(state_dir: Path) -> str:
    return f"""# 5C 派生 subagent prompt(opus 4.7)

input: {state_dir}/inputs.jsonl
output: {state_dir}/results/results.jsonl

每行 input:
  {{"pid": "P_xxx", "title": "...", "raw_md": "完整 markdown 14K 字内"}}

输出 schema(每行):
  {{
    "pid": "P_xxx",
    "summary": "2-3 句客观摘要,不含品牌名",
    "summary_one_liner": "≤25 字精髓",
    "reading_value": "≤25 字阅读价值",
    "national_source": {{
      "is_national_level_originated": true|false,
      "primary_source": {{"title_or_official": "...", "linkage_type": null|"直接落地"|"借鉴框架"|"主题对应"}},
      "secondary_sources": [],
      "evidence": ""
    }},
    "scores": {{"D1":0-5,"D2":0-5,"D3":0-5,"D4":0-5,"D5":0-5,"D6":0-5}},
    "影响分析": {{"加油":"...","充电":"...","电力_储能_V2G_交易":"...","乡村":"..."}},
    "行动建议": ["A 立即/B 研究/C 关注: ..."]
  }}

服务对象: 滴滴能源(加油/充电/电力/乡村)。详细规则同 derive_business_view.py 的 PROMPT。

CRITICAL: 处理全部行;ensure_ascii=False;不修改 vault;output ONE JSON per line.
"""


def _rel_judge_prompt_template(state_dir: Path) -> str:
    return f"""# 关系层 LLM judge subagent prompt(opus 4.7)

input: {state_dir}/inputs.jsonl(target pids 完整 raw_md)
vault_index: {state_dir}/vault_index.jsonl(候选 pid + title + official + date)
output: {state_dir}/results/results.jsonl

任务:对每个 target pid,扫 raw body 抽 5 类 政策→政策 关系
(cites_basis / iterates / extends / clarifies / aligns_with),
to 必须在 vault_index 中,from = target,confidence>=0.7 才输出。

不抽:references(regex 已抽)/ supersedes(单独判)/ derives_from(5C 派生)。

每行 output:
  {{"from": "P_xxx", "to": "P_yyy", "rel": "cites_basis|iterates|extends|clarifies|aligns_with",
    "evidence": "≤200 字", "confidence": 0.7-1.0,
    "extracted_by": "rebuild_l2_rel_judge", "extracted_at": "{NOW_ISO}",
    "signals": [...], "reason": "..."}}

CRITICAL: from 必须 target;to 必须 vault 内;不重复 (from,to,rel);不修改 vault.
"""


def _stance_prompt_template(state_dir: Path) -> str:
    return f"""# stance 重抽 subagent prompt(opus 4.7,4 batch)

input: {state_dir}/batch_{{1..4}}.jsonl
output: {state_dir}/results/batch_{{1..4}}.jsonl

每行 input:
  {{"comment_filename": "X.md", "comment_type": "...", "source_account": "...",
    "source_domain": "www.example.com", "date_published": "YYYY-MM-DD",
    "related_policy_pids": [...], "policies_context": [...], "body_excerpt": "..." (前 5000 字)}}

任务:对每个 (commentary, target_policy) pair 输出 1 行:
  {{"comment_filename": "X.md", "target_policy_id": "P_xxx",
    "comment_type": "news_report|reposted_original|commentary|unknown",
    "source": "<domain>",
    "stances": [{{"aspect":"...","polarity":"supportive|critical|neutral|mixed",
                  "claim":"≤80字","evidence":"≤120字","confidence":0.0-1.0}}]}}

规则:
- reposted_original 类 stances=[];news_report 0-1 中性;commentary 1-3
- aspect 抽具体议题(商业模式/试点范围/价格机制/...),不空泛
- evidence 必须真实原文片段
- source 取 source_domain;若空写 "?"

CRITICAL: 处理全部行;每 pair 一行(可能 >batch_size 总行);ensure_ascii=False;不修改 vault.
"""


def _opinions_summary_prompt_template(state_dir: Path) -> str:
    return f"""# opinions-summary 重生成 subagent prompt(opus 4.7,3 batch × 3 主题)

input: {state_dir}/spec_{{1..3}}.json (每 file 含 3 主题数组)
output: 直接 Write 到 vault {VAULT}/2_crystallized/themes/<theme_dir_name>/opinions-summary.md

每主题 spec:
  {{"theme_id":"...", "theme_dir_name":"...", "theme_zh":"...",
    "aliases":[...], "total_policies": int, "opinion_policy_count": int,
    "opinion_pids":[...], "opinions_md":{{pid: "<完整.md内容>"}},
    "uncovered_pids":[...], "uncovered_total": int,
    "policies_brief":[{{id, title}}]}}

聚合规则:
- §1 共识: aspect 同向归并,≥3 distinct domain 同 polarity → "🟢/🔴/⚪ **<aspect>** — 涉及 P_xxx 共 N 篇,跨 d1/d2/... 等 M 个独立来源同向 X。"
- §2 分歧: 同 aspect ≥2 不同 polarity 不同 source → 表格
- §3 中性: polarity=neutral 独立条目
- §4 待跟进: claim 含 ?/待/未明 等
- §5 未覆盖: uncovered_pids 列 [[P_xxx]] - title

OUTPUT 模板 frontmatter:
  ---
  title: <theme_zh> 业界观点
  theme_id: <theme_id>
  opinion_coverage: "<X>/<Y> (<Z>%)"
  last_updated: {NOW_ISO}
  ---

CRITICAL: 处理 spec 中所有主题;直接 Write 到 vault 路径(2_crystallized 是 L3 派生层,允许).
"""


# ============================================================
# main
# ============================================================

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_prepare = sub.add_parser("prepare", help="stage L2 rebuild inputs by trigger type")
    p_prepare.add_argument("--trigger", required=True,
                           choices=["pid_change", "commentary_change"])
    p_prepare.add_argument("--pids", help="comma-sep pids for pid_change")
    p_prepare.add_argument("--commentaries", help="comma-sep commentary filenames for commentary_change")
    p_prepare.add_argument("--all-commentaries", action="store_true",
                           help="commentary_change 时表示全 191 linked 重抽")

    p_apply = sub.add_parser("apply", help="apply LLM results from _l2_rebuild_state/")
    p_apply.add_argument("--stage", required=True,
                         choices=["5c", "rel", "stance", "opinions-summary"])

    p_det = sub.add_parser("deterministic", help="run deterministic scripts")
    p_det.add_argument("--scope", required=True,
                       choices=["references", "entities", "themes", "regions", "global", "reverse-links",
                                "pre-llm", "post-llm", "all"])

    args = ap.parse_args()

    if args.cmd == "prepare":
        if args.trigger == "pid_change":
            if not args.pids:
                ap.error("--trigger pid_change 需 --pids")
            prepare_pid_change([p.strip() for p in args.pids.split(",") if p.strip()])
        elif args.trigger == "commentary_change":
            if args.all_commentaries:
                prepare_commentary_change(None)
            elif args.commentaries:
                prepare_commentary_change([c.strip() for c in args.commentaries.split(",") if c.strip()])
            else:
                ap.error("--trigger commentary_change 需 --commentaries 或 --all-commentaries")
    elif args.cmd == "apply":
        {"5c": apply_5c, "rel": apply_rel, "stance": apply_stance,
         "opinions-summary": apply_opinions_summary}[args.stage]()
    elif args.cmd == "deterministic":
        run_deterministic(args.scope)


if __name__ == "__main__":
    main()
