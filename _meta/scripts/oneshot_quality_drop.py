#!/usr/bin/env python3
"""一次性 — 基于 hard-pattern 把 normalize 后的 junk 政策移到 archive。

复用模式:每次 normalize 后(new_files.jsonl 写入新批),跑此脚本筛 junk。
默认 dry-run;加 --apply 执行 mv + 写 drops log。

Hard junk pattern(P0 refetch 经验,误判风险低):
  报告 / 答复 / 提案 / 投诉 / 建议 / 咨询 / 回复 / 新闻 / 通报 / 简报 /
  快讯 / 消息 / 动态 / 资讯 / 解读 / 问答 / 访谈 / 述评 / 介绍 /
  征集 / 征求意见 / 统计 / 运行情况 / 月报 / 季报 / 年报 /
  会议 / 论坛 / 讲话 / 致辞 / 喜报 / 公示 / 目录 / 索引

Strong override(若标题同时含)→ 不 drop:
  措施 / 办法 / 方案 / 通知 / 规定 / 意见 / 细则 / 规划 / 决定 / 实施
"""
import argparse
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

VAULT = Path(__file__).resolve().parents[2]
NEW_FILES_LOG = VAULT / "_meta" / "audit_2026-05-06" / "new_files.jsonl"
RAW = VAULT / "0_raw" / "policies"

JUNK_PATTERNS = [
    r"答复", r"提案", r"投诉", r"建议", r"咨询", r"回复",
    r"新闻", r"通报", r"简报", r"快讯", r"消息", r"动态", r"资讯",
    r"解读", r"问答", r"访谈", r"述评", r"介绍", r"答记者问",
    r"征集", r"征求意见", r"公开征求",
    r"统计", r"运行情况", r"月报", r"季报", r"年报",
    r"会议", r"论坛", r"讲话", r"致辞", r"调研",
    r"报告", r"喜报", r"公示", r"目录", r"索引",
    # 2026-05-08 A.1 校准补充(媒体/网页框架/headline)
    r"媒体报道", r"人民日报", r"新华社", r"新华网", r"长者版", r"无障碍",
    r"工作总结", r"工作要点", r"工作动态", r"发布会",
    r"如何\?", r"如何？", r"为何\?", r"为何？",  # 反问标题 = news/think piece
]
STRONG_OVERRIDE = [
    r"措施", r"办法", r"方案", r"通知", r"规定", r"意见",
    r"细则", r"规划", r"决定", r"实施", r"指导意见", r"行动计划",
]


def parse_title_from_filename(fn):
    m = re.match(r"【(.+?)(?:[(（]([^)）]+)[)）])?】-(.*?)-([0-9a-f]+)\.md", fn)
    if not m:
        return fn, ""
    title, on, _, _ = m.groups()
    return title, (on or "")


# 2026-05-08 A.1 校准:这些 pattern 即便共存 strong_override 也是 junk
# (因为标题里的 strong word 是政策被引用,而文档本身是 meta-content)
HARD_JUNK = [
    r"解读", r"答记者问", r"媒体报道", r"人民日报", r"新华社", r"新华网",
    r"答复", r"提案", r"建议", r"咨询", r"投诉",
    r"问答", r"访谈", r"述评", r"喜报",
    r"长者版", r"无障碍",
]


def classify(title, on):
    hard_hits = [p for p in HARD_JUNK if re.search(p, title)]
    if hard_hits:
        return "junk", hard_hits
    junk_hits = [p for p in JUNK_PATTERNS if re.search(p, title)]
    strong_hits = [p for p in STRONG_OVERRIDE if re.search(p, title)]
    if junk_hits and not strong_hits and not on:
        return "junk", junk_hits
    if strong_hits or on:
        return "strong", strong_hits
    return "unknown", []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="执行 mv + 写 drops log(默认 dry-run)")
    ap.add_argument("--batch", required=True,
                    help="批次名,如 a1 / a2(用于 archive 子目录命名)")
    args = ap.parse_args()

    today = datetime.now().strftime("%Y-%m-%d")
    archive_dir = VAULT / "0_raw" / "_archive" / "policies" / f"p2_7_{args.batch}_drops_{today}"
    drops_log = VAULT / "_meta" / "audit" / f"p2_7_{args.batch}_drops_{today}.jsonl"

    junk = []; strong = []; unknown = []
    with NEW_FILES_LOG.open() as f:
        for ln in f:
            if not ln.strip():
                continue
            r = json.loads(ln)
            title, on = parse_title_from_filename(r["filename"])
            cat, hits = classify(title, on)
            entry = {**r, "title": title, "official_number": on, "hits": hits}
            (junk if cat == "junk" else strong if cat == "strong" else unknown).append(entry)

    print(f"=== quality_drop ({args.batch}, {len(junk)+len(strong)+len(unknown)} new files) ===")
    print(f"  junk:    {len(junk):>3}  → drop")
    print(f"  strong:  {len(strong):>3}  → keep, send to trigger A")
    print(f"  unknown: {len(unknown):>3}  → keep, let 5C audit gate decide")

    if not args.apply:
        print("\n--- DRY RUN (use --apply to execute) ---")
        print("\n--- junk samples ---")
        for e in junk[:5]:
            print(f"  [{','.join(e['hits'])}] {e['title'][:60]}")
        return

    archive_dir.mkdir(parents=True, exist_ok=True)
    drops_log.parent.mkdir(parents=True, exist_ok=True)
    moved = 0
    with drops_log.open("w") as logf:
        for e in junk:
            src = RAW / e["filename"]
            if not src.exists():
                continue
            dst = archive_dir / e["filename"]
            shutil.move(str(src), str(dst))
            logf.write(json.dumps({
                "pid": e["pid"], "title": e["title"],
                "filename": e["filename"], "url": e["url"],
                "hits": e["hits"], "reason": "hard_junk_pattern",
                "archived_to": str(dst.relative_to(VAULT)),
                "archived_at": datetime.now().isoformat(timespec="seconds"),
            }, ensure_ascii=False) + "\n")
            moved += 1

    keep_pids = [e["pid"] for e in strong + unknown]
    keep_pids_file = VAULT / "_meta" / "audit_2026-05-06" / f"keep_pids_{args.batch}.txt"
    keep_pids_file.write_text("\n".join(keep_pids))

    print(f"\n=== APPLIED ===")
    print(f"  moved {moved} junk → {archive_dir.relative_to(VAULT)}/")
    print(f"  drops log → {drops_log.relative_to(VAULT)}")
    print(f"  keep_pids ({len(keep_pids)}) → {keep_pids_file.relative_to(VAULT)}")


if __name__ == "__main__":
    main()
