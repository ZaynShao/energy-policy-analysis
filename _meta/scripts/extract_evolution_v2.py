#!/usr/bin/env python3
"""
extract_evolution_v2.py
P0-2: supersedes / iterates 用 cites_basis + references + 同 issuer 多源反推 + LLM

输入:
  - 0_raw/policies/*.md                              (P_id → meta)
  - 1_extracted/relations/references.jsonl           (135 条文号引用边)
  - 1_extracted/relations/cites_basis.jsonl          (10 条依据引用边)

输出:
  - 1_extracted/relations/supersedes_v2.jsonl
  - 1_extracted/relations/iterates_v2.jsonl
  (人工抽查后 mv 成正式 supersedes.jsonl / iterates.jsonl)

3 阶段:
  Stage 1 候选生成(3 源融合):
    - cites_basis 边
    - references 边
    - 同 issuer 政策对 + 时间窗 ≤3y + 标题主干 jaccard ≥0.5(剔除年份)
    A.date > B.date 才入候选(演进方向)
  Stage 2 LLM 判定 rel ∈ {iterates, supersedes, neither}
  Stage 3 confidence ≥0.7 的写 v2 文件

环境变量:
  MINIMAX_API_KEY    必填(--dry-run 时可省)
  MINIMAX_BASE_URL   默认 https://api.minimax.chat/v1
  MINIMAX_MODEL      默认 MiniMax-M2

用法:
  export MINIMAX_API_KEY=...
  python3 extract_evolution_v2.py --dry-run    # 不耗 token,看候选量
  python3 extract_evolution_v2.py              # 正式跑
"""

import os
import re
import sys
import json
import yaml
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from openai import OpenAI, OpenAIError

# 配置
VAULT_ROOT = Path.home() / "Documents/Zayn Main/政策分析"
POLICIES_DIR = VAULT_ROOT / "0_raw/policies"
RELATIONS_DIR = VAULT_ROOT / "1_extracted/relations"
REFERENCES_JSONL = RELATIONS_DIR / "references.jsonl"
CITES_BASIS_JSONL = RELATIONS_DIR / "cites_basis.jsonl"
OUT_SUPERSEDES = RELATIONS_DIR / "supersedes_v2.jsonl"
OUT_ITERATES = RELATIONS_DIR / "iterates_v2.jsonl"

ITERATES_TIME_WINDOW_YEARS = 3
TITLE_JACCARD_MIN = 0.5
KEEP_CONFIDENCE_MIN = 0.7

LLM_TEMPERATURE = 0.0
LLM_MAX_TOKENS = 600
DEFAULT_BASE_URL = "https://api.minimax.chat/v1"
DEFAULT_MODEL = "MiniMax-M2"

CST = timezone(timedelta(hours=8))

PUNCT = "（）()、，。：；【】《》〔〕\"'""•—－-—_/\\|"


def cn_now_iso():
    return datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def parse_frontmatter(md_path: Path):
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, parts[2]


def parse_date(s):
    if not s:
        return None
    s = str(s)[:10]
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def title_jaccard(t1, t2):
    """剔除数字、空白、标点后字符 jaccard"""
    def norm(t):
        return set(c for c in (t or "") if not c.isdigit() and not c.isspace() and c not in PUNCT)
    s1, s2 = norm(t1), norm(t2)
    if not s1 or not s2:
        return 0.0
    return len(s1 & s2) / len(s1 | s2)


def years_between(d1, d2):
    if not (d1 and d2):
        return None
    return abs((d1 - d2).days) / 365.25


def build_id_to_meta():
    id_to_meta = {}
    for md in POLICIES_DIR.glob("*.md"):
        fm, _ = parse_frontmatter(md)
        pid = fm.get("id")
        if not pid:
            continue
        date_obj = parse_date(fm.get("date"))
        issuers = fm.get("issuer") or []
        if isinstance(issuers, str):
            issuers = [issuers]
        id_to_meta[pid] = {
            "title": (fm.get("title") or "").strip(),
            "date_obj": date_obj,
            "date_str": str(fm.get("date") or "")[:10],
            "issuers": frozenset(issuers),
        }
    return id_to_meta


# ---------- Stage 1: 候选生成 ----------

def stage_1_candidates(id_to_meta):
    """生成候选 (A_id, B_id) → {evidence, signals}, 满足 A.date > B.date"""
    candidates = {}

    def add(a, b, ev, sig):
        if a == b:
            return
        ma, mb = id_to_meta.get(a), id_to_meta.get(b)
        if not (ma and mb and ma["date_obj"] and mb["date_obj"]):
            return
        if not (ma["date_obj"] > mb["date_obj"]):
            return
        key = (a, b)
        if key not in candidates:
            candidates[key] = {"evidence": "", "signals": set()}
        candidates[key]["signals"].add(sig)
        if ev and not candidates[key]["evidence"]:
            candidates[key]["evidence"] = ev

    # Source 1: cites_basis
    if CITES_BASIS_JSONL.exists():
        with CITES_BASIS_JSONL.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                e = json.loads(line)
                add(e["from"], e["to"], e.get("evidence", ""), "basis")

    # Source 2: references
    if REFERENCES_JSONL.exists():
        with REFERENCES_JSONL.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                e = json.loads(line)
                add(e["from"], e["to"], e.get("evidence", ""), "ref")

    # Source 3: 同 issuer 政策对(时间窗 + 标题 jaccard)
    issuer_to_pids = defaultdict(list)
    for pid, meta in id_to_meta.items():
        if not (meta["date_obj"] and meta["issuers"]):
            continue
        for iss in meta["issuers"]:
            issuer_to_pids[iss].append(pid)

    for iss, pids in issuer_to_pids.items():
        for a in pids:
            for b in pids:
                if a == b:
                    continue
                ma, mb = id_to_meta[a], id_to_meta[b]
                if not (ma["date_obj"] > mb["date_obj"]):
                    continue
                yrs = years_between(ma["date_obj"], mb["date_obj"])
                if yrs is None or yrs > ITERATES_TIME_WINDOW_YEARS:
                    continue
                if title_jaccard(ma["title"], mb["title"]) < TITLE_JACCARD_MIN:
                    continue
                add(a, b, "", "same_issuer")

    return candidates


# ---------- Stage 2: LLM 判定 ----------

JUDGE_PROMPT = """你是政策演进关系判定专家。给定两份政策 A 和 B (A.date > B.date,A 在 B 之后发布),判定 A 对 B 的关系。

类别 (三选一):
- iterates: A 是 B 的迭代/升级版。常见标志:标题主干一致仅年份/版本不同;A 在引文段写"在 B 基础上修订";同主题年度更新;同 issuer 续作。
- supersedes: A 显式废止 B (含明确"废止 B"/"B 同时废止"等语句),或 A 完全替代 B 的功能。
- neither: 仅引用、同主题对齐、不同维度、或无明确演进关系。

输入 JSON 含: A.title/date, B.title/date, evidence_hint (A 引用 B 的句子,可能为空), signals (引用证据来源,如 ref/basis/same_issuer)。

只输出 JSON 一对象,不带 markdown 包裹:
{"rel": "iterates"|"supersedes"|"neither", "confidence": 0.0-1.0, "reason": "≤30 字"}"""


THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
JSON_OBJ_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)


def parse_llm_json(raw):
    raw = THINK_BLOCK_RE.sub("", raw or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = JSON_OBJ_RE.search(raw)
        if m:
            return json.loads(m.group(0))
        raise


def stage_2_judge(candidates, id_to_meta, client, model):
    iterates_out, supersedes_out = [], []
    skipped, failed = 0, 0
    n = len(candidates)
    items = list(candidates.items())

    for i, ((a, b), info) in enumerate(items, 1):
        ma, mb = id_to_meta[a], id_to_meta[b]
        payload = json.dumps({
            "A": {"id": a, "title": ma["title"], "date": ma["date_str"]},
            "B": {"id": b, "title": mb["title"], "date": mb["date_str"]},
            "evidence_hint": info["evidence"][:300],
            "signals": sorted(info["signals"]),
        }, ensure_ascii=False)

        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": JUDGE_PROMPT},
                    {"role": "user", "content": payload},
                ],
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
            )
            raw = resp.choices[0].message.content or ""
            judgment = parse_llm_json(raw)
        except (OpenAIError, json.JSONDecodeError, ValueError, AttributeError) as e:
            print(f"[2 fail {i}/{n}] {a} → {b}: {type(e).__name__}: {str(e)[:80]}", file=sys.stderr)
            failed += 1
            continue
        except Exception as e:
            print(f"[2 fail {i}/{n}] {a} → {b}: {type(e).__name__}: {str(e)[:80]}", file=sys.stderr)
            failed += 1
            continue

        rel = judgment.get("rel", "neither")
        conf = float(judgment.get("confidence", 0.0))
        reason = (judgment.get("reason", "") or "")[:50]

        if rel == "neither" or conf < KEEP_CONFIDENCE_MIN:
            skipped += 1
            if i % 10 == 0 or rel != "neither":
                print(f"[2 skip {i}/{n}] {a} → {b}  ({rel}, {conf:.2f}) {reason}")
            continue

        record = {
            "from": a,
            "to": b,
            "rel": rel,
            "evidence": info["evidence"][:300],
            "confidence": conf,
            "extracted_by": "llm_judge_v2",
            "extracted_at": cn_now_iso(),
            "signals": sorted(info["signals"]),
            "reason": reason,
        }
        if rel == "iterates":
            iterates_out.append(record)
            print(f"[2 ITER {i}/{n}] {a} → {b}  conf={conf:.2f}  {reason}")
        elif rel == "supersedes":
            supersedes_out.append(record)
            print(f"[2 SUPS {i}/{n}] {a} → {b}  conf={conf:.2f}  {reason}")

    return iterates_out, supersedes_out, {"skipped": skipped, "failed": failed}


# ---------- ping ----------

def ping_llm(client, model):
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Reply 'pong' only."},
                {"role": "user", "content": "ping"},
            ],
            temperature=0.0,
            max_tokens=20,
        )
        body = (resp.choices[0].message.content or "").strip()
        print(f"[ping] {model} responded: {body[:30]!r}")
        return True
    except Exception as e:
        print(f"[ping FAIL] {type(e).__name__}: {e}", file=sys.stderr)
        return False


# ---------- main ----------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="跳过 LLM 调用,只看候选量 + 信号分布")
    parser.add_argument("--dump-candidates", metavar="PATH",
                        help="把候选清单 dump 成 JSON 后退出(供 subagent 判定)")
    parser.add_argument("--load-judgments", metavar="PATH",
                        help="读 subagent 判定结果 JSON,按 KEEP_CONFIDENCE_MIN 过滤后写 v2 文件")
    args = parser.parse_args()

    base_url = os.environ.get("MINIMAX_BASE_URL", DEFAULT_BASE_URL)
    model = os.environ.get("MINIMAX_MODEL", DEFAULT_MODEL)
    api_key = os.environ.get("MINIMAX_API_KEY")

    need_llm = not (args.dry_run or args.dump_candidates or args.load_judgments)

    if need_llm and not api_key:
        print("[fatal] MINIMAX_API_KEY 未设", file=sys.stderr)
        sys.exit(2)

    client = None
    if need_llm:
        client = OpenAI(api_key=api_key, base_url=base_url)
        print(f"[init] base_url: {base_url}")
        print(f"[init] model:    {model}")
        if not ping_llm(client, model):
            sys.exit(3)

    print(f"[init] vault: {VAULT_ROOT}")
    print(f"[init] dry_run: {args.dry_run}")

    id_to_meta = build_id_to_meta()
    print(f"[init] policies indexed: {len(id_to_meta)}")

    print("\n=== Stage 1: 候选生成 ===")
    candidates = stage_1_candidates(id_to_meta)
    print(f"[1] total candidates: {len(candidates)}")

    sig_dist = defaultdict(int)
    for info in candidates.values():
        sig_key = ",".join(sorted(info["signals"]))
        sig_dist[sig_key] += 1
    print("[1] signal distribution:")
    for sig, n in sorted(sig_dist.items(), key=lambda x: -x[1]):
        print(f"     {sig}: {n}")

    if args.dry_run:
        print("\n[dry-run] 跳过 stage 2/3,前 10 候选样例:")
        for i, ((a, b), info) in enumerate(list(candidates.items())[:10]):
            ma, mb = id_to_meta[a], id_to_meta[b]
            print(f"  - {a}({ma['date_str']}) → {b}({mb['date_str']})  signals={sorted(info['signals'])}")
            print(f"    A: {ma['title'][:50]}")
            print(f"    B: {mb['title'][:50]}")
        return

    if args.dump_candidates:
        out_path = Path(args.dump_candidates)
        rows = []
        for (a, b), info in candidates.items():
            ma, mb = id_to_meta[a], id_to_meta[b]
            rows.append({
                "from": a,
                "to": b,
                "A": {"id": a, "title": ma["title"], "date": ma["date_str"]},
                "B": {"id": b, "title": mb["title"], "date": mb["date_str"]},
                "evidence_hint": info["evidence"][:300],
                "signals": sorted(info["signals"]),
            })
        out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[dump] {len(rows)} candidates → {out_path}")
        return

    if args.load_judgments:
        judgments_path = Path(args.load_judgments)
        judgments = json.loads(judgments_path.read_text(encoding="utf-8"))
        print(f"\n[load] {len(judgments)} judgments from {judgments_path}")

        cand_lookup = {(a, b): info for (a, b), info in candidates.items()}
        iterates_out, supersedes_out = [], []
        kept, skipped, missing = 0, 0, 0

        for j in judgments:
            a, b = j.get("from"), j.get("to")
            rel = j.get("rel", "neither")
            conf = float(j.get("confidence", 0.0))
            reason = (j.get("reason", "") or "")[:50]

            info = cand_lookup.get((a, b))
            if not info:
                missing += 1
                continue
            if rel == "neither" or conf < KEEP_CONFIDENCE_MIN:
                skipped += 1
                continue

            record = {
                "from": a,
                "to": b,
                "rel": rel,
                "evidence": info["evidence"][:300],
                "confidence": conf,
                "extracted_by": "llm_judge_v2",
                "extracted_at": cn_now_iso(),
                "signals": sorted(info["signals"]),
                "reason": reason,
            }
            if rel == "iterates":
                iterates_out.append(record)
            elif rel == "supersedes":
                supersedes_out.append(record)
            kept += 1

        OUT_ITERATES.parent.mkdir(parents=True, exist_ok=True)
        with OUT_ITERATES.open("w", encoding="utf-8") as f:
            for r in iterates_out:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        with OUT_SUPERSEDES.open("w", encoding="utf-8") as f:
            for r in supersedes_out:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        print(f"[load] kept:      {kept}  (iterates={len(iterates_out)}, supersedes={len(supersedes_out)})")
        print(f"[load] skipped:   {skipped} (neither/低置信)")
        print(f"[load] missing:   {missing} (judgment 中的对没在 candidates 里,候选已变?)")
        print(f"[load] {OUT_ITERATES.name}: {len(iterates_out)} 条")
        print(f"[load] {OUT_SUPERSEDES.name}: {len(supersedes_out)} 条")
        return

    print(f"\n=== Stage 2: LLM 判定 ({len(candidates)} 候选) ===")
    iterates_out, supersedes_out, stats = stage_2_judge(
        candidates, id_to_meta, client, model
    )
    print(f"\n[2] iterates kept:    {len(iterates_out)}")
    print(f"[2] supersedes kept:  {len(supersedes_out)}")
    print(f"[2] skipped (neither/低置信): {stats['skipped']}")
    print(f"[2] failed (LLM 错误): {stats['failed']}")

    print("\n=== Stage 3: 写 v2 文件 ===")
    OUT_ITERATES.parent.mkdir(parents=True, exist_ok=True)
    with OUT_ITERATES.open("w", encoding="utf-8") as f:
        for r in iterates_out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with OUT_SUPERSEDES.open("w", encoding="utf-8") as f:
        for r in supersedes_out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[3] {OUT_ITERATES.name}: {len(iterates_out)} 条")
    print(f"[3] {OUT_SUPERSEDES.name}: {len(supersedes_out)} 条")
    print("\n[next] 人工抽查后:")
    print(f"  mv {OUT_ITERATES.name} iterates.jsonl")
    print(f"  mv {OUT_SUPERSEDES.name} supersedes.jsonl")


if __name__ == "__main__":
    main()
