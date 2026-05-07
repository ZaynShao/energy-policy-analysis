"""统一 isolated 过滤 helper

源 of truth:`_meta/audit/isolated_classification.jsonl`(B7 LLM 分类落地)
fm tag `classified_main_graph_exclude` 是给 Obsidian graph view 用的过滤元数据,
但 Python 脚本一律以 jsonl 为准 — 单一权威来源,刷 jsonl 后 deterministic
post-llm 即可全派生层同步。

用法:
    from _isolated_filter import load_exclude_pids
    EXCLUDE = load_exclude_pids()
    if pid in EXCLUDE: continue
"""
import json
from pathlib import Path

_VAULT = Path(__file__).resolve().parents[2]
_AUDIT_JSONL = _VAULT / "_meta" / "audit" / "isolated_classification.jsonl"


def load_exclude_pids() -> set[str]:
    """返回 suggested_action='exclude_from_main_graph' 的 pid 集合(B7 79 个 noise 政策)"""
    if not _AUDIT_JSONL.exists():
        return set()
    out: set[str] = set()
    for ln in _AUDIT_JSONL.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if r.get("suggested_action") == "exclude_from_main_graph":
            out.add(r["pid"])
    return out
