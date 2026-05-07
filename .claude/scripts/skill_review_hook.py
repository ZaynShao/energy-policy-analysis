#!/usr/bin/env python3
"""PreCompact hook — 在 compact 之前注入 SKILL.md review 任务

设计:LLM 不直接 Write SKILL.md,只在 compact summary 末尾追加 "## SKILL
Review" 段产出 diff 草稿(或 NO-OP)。用户在 next session 决定是否 apply。

反向门槛:默认 NO-OP,只在产出"系统性新知识 / 未覆盖新坑 / 新数据契约"时
才输出 diff。避免 LLM 过度产出 / SKILL 膨胀。

输出:JSON to stdout(hook 协议)→ Claude Code 把 additionalContext 注入
LLM 在 compact 任务中的 context。
"""
import json
import sys

PROMPT = """[SKILL Review — Auto Hook,在生成 compact summary 之前先做]

评估本会话产出对 `.claude/skills/policy-vault-l2-rebuild/SKILL.md` 的影响。
在 compact summary 最末尾追加 "## SKILL Review" 段:

DEFAULT = NO-OP。除非满足以下任一,否则输出"无需更新 SKILL.md
(理由:本会话无系统性新知识 / 新坑 / 新数据契约)":

1. 产出可复用 pattern / 协议 / 新 trigger(non-trivial,需 §X.Y 级章节)
2. 踩了 SKILL.md 现有内容未覆盖、未来会重复的"新坑"
3. 引入新 audit 表 / helper / 履历字段(改变 vault 数据契约)

满足任一 → 输出 diff 草稿(每条):
- 目标章节:§X.Y / §X.Y.Z 新增 / 现有节追加段
- 内容:精简,不超过 SKILL.md 现有同类章节平均长度
- 理由:1 句话,为什么这是系统性而非边角

硬约束:
- LLM 不直接 Write SKILL.md(只在 compact summary 输出草稿)
- 不超过 3 条候选 — 多了说明阈值太松
- 不入 skill 的:baseline 卫生 / 数据修复 backlog / 单次脚本细节 / 已在
  SKILL.md 覆盖的内容(检查 SKILL §0-§11,避免重复)
- 草稿要可直接 copy 到 SKILL.md 后用 Edit tool apply
"""


def main() -> int:
    # PreCompact hook 不需要 stdin,但消费掉以避免 broken pipe
    try:
        sys.stdin.read()
    except OSError:
        pass

    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreCompact",
            "additionalContext": PROMPT,
        },
        "systemMessage": "[skill-review] 已注入 SKILL.md review 任务到 compact summary 末尾",
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
