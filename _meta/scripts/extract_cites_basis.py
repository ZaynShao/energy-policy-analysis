#!/usr/bin/env python3
"""
extract_cites_basis.py
Step 6c — 抽 cites_basis (第 8 类 typed relation,见 schema_v3.md §6.3)

输入:
  - 0_raw/policies/*.md (289 篇 frontmatter + body)
  - 1_extracted/relations/references.jsonl (135 条 regex 文号匹配)

输出:
  - 1_extracted/relations/cites_basis.draft.jsonl
    (人工抽查后 mv 成 cites_basis.jsonl)

3 阶段管道:
  3a 位置过滤  - 读 references → evidence 落在政策开头 800 字符的保留
  3b LLM 语义  - MiniMax 判定 basis / clause_ref / context_mention,只留 basis
  3c 标题补漏  - 对 ⭐≥4 政策开头扫《xxx》引用 → 政策标题倒排匹配

环境变量:
  MINIMAX_API_KEY    必填(--dry-run 时可省)
  MINIMAX_BASE_URL   可选,默认 https://api.minimax.chat/v1
                     国际域名走 https://api.minimaxi.com/v1
  MINIMAX_MODEL      可选,默认 abab6.5s-chat

用法:
  export MINIMAX_API_KEY=sk-cp-...
  python3 extract_cites_basis.py             # 正式跑
  python3 extract_cites_basis.py --dry-run   # 跳过 3b,只看候选量
"""

import os
import re
import sys
import json
import yaml
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

from openai import OpenAI, OpenAIError

# ---------- 配置 ----------
VAULT_ROOT = Path.home() / "Documents/Zayn Main/政策分析"
POLICIES_DIR = VAULT_ROOT / "0_raw/policies"
REFERENCES_JSONL = VAULT_ROOT / "1_extracted/relations/references.jsonl"
OUTPUT_JSONL = VAULT_ROOT / "1_extracted/relations/cites_basis.draft.jsonl"

OPENING_CHAR_LIMIT = 800
HIGH_SCORE_THRESHOLD = 4
LLM_TEMPERATURE = 0.0
LLM_MAX_TOKENS = 600   # M 系列是 reasoning model,需要 <think> 思考空间

# from 政策标题含这些词的不参与 cites_basis(它们是解读/报道/转载文,不是政策本体)
EXCLUDE_FROM_TITLE_KEYWORDS = ["解读", "报道", "答记者问", "转载"]

DEFAULT_BASE_URL = "https://api.minimax.chat/v1"
DEFAULT_MODEL = "MiniMax-M2"

CST = timezone(timedelta(hours=8))


# ---------- 工具 ----------
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
    return fm, parts[2].lstrip("\n")


def build_id_to_meta():
    id_to_meta = {}
    for md in POLICIES_DIR.glob("*.md"):
        fm, body = parse_frontmatter(md)
        pid = fm.get("id")
        if not pid:
            continue
        id_to_meta[pid] = {
            "title": fm.get("title", ""),
            "importance": int(fm.get("重要性", 0) or 0),
            "body": body,
            "path": md,
        }
    return id_to_meta


def is_commentary_like(meta) -> bool:
    """from 政策标题含解读/报道/答记者问/转载 等词的视为非政策本体,不参与 cites_basis"""
    title = (meta.get("title") or "").strip()
    return any(kw in title for kw in EXCLUDE_FROM_TITLE_KEYWORDS)


def find_evidence_position(body: str, evidence: str) -> int:
    if not evidence:
        return -1
    idx = body.find(evidence)
    if idx >= 0:
        return idx
    if len(evidence) >= 20:
        sub = evidence[5:-5]
        idx = body.find(sub)
        if idx >= 0:
            return idx - 5
    return -1


# ---------- 阶段 3a ----------
def stage_3a_position_filter(refs, id_to_meta):
    candidates = []
    for ref in refs:
        from_id = ref["from"]
        meta = id_to_meta.get(from_id)
        if not meta:
            continue
        if is_commentary_like(meta):
            continue
        pos = find_evidence_position(meta["body"], ref["evidence"])
        if 0 <= pos < OPENING_CHAR_LIMIT:
            candidates.append({
                **ref,
                "_position": pos,
                "_from_title": meta["title"],
                "_from_opening": meta["body"][:OPENING_CHAR_LIMIT],
            })
    return candidates


# ---------- 阶段 3b ----------
JUDGE_SYSTEM_PROMPT = """你是政策文本分析专家。给定一段政策开头文字和它对另一份政策的引用,判定这次引用的语义类别。

类别定义(三选一):
- basis: 把被引政策作为本政策的"制定依据"或"基础框架"。常见标志在开头段:"根据《X》"、"依据《X》"、"按照《X》要求"、"贯彻落实《X》精神"、"参照《X》执行"。
- clause_ref: 引用被引政策的某个具体条款或局部规定,不是整体依据。常见标志:"按照《X》第N条"、"根据《X》关于...的规定"、"参考《X》中的标准"。
- context_mention: 仅作为背景或过往沿革提及。常见标志:"在《X》出台后"、"《X》以来"、"继《X》之后"。

输入会以 JSON 给出 from_policy_title / from_opening_excerpt / to_policy_doc_num / evidence。
输出严格 JSON,只一个对象,不要 markdown:
{"semantic": "basis" | "clause_ref" | "context_mention", "confidence": 0.0-1.0}"""


THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
JSON_OBJ_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)


def parse_llm_json(raw: str):
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


def stage_3b_llm_judge(candidates, client, model):
    results = []
    for i, c in enumerate(candidates, 1):
        user_payload = json.dumps({
            "from_policy_title": c["_from_title"],
            "from_opening_excerpt": c["_from_opening"],
            "to_policy_doc_num": c.get("doc_num_matched", ""),
            "evidence": c["evidence"],
        }, ensure_ascii=False)

        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_payload},
                ],
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
            )
            raw = resp.choices[0].message.content or ""
            judgment = parse_llm_json(raw)
        except (OpenAIError, json.JSONDecodeError, ValueError, AttributeError) as e:
            print(f"[3b warn {i}/{len(candidates)}] {c['from']} → {c['to']}: {type(e).__name__}: {e}",
                  file=sys.stderr)
            continue

        semantic = judgment.get("semantic")
        confidence = float(judgment.get("confidence", 0.0))

        if semantic != "basis":
            print(f"[3b skip {i}/{len(candidates)}] {c['from']} → {c['to']}  ({semantic}, {confidence:.2f})")
            continue

        results.append({
            "from": c["from"],
            "to": c["to"],
            "rel": "cites_basis",
            "evidence": c["evidence"],
            "location": "opening",
            "semantic": "basis",
            "confidence": confidence,
            "extracted_by": "regex_filter+llm_judge",
            "extracted_at": cn_now_iso(),
        })
        print(f"[3b keep {i}/{len(candidates)}] {c['from']} → {c['to']}  (conf={confidence:.2f})")
    return results


# ---------- 阶段 3c ----------
TITLE_QUOTE_RE = re.compile(r"《([^》《]{5,80})》")


def stage_3c_title_match(id_to_meta, existing_pairs):
    title_to_id = {}
    for pid, meta in id_to_meta.items():
        title = (meta["title"] or "").strip()
        if title and title not in title_to_id:
            title_to_id[title] = pid

    results = []
    for from_id, meta in id_to_meta.items():
        if meta["importance"] < HIGH_SCORE_THRESHOLD:
            continue
        if is_commentary_like(meta):
            continue
        opening = meta["body"][:OPENING_CHAR_LIMIT]
        from_title = (meta["title"] or "").strip()
        for m in TITLE_QUOTE_RE.finditer(opening):
            cited = m.group(1).strip()
            if not cited or cited == from_title:
                continue

            to_id = None
            if cited in title_to_id:
                to_id = title_to_id[cited]
            else:
                for cand_title, cand_id in title_to_id.items():
                    if cand_id == from_id:
                        continue
                    if len(cited) >= 10 and (cited in cand_title or cand_title in cited):
                        to_id = cand_id
                        break

            if not to_id or to_id == from_id:
                continue
            pair = (from_id, to_id)
            if pair in existing_pairs:
                continue

            start = max(0, m.start() - 30)
            end = min(len(opening), m.end() + 30)
            evidence = opening[start:end]
            results.append({
                "from": from_id,
                "to": to_id,
                "rel": "cites_basis",
                "evidence": evidence,
                "location": "opening",
                "semantic": "basis",
                "confidence": 0.85,
                "extracted_by": "title_match",
                "extracted_at": cn_now_iso(),
            })
            existing_pairs.add(pair)
            print(f"[3c add] {from_id} → {to_id}  ({cited[:30]}...)")
    return results


# ---------- LLM ping ----------
def ping_llm(client, model):
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Reply with literally 'pong' only."},
                {"role": "user", "content": "ping"},
            ],
            temperature=0.0,
            max_tokens=20,
        )
        body = (resp.choices[0].message.content or "").strip()
        print(f"[ping] {model} responded: {body[:40]!r}")
        return True
    except Exception as e:
        print(f"[ping FAIL] {type(e).__name__}: {e}", file=sys.stderr)
        return False


# ---------- main ----------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="跳过 3b LLM 调用,只产 stage 3a + 3c")
    args = parser.parse_args()

    base_url = os.environ.get("MINIMAX_BASE_URL", DEFAULT_BASE_URL)
    model = os.environ.get("MINIMAX_MODEL", DEFAULT_MODEL)
    api_key = os.environ.get("MINIMAX_API_KEY")

    if not args.dry_run and not api_key:
        print("[fatal] 未设置 MINIMAX_API_KEY,export 后重试", file=sys.stderr)
        sys.exit(2)

    client = None
    if not args.dry_run:
        client = OpenAI(api_key=api_key, base_url=base_url)
        print(f"[init] base_url: {base_url}")
        print(f"[init] model:    {model}")
        if not ping_llm(client, model):
            print("[fatal] LLM ping 失败,检查 MINIMAX_BASE_URL / API key / model 名", file=sys.stderr)
            sys.exit(3)

    print(f"[init] vault: {VAULT_ROOT}")
    print(f"[init] output: {OUTPUT_JSONL}")
    print(f"[init] dry_run: {args.dry_run}")

    id_to_meta = build_id_to_meta()
    print(f"[init] policies indexed: {len(id_to_meta)}")

    refs = []
    with REFERENCES_JSONL.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                refs.append(json.loads(line))
    print(f"[init] references loaded: {len(refs)}")

    print("\n=== Stage 3a: 位置过滤 ===")
    candidates = stage_3a_position_filter(refs, id_to_meta)
    print(f"[3a] kept {len(candidates)} / {len(refs)} (落在前 {OPENING_CHAR_LIMIT} 字符)")

    if args.dry_run:
        print("\n[dry-run] 跳过 3b LLM 判定")
        print("[dry-run] 候选样例 (前 5):")
        for c in candidates[:5]:
            print(f"  - {c['from']} → {c['to']}  pos={c['_position']}")
            print(f"    evidence: {c['evidence'][:80]}...")
        basis_from_refs = []
    else:
        print(f"\n=== Stage 3b: LLM 语义判定 ===")
        basis_from_refs = stage_3b_llm_judge(candidates, client, model)
        print(f"[3b] kept {len(basis_from_refs)} / {len(candidates)} as basis")

    print(f"\n=== Stage 3c: 标题引用补漏 (⭐≥{HIGH_SCORE_THRESHOLD}) ===")
    existing_pairs = {(r["from"], r["to"]) for r in basis_from_refs}
    title_added = stage_3c_title_match(id_to_meta, existing_pairs)
    print(f"[3c] added {len(title_added)}")

    all_results = basis_from_refs + title_added
    OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_JSONL.open("w", encoding="utf-8") as f:
        for r in all_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n[done] {len(all_results)} cites_basis 写入 {OUTPUT_JSONL.name}")
    by_method = {}
    for r in all_results:
        by_method[r["extracted_by"]] = by_method.get(r["extracted_by"], 0) + 1
    for k, v in by_method.items():
        print(f"  - {k}: {v}")
    print(f"\n[next] 人工抽查后:  mv {OUTPUT_JSONL.name} cites_basis.jsonl")


if __name__ == "__main__":
    main()
