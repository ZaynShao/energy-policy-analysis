#!/usr/bin/env python3
"""
oneshot: 给 9 主题 opinions-summary.md 末尾加 graph 兜底段。

opinions-summary §1/§2/§3 段落用 [[P_xxx]] alias 引用,Obsidian Graph view
对 alias-resolved link 不一定建边(已知 behavior)。本脚本在末尾加 §6 段
"全部相关政策(graph 用)",用 [[<raw 文件名>|P_xxx]] 显式形式列举所有
opinion_pids ∪ uncovered_pids,确保 graph view 中 opinions-summary 节点
连到所有 N 个相关政策。

读 _meta/{theme}_input.json 拿全部政策清单。

可重复跑(检查并替换已存在的"# 关联政策(graph)"段)。
"""
from __future__ import annotations
import json
import re
from pathlib import Path

import yaml

VAULT = Path(__file__).resolve().parent.parent.parent
THEMES_DIR = VAULT / "2_crystallized" / "themes"

GRAPH_SECTION_HEADER = "# 关联政策清单(graph 兜底)"
SECTION_RE = re.compile(
    rf"\n{re.escape(GRAPH_SECTION_HEADER)}.*?(?=\n#{{1,2}}\s|\Z)", re.DOTALL
)


def load_pid_to_filestem() -> dict:
    pid_to_stem = {}
    for p in (VAULT / "0_raw" / "policies").glob("*.md"):
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if not txt.startswith("---"):
            continue
        end = txt.find("---", 3)
        try:
            fm = yaml.safe_load(txt[3:end]) or {}
        except yaml.YAMLError:
            continue
        if fm.get("id"):
            pid_to_stem[fm["id"]] = (p.stem, fm.get("title", "") or "")
    return pid_to_stem


def render_graph_section(pids: list[str], pid_to_stem: dict) -> str:
    lines = [GRAPH_SECTION_HEADER, ""]
    lines.append(
        "> 此段为 Obsidian Graph View 兜底:用真实文件名 [[]] link 列举本主题"
        "全部相关政策,确保 graph view 显示该主题与各政策的连接边。"
    )
    lines.append("")
    for pid in sorted(pids):
        if pid not in pid_to_stem:
            continue
        stem, title = pid_to_stem[pid]
        lines.append(f"- [[{stem}|{pid}]] — {title[:60]}")
    return "\n".join(lines) + "\n"


def main() -> int:
    pid_to_stem = load_pid_to_filestem()
    print(f"loaded {len(pid_to_stem)} raw policies pid → file stem map")

    # 9 主题
    summaries = sorted(THEMES_DIR.glob("*/opinions-summary.md"))
    if not summaries:
        print("no opinions-summary.md found")
        return 1

    for s in summaries:
        theme_dir = s.parent
        # 读 _input.json 拿全部 policy ids
        inp = theme_dir / "_input.json"
        if not inp.exists():
            print(f"  [skip] {theme_dir.name}: no _input.json")
            continue
        d = json.loads(inp.read_text(encoding="utf-8"))
        all_pids = [p["id"] for p in d.get("policies", [])]

        text = s.read_text(encoding="utf-8")
        # 移除已存在的 graph 兜底段(若有)
        text = SECTION_RE.sub("", text).rstrip() + "\n\n"
        # append 新段
        text += render_graph_section(all_pids, pid_to_stem)
        s.write_text(text, encoding="utf-8")
        n = sum(1 for p in all_pids if p in pid_to_stem)
        print(f"  ✓ {theme_dir.name}: +graph 段 {n} 个政策 link")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
