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

  # 场景 D 例:T4 反向 cites_basis 全扫(对 N 个上位政策,扫 vault 内派生引用)
  python3 rebuild_l2.py prepare --trigger reverse_cites --target-pids P_2024_GO_L775,P_2018_NDRC_364
    # → stage _l2_rebuild_state/reverse_cites/{targets.jsonl, vault_index.jsonl, prompt.md}
  # 用户派 1 subagent 跑 prompt(LLM 对每 target 验证候选 from→target 的 cites_basis 边)
  python3 rebuild_l2.py apply --stage rev_cites
    # → 写入 1_extracted/relations/cites_basis.jsonl(防重 by (from,to))

  # 场景 C 例:全量重跑 deterministic 部分(不含 LLM)
  python3 rebuild_l2.py deterministic --scope all
"""
from __future__ import annotations
import argparse
import json
import os
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

def _run_preflight_audit(pids: list[str]) -> None:
    """Step 0 — 入库政策的前置 audit(LLM Wiki §1 raw immutable + 数据合规闸)。

    串跑 3 个 audit 工具 --pid 模式,任一 error/suspicious/violation 即阻断:
      - validate_l1.py   fm 必填 + enum + ISO ts
      - oneshot_l1_body_audit.py   PDF binary / HTML / title-body recall
      - oneshot_l12_residue_audit.py   fm 违规 LLM 派生字段 + body 派生 section

    阻断后用户应改 raw / 重抓 / 净化后重跑 prepare。
    """
    print("\n--- step 0/4: 前置 audit(LLM Wiki §1 / 数据合规闸)---")
    pid_arg = ",".join(pids)

    audits = [
        ("validate_l1",   "validate_l1.py",                ["--pid", pid_arg, "--json"]),
        ("body_audit",    "oneshot_l1_body_audit.py",      ["--pid", pid_arg, "--json"]),
        ("residue_audit", "oneshot_l12_residue_audit.py",  ["--pid", pid_arg, "--json"]),
    ]
    blocking: list[str] = []

    for label, script, extra in audits:
        cmd = ["python3", str(SCRIPTS / script)] + extra
        r = subprocess.run(cmd, cwd=str(VAULT), capture_output=True, text=True)
        if r.returncode == 0:
            print(f"  ✓ {label}: clean")
            continue
        try:
            data = json.loads(r.stdout)
        except json.JSONDecodeError:
            print(f"  [fatal] {label}: 工具崩溃")
            print(f"  stderr: {r.stderr[:500]}")
            sys.exit(1)

        if label == "validate_l1":
            errs = [v for v in data.get("violations", []) if v.get("level") == "error"]
            warns = [v for v in data.get("violations", []) if v.get("level") == "warn"]
            print(f"  {label}: errors={len(errs)} warns={len(warns)}")
            for v in errs[:5]:
                print(f"    [error/{v['code']}] {v['file']}: {v['message']}")
                blocking.append(f"{label}/{v['code']}: {v['file']}")
        elif label == "body_audit":
            susp = [i for i in data.get("items", []) if i.get("level") == "suspicious"]
            warns = [i for i in data.get("items", []) if i.get("level") == "warn"]
            print(f"  {label}: suspicious={len(susp)} warns={len(warns)}")
            for i in susp[:5]:
                print(f"    [suspicious/{i['code']}] {i['file']}: {i['detail'][:120]}")
                blocking.append(f"{label}/{i['code']}: {i['file']}")
        elif label == "residue_audit":
            viol = [i for i in data.get("items", []) if i.get("level") == "violation"]
            print(f"  {label}: violations={len(viol)}")
            for i in viol[:5]:
                print(f"    [violation/{i['code']}] {i['file']}: {i['detail'][:120]}")
                blocking.append(f"{label}/{i['code']}: {i['file']}")

    if blocking:
        print(f"\n[fatal] 前置 audit 阻断 {len(blocking)} 项:")
        for b in blocking[:10]:
            print(f"  - {b}")
        print("\n请按建议修 raw fm / 重抓 body / 净化派生字段后,重跑 prepare。")
        print("如需强制跳过(不推荐),设环境变量 SKIP_PREFLIGHT_AUDIT=1。")
        if os.environ.get("SKIP_PREFLIGHT_AUDIT") != "1":
            sys.exit(2)
        print("[warn] SKIP_PREFLIGHT_AUDIT=1 已强制跳过,后果自负\n")


def prepare_pid_change(pids: list[str]):
    """stage 5C + rel_judge inputs;deterministic 前置(references / entities)"""
    print(f"\n=== prepare pid_change for {len(pids)} pids ===")
    print(f"pids: {pids}\n")

    # 校验 pid 存在
    for pid in pids:
        if find_policy_file_by_pid(pid) is None:
            print(f"[fatal] pid 不在 vault: {pid}")
            sys.exit(1)

    # Step 0:前置 audit(LLM Wiki §1 数据合规闸)
    _run_preflight_audit(pids)

    # 1. deterministic 前置(references regex + entities)
    print("\n--- step 1/4: deterministic 前置 ---")
    run_script("extract_relations_regex.py", ["--references-only"], "references 重抽")
    run_script("extract_entities.py", [], "entities 重抽")

    # 2. stage 5C inputs
    print("\n--- step 2/4: stage 5C LLM inputs ---")
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
    print("\n--- step 3/4: stage rel_judge LLM inputs ---")
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
# Prepare: reverse_cites (T4 反向 cites_basis 全扫上位政策)
# ============================================================

def _extract_official_pattern(official: str) -> str | None:
    """从 official_number 抽出最具识别力的核心 token 用于 regex 匹配。

    例:
      '国务院令第775号'           → '第775号'
      '发改办能源〔2024〕718号'    → '〔2024〕718号'
      '发改综合〔2023〕545号'      → '〔2023〕545号'
      '国办发〔2023〕19号'         → '〔2023〕19号'
    返回 None 表示无可识别核心 token。
    """
    if not official:
        return None
    # 优先 〔YYYY〕XX号
    m = re.search(r"〔\d{4}〕\d+号", official)
    if m:
        return m.group(0)
    # 第 N 号 / 第N号
    m = re.search(r"第\s*\d+\s*号", official)
    if m:
        return m.group(0).replace(" ", "")
    # 数字 + 号
    m = re.search(r"\d{2,4}号", official)
    if m:
        return m.group(0)
    return None


def _title_jieba_top(title: str, top_k: int = 6) -> list[str]:
    """jieba 切 title,取前 top_k 长度 ≥ 2 的非停用词 + 非通用政策高频词 token。

    用更宽 top_k(6)便于上层用 ≥3 词命中策略,且要求至少一个 ≥4 字核心 token。
    """
    try:
        import jieba
        jieba.setLogLevel(40)
    except ImportError:
        return []
    # 跳过停用词 + 通用政策高频词(命中无判别力)
    stop = {
        "关于", "通知", "意见", "办法", "方案", "规定", "细则", "条例", "规则",
        "印发", "发布", "实施", "管理", "工作", "建设", "支持", "促进",
        "中华人民共和国", "国务院", "国务院令", "国务院办公厅",
        "国家发展改革委", "国家能源局", "工业和信息化部",
        "和", "与", "及", "等", "做好", "做好的",
        "加快", "推进", "构建", "提升", "高质量", "深入",
        # 通用业务词(命中无判别力)
        "充电", "乡村", "下乡", "新能源", "汽车", "电力", "能源",
        "服务", "保障", "发展", "市场", "运行", "试点",
    }
    out: list[str] = []
    for w in jieba.cut(title, cut_all=False):
        w = w.strip()
        if not w or w in stop or len(w) < 2:
            continue
        if w in out:
            continue
        out.append(w)
        if len(out) >= top_k:
            break
    return out


def _prefilter_candidates(
    target: dict, all_policies: list[dict], min_candidates: int = 2,
    max_candidates: int = 80,
) -> list[str]:
    """对 target 政策,扫 271 候选 body 找出可能引用 target 的 from pid 集合。

    匹配规则(任一命中即候选):
      hard hit:
        - target.official_number 核心 token(如 〔2024〕718号 / 第775号)精确
          出现在 candidate body
      soft hit(需双重门槛):
        - candidate body 前 3000 字含 ≥ 3 个 target.title jieba 关键词,
          **且**其中至少一个为 ≥ 4 字核心 token(避免"加快/推进"类通用词单独命中)

    若候选 < min_candidates,fallback 全 vault;若 > max_candidates,
    优先保留 hard hit + 按 hit 词数排序截断(LLM cost 控制)。
    """
    self_pid = target["pid"]
    pat = _extract_official_pattern(target.get("official", "") or "")
    title_kw = _title_jieba_top(target.get("title", "") or "")
    long_kw = [w for w in title_kw if len(w) >= 4]

    hard_hits: list[str] = []
    soft_hits: list[tuple[str, int]] = []  # (pid, hit_count)

    for cand in all_policies:
        if cand["pid"] == self_pid:
            continue
        body = cand.get("body", "") or ""
        # hard hit:文号精确
        if pat and pat in body:
            hard_hits.append(cand["pid"])
            continue
        # soft hit:title 关键词 ≥3 词 + 至少 1 个 ≥4 字核心词
        if len(title_kw) >= 3 and long_kw:
            body_head = body[:3000]
            hits = sum(1 for kw in title_kw if kw in body_head)
            has_long = any(kw in body_head for kw in long_kw)
            if hits >= 3 and has_long:
                soft_hits.append((cand["pid"], hits))

    # 合并 hard + soft(按 hit 词数降序)
    soft_sorted = [pid for pid, _ in sorted(soft_hits, key=lambda x: -x[1])]
    candidates = hard_hits + [pid for pid in soft_sorted if pid not in set(hard_hits)]

    if len(candidates) < min_candidates:
        return [c["pid"] for c in all_policies if c["pid"] != self_pid]
    if len(candidates) > max_candidates:
        candidates = candidates[:max_candidates]
    return candidates


def prepare_reverse_cites(target_pids: list[str]):
    """stage T4 反向 cites_basis 全扫 inputs。

    对每个 target(上位政策),预过滤候选 from(扫 vault 271 政策 body 是否
    含 target 文号或 title 关键词),让 LLM 验证候选并产出 cites_basis 边。
    """
    print(f"\n=== prepare reverse_cites for {len(target_pids)} target pids ===")
    print(f"targets: {target_pids}\n")

    # 0. 校验 + 加载 target 元数据
    targets: list[dict] = []
    for pid in target_pids:
        f = find_policy_file_by_pid(pid)
        if f is None:
            print(f"[fatal] target pid 不在 vault: {pid}")
            sys.exit(1)
        fm, body, _ = parse_fm(f)
        targets.append({
            "pid": pid,
            "title": fm.get("title", ""),
            "official": fm.get("official_number", "") or "",
            "issuer": fm.get("issuer", []) or [],
            "date": str(fm.get("date", "") or "")[:10],
            "body_excerpt": body[:1500],
        })

    # 1. 加载全 vault 政策(pid + title + official + body 前 5000 字 — LLM 看的内容)
    print("--- step 1/2: 加载 vault 全 271 政策 body ---")
    all_policies: list[dict] = []
    for p in (VAULT / "0_raw/policies").glob("*.md"):
        # 跳 _archive / _duplicates(glob 不带 rglob,但 glob 可能含子目录,稳妥过滤)
        if any(part.startswith("_") for part in p.relative_to(VAULT).parts[2:]):
            continue
        fm, body, _ = parse_fm(p)
        if not fm or not fm.get("id"):
            continue
        all_policies.append({
            "pid": fm["id"],
            "title": fm.get("title", "") or "",
            "official": fm.get("official_number", "") or "",
            "date": str(fm.get("date", "") or "")[:10],
            "body": body,
        })
    print(f"  loaded {len(all_policies)} policies")

    # 2. 对每 target 预过滤候选,stage
    print("\n--- step 2/2: 预过滤候选 + stage ---")
    state = ensure_state_dir("reverse_cites")

    target_rows = []
    for t in targets:
        cands = _prefilter_candidates(t, all_policies)
        target_rows.append({
            "pid": t["pid"],
            "title": t["title"],
            "official": t["official"],
            "issuer": t["issuer"],
            "date": t["date"],
            "body_excerpt": t["body_excerpt"],
            "candidate_pids": cands,
        })
        print(f"  target {t['pid']}: {len(cands)} candidates")

    (state / "targets.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in target_rows),
        encoding="utf-8",
    )

    # 候选 from 政策的 body excerpt(LLM 用于判断是否引用 target)
    referenced_pids = set()
    for r in target_rows:
        referenced_pids.update(r["candidate_pids"])
    vault_idx_rows = []
    for ap in all_policies:
        if ap["pid"] not in referenced_pids:
            continue
        vault_idx_rows.append({
            "pid": ap["pid"],
            "title": ap["title"],
            "official": ap["official"],
            "date": ap["date"],
            "body_excerpt": ap["body"][:5000],
        })
    (state / "vault_index.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in vault_idx_rows),
        encoding="utf-8",
    )

    (state / "prompt.md").write_text(
        _reverse_cites_prompt_template(state), encoding="utf-8"
    )

    print(f"  ✓ {state}/targets.jsonl ({len(target_rows)} targets)")
    print(f"  ✓ {state}/vault_index.jsonl ({len(vault_idx_rows)} candidate from-policies)")
    print(f"  ✓ {state}/prompt.md")
    print("\n=== prepare reverse_cites 完成 ===")
    print("下一步:派 1 个 opus 4.7 subagent 跑 prompt.md,results 写到")
    print("  _l2_rebuild_state/reverse_cites/results/results.jsonl,")
    print("然后 python3 rebuild_l2.py apply --stage rev_cites")
    print("最后 python3 rebuild_l2.py deterministic --scope post-llm(刷反链)")


# ============================================================
# Apply: 5C / rel / stance / opinions-summary / rev_cites
# ============================================================

def _validate_5c_results(results_path: Path) -> list[str]:
    """检查 5C results.jsonl 每行 schema 完整性。返回阻断错误列表(empty=clean)。

    必填字段:
      - pid (str)
      - summary (str, ≥10 字)
      - scores (6 维 D1-D6,值 0-5)
      - 影响分析 (4 段:加油 / 充电 / 电力_储能_V2G_交易 / 乡村)
    选填(不阻断,只 warn):
      - summary_one_liner / reading_value / national_source / 行动建议 / didi_impact_one_liner
    """
    errors: list[str] = []
    seen_pids: set[str] = set()
    for i, line in enumerate(results_path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"line {i}: JSON decode 失败 ({e})")
            continue
        pid = r.get("pid")
        if not isinstance(pid, str) or not pid.startswith("P_"):
            errors.append(f"line {i}: pid 缺/非法 ({pid!r})")
            continue
        if pid in seen_pids:
            errors.append(f"line {i}: pid 重复 ({pid})")
        seen_pids.add(pid)

        summary = r.get("summary") or ""
        if len(summary) < 10:
            errors.append(f"line {i} ({pid}): summary 缺/过短(<10 字)")

        scores = r.get("scores")
        if not isinstance(scores, dict):
            errors.append(f"line {i} ({pid}): scores 缺/非 dict")
        else:
            for d in ("D1", "D2", "D3", "D4", "D5", "D6"):
                v = scores.get(d)
                if not isinstance(v, (int, float)) or not (0 <= v <= 5):
                    errors.append(f"line {i} ({pid}): scores.{d}={v!r} 缺/越界(0-5)")

        impact = r.get("影响分析")
        if not isinstance(impact, dict):
            errors.append(f"line {i} ({pid}): 影响分析 缺/非 dict")
        else:
            for seg in ("加油", "充电", "电力_储能_V2G_交易", "乡村"):
                if not isinstance(impact.get(seg), str) or not impact.get(seg).strip():
                    errors.append(f"line {i} ({pid}): 影响分析.{seg} 缺")
    return errors


def apply_5c():
    """读 _l2_rebuild_state/5c/results/results.jsonl → schema 强校验 → /tmp + oneshot_apply_5c"""
    state = STATE_ROOT / "5c"
    results = state / "results" / "results.jsonl"
    if not results.exists():
        print(f"[fatal] 缺 {results}")
        sys.exit(1)

    # B.1 schema 强校验:任一 critical 字段缺失即阻断
    errors = _validate_5c_results(results)
    if errors:
        print(f"\n[fatal] 5C results schema 校验失败,{len(errors)} 项阻断:")
        for e in errors[:15]:
            print(f"  - {e}")
        if len(errors) > 15:
            print(f"  ... 其余 {len(errors) - 15} 条略")
        print("\n请改 5C subagent prompt / 让 subagent 重跑生成完整 schema 后,重跑 apply。")
        sys.exit(2)
    print(f"  ✓ 5C results schema 校验:{sum(1 for _ in results.read_text(encoding='utf-8').splitlines() if _.strip())} 行全合规")

    tmp = Path(f"/tmp/5c_results_rebuild_{NOW_TS}.jsonl")
    shutil.copy2(results, tmp)
    run_script("oneshot_apply_5c_subagent_results.py",
               ["--input-glob", str(tmp), "--no-skip-march"], "5C 应用")


def _load_vault_pid_set() -> set[str]:
    """读 0_raw/policies/ 全 fm.id 集合(用于 dangling to/from 检测)。"""
    pids: set[str] = set()
    for p in (VAULT / "0_raw/policies").glob("*.md"):
        if any(part.startswith("_") for part in p.relative_to(VAULT).parts[2:]):
            continue
        fm, _, _ = parse_fm(p)
        if fm and isinstance(fm.get("id"), str):
            pids.add(fm["id"])
    return pids


def apply_rel():
    """读 rel_judge results → dangling 校验 → write to relations/<rel>.jsonl(防重)"""
    state = STATE_ROOT / "rel_judge"
    results = state / "results" / "results.jsonl"
    if not results.exists():
        print(f"[fatal] 缺 {results}")
        sys.exit(1)

    rows = [json.loads(l) for l in results.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"\n应用 {len(rows)} rel 边(校验前)")

    # B.2 dangling from/to 检测:不存在的 pid 一律 skip(LLM 偶发幻觉,容忍但记录)
    vault_pids = _load_vault_pid_set()
    valid_rows = []
    dangling_from = 0
    dangling_to = 0
    bad_self = 0
    for r in rows:
        f, t, rel = r.get("from"), r.get("to"), r.get("rel")
        if not (isinstance(f, str) and isinstance(t, str) and isinstance(rel, str)):
            continue
        if f not in vault_pids:
            dangling_from += 1
            print(f"  [skip dangling-from] {f} -> {t} ({rel})")
            continue
        if t not in vault_pids:
            dangling_to += 1
            print(f"  [skip dangling-to] {f} -> {t} ({rel})")
            continue
        if f == t:
            bad_self += 1
            print(f"  [skip self-loop] {f} -> {t} ({rel})")
            continue
        valid_rows.append(r)
    if dangling_from or dangling_to or bad_self:
        print(f"  ⚠ skipped: dangling_from={dangling_from} dangling_to={dangling_to} self_loop={bad_self}")
    print(f"  ✓ {len(valid_rows)} 边通过 dangling 校验,继续写入")

    by_rel: dict[str, list[dict]] = {}
    for r in valid_rows:
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


def apply_rev_cites():
    """读 reverse_cites/results.jsonl → 写入 cites_basis.jsonl(防重 by (from, to))。

    所有 result 行的 rel 强制为 cites_basis;不在白名单的 result 跳过并打印告警。
    """
    state = STATE_ROOT / "reverse_cites"
    results = state / "results" / "results.jsonl"
    if not results.exists():
        print(f"[fatal] 缺 {results}")
        sys.exit(1)

    rows = [json.loads(l) for l in results.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"\n应用 reverse_cites 候选边 {len(rows)} 行")

    # B.3 dangling from/to 校验(LLM 偶发幻觉,容忍但记录)
    vault_pids = _load_vault_pid_set()

    target = VAULT / "1_extracted/relations/cites_basis.jsonl"
    existing: list[dict] = []
    if target.exists():
        for line in target.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    existing.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    existing_keys = {(r.get("from"), r.get("to")) for r in existing}

    added, skipped_dup, skipped_bad, skipped_dangling = 0, 0, 0, 0
    for nr in rows:
        if nr.get("rel") != "cites_basis":
            print(f"  [skip] rel != cites_basis: {nr.get('from')} -> {nr.get('to')} rel={nr.get('rel')}")
            skipped_bad += 1
            continue
        f, t = nr.get("from"), nr.get("to")
        if not (f and t):
            skipped_bad += 1
            continue
        if f not in vault_pids or t not in vault_pids:
            print(f"  [skip dangling] {f} -> {t}(not in vault pid set)")
            skipped_dangling += 1
            continue
        if f == t:
            skipped_bad += 1
            continue
        if (f, t) in existing_keys:
            skipped_dup += 1
            continue
        existing.append(nr)
        existing_keys.add((f, t))
        added += 1

    target.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in existing) + "\n",
        encoding="utf-8",
    )
    print(f"  cites_basis.jsonl: +{added}(now {len(existing)});"
          f"dup={skipped_dup} bad={skipped_bad} dangling={skipped_dangling}")


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
    "didi_impact_one_liner": "≤30 字滴滴业务核心影响一句话(月报段标题候选,允许提滴滴)",
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


def _reverse_cites_prompt_template(state_dir: Path) -> str:
    return f"""# T4 反向 cites_basis 全扫 subagent prompt(opus 4.7,1 subagent)

input 1: {state_dir}/targets.jsonl
  每行一个上位 target 政策(N 个):
    {{"pid":"P_xxx","title":"...","official":"...","issuer":[...],"date":"YYYY-MM-DD",
      "body_excerpt":"target 政策正文前 1500 字(用于让你理解 target 是什么)",
      "candidate_pids":["P_aaa","P_bbb",...]}}

input 2: {state_dir}/vault_index.jsonl
  候选 from 政策(可能引用 target 的 vault 政策):
    {{"pid":"P_aaa","title":"...","official":"...","date":"YYYY-MM-DD",
      "body_excerpt":"candidate 正文前 5000 字"}}

output: {state_dir}/results/results.jsonl

## 任务

对每个 target,扫其 candidate_pids 中所有 candidate 的 body_excerpt,判断
candidate **是否将 target 引用为制定依据**(cites_basis 语义,见 schema_v3 §6.3)。

cites_basis 严格定义:
  - **位置**:候选政策的开头段(opening,前 800 字符内)或正文显式"依据"段
  - **语义**:candidate 明确把 target 视为制定依据(关键词:根据 / 依据 / 参照 /
    遵循 / 落实 / 对接 / 贯彻 …),而非随便提到一句
  - **形式**:正面引用(可能含 target 文号 / target 标题 /《...》两类)
  - **排除**:
    - candidate 只是 references target(在中段或附则提到一次,无"依据"语义)
    - candidate 引用 target 上位的兄弟政策(如同一年同部门其他文件)
    - candidate 是 target 的 supersedes / iterates / clarifies(那是其他关系)

## 输出 schema(每行一个边,JSON Lines)

```json
{{
  "from": "P_aaa",
  "to":   "P_xxx",
  "rel":  "cites_basis",
  "evidence": "≤200 字原文片段(候选 body 中那段引用 target 的句子)",
  "location": "opening|body",
  "semantic": "basis",
  "confidence": 0.70-1.00,
  "extracted_by": "rebuild_l2_reverse_cites",
  "extracted_at": "{NOW_ISO}",
  "reason": "≤80 字判定依据(为何认为是 basis 而非 reference)"
}}
```

只输出 confidence ≥ 0.70 的边。语义不清晰宁可不输出。

## 关键约束

- **from / to 必须真实存在**:from 必须在该 target 的 candidate_pids 中,
  to 必须等于 target.pid
- **不重复**:同一 (from, to) 只输出一行(取 confidence 最高的 evidence)
- **不修改 vault**:只写 {state_dir}/results/results.jsonl
- **ensure_ascii=False**(中文原样)
- **JSON Lines**:每行一个完整 JSON,不要数组包裹

## 工作建议

按 target 串行处理(每 target 一次性扫完所有 candidate):
1. 读 target 的 title + official + body_excerpt → 知道 target 在讲什么
2. 对每 candidate,grep candidate.body_excerpt 看是否含:
   - target 的 official_number 核心 token(如 〔2024〕718号 / 第775号)
   - target 的 title 标志性短语(如 "新型电力系统行动方案" / "暂行条例")
3. 对命中的 candidate,看那段语境是否符合 cites_basis 严格定义
4. 输出符合的边

预期产出量:per target 5-30 边(取决于 target 在 vault 内的辐射力)。
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
                           choices=["pid_change", "commentary_change", "reverse_cites"])
    p_prepare.add_argument("--pids", help="comma-sep pids for pid_change")
    p_prepare.add_argument("--commentaries", help="comma-sep commentary filenames for commentary_change")
    p_prepare.add_argument("--all-commentaries", action="store_true",
                           help="commentary_change 时表示全 191 linked 重抽")
    p_prepare.add_argument("--target-pids", help="comma-sep upstream pids for reverse_cites")

    p_apply = sub.add_parser("apply", help="apply LLM results from _l2_rebuild_state/")
    p_apply.add_argument("--stage", required=True,
                         choices=["5c", "rel", "stance", "opinions-summary", "rev_cites"])

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
        elif args.trigger == "reverse_cites":
            if not args.target_pids:
                ap.error("--trigger reverse_cites 需 --target-pids")
            prepare_reverse_cites([p.strip() for p in args.target_pids.split(",") if p.strip()])
    elif args.cmd == "apply":
        {"5c": apply_5c, "rel": apply_rel, "stance": apply_stance,
         "opinions-summary": apply_opinions_summary,
         "rev_cites": apply_rev_cites}[args.stage]()
    elif args.cmd == "deterministic":
        run_deterministic(args.scope)


if __name__ == "__main__":
    main()
