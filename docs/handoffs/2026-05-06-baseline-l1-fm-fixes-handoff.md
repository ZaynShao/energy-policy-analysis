---
date: 2026-05-06
session_origin: 本会话末尾(commits 3369d8e → c2cf47c, 6 commits)
focus: L1 raw frontmatter baseline 数据修复(3a + 3b)
estimated_total_work: ~2 小时(3a 30min + 3b 1.5h)
risk_tier: 中(raw 写入 + 145 文件批量改 fm)
prerequisite_commit: c2cf47c
---

# Baseline L1 Frontmatter 修复 Handoff

## 背景

Stage 1 audit 工具集(commit 3369d8e)发现 L1 raw 评论侧两类 baseline 数据漂移:
- **3a**:14 篇评论 fm 残留 LLM 派生业务字段(`scores` / `重要性` / `价值标签` / `行动分类`)— reclassify 时漏净化
- **3b**:145 篇评论 fm 用 v2 schema 字段名(`url`/`date` 而非 v3 的 `source_url`/`date_published`)

这些 baseline 问题**不在前会话(c2cf47c)的修复范围**,前会话只接了"前置闸"防止新数据再次引入,但未清理历史数据。

**为何要现在修?** 不是为了 lint 美观,而是修复**静默 bug**:
- callsite 分析(grep fm.get):评论侧脚本(rebuild_l2 prepare_commentary_change / aggregate_opinions / oneshot_b3 / wewe_rss)已全部读 v3 字段(`source_url` / `date_published` / `source_account`)
- 145 v2 评论被这些脚本读时,`fm.get("source_url")` 返回空 → stance LLM judge 拿不到 source domain → 共识门槛"≥3 distinct domain"命中率被压低
- handoff `2026-04-30-l1-l2-completeness-handoff.md` T10 写到"stance source 不为 `?` 占比仅 ~30%",**这就是 root cause 之一**(另一原因是无 source_url 评论)

修完 3b 直接受益:stance source 命中率应从 ~30% → ~70%,handoff §T10 目标自动达成。

## 必读文档(按顺序)

1. **`CLAUDE.md`** — 项目级规则,**特别是 §1 Raw immutable + §6 重抓重入例外**
2. **`.claude/skills/policy-vault-l2-rebuild/SKILL.md`** — 维护协议,**特别是 §6 重抓重入例外协议**(本任务的合规依据)
3. **本文档** — 任务详细
4. 参考:`_meta/schema_v3.md` §5 评论 frontmatter schema(权威)

## 任务

### 3a [30min] — 14 评论 fm 净化

**问题**:14 篇评论(都带 `_migrated_from: policies`)从政策迁移到评论时,带过来 `scores / 重要性 / 价值标签 / 行动分类` 等 LLM 派生业务字段。这违反 LLM Wiki §1(raw immutable)和 §2(派生分层)— 这些字段属 `_meta/business_view/{pid}.yaml`,不属 raw fm。

**字段操作**:删除以下 fm 字段(若存在):
- `scores`
- `重要性`
- `行动分类`
- `价值标签`
- `archive`(派生层标记,不属 raw)

**保留**(评论 v3 schema 字段 + 迁移 audit 字段):
- `id` / `title` / `official_number` / `issuer` / `date` / `region` / `provenance` / `tags` / `type`
- `_migrated_from` / `_migrated_at` / `issuer_canonical`
- `_review_needed_related_policy` / `related_policy` / `related_policy_source` / `related_policy_confidence` / `related_policy_matched_at`

**协议**(走 SKILL.md §6 重抓重入例外的"轻量字段修正"分支):
1. 备份原文件到 `0_raw/_archive/commentaries/{filename}__pre_l12_purge_<timestamp>.md`
2. 修改 fm:删除上述 5 个字段
3. 加 audit 字段到 provenance(或顶层 frontmatter):
   ```yaml
   provenance:
     # 原字段保留
     l12_residue_purged_at: '2026-05-06T...+08:00'
     l12_residue_purged_fields: [scores, 重要性, 价值标签, 行动分类]
   ```
4. body 完全不改

**验证**:
```bash
python3 _meta/scripts/oneshot_l12_residue_audit.py --commentaries-only --json | python3 -c "
import json, sys
d = json.load(sys.stdin)
v = [i for i in d['items'] if i['level']=='violation' and i['code']=='fm_forbidden_field']
print(f'残留 violations: {len(v)} (target: 0)')
"
```
应输出 `残留 violations: 0`。

### 3b [1.5h] — 145 评论 v2 → v3 字段重命名

**问题**:145 评论 fm 字段名是 v2 schema(`url` / `date` / `source`)而非 v3(`source_url` / `date_published` / `source_account`)。callsite 分析显示评论侧脚本已读 v3,导致 145 评论 stance 抽取时元信息全空 → source 命中率低。

**字段映射**:
| v2 字段 | v3 字段 | 处理 |
|---|---|---|
| `url` | `source_url` | 重命名 |
| `date` | `date_published` | 重命名 |
| `source` | `source_account` | 重命名(注意 wewe-rss 评论已是 `source: wewe-rss` 表示 source 类别 ≠ source_account 公众号名;需判断,可能不能简单重命名) |
| `date: '未知'` | `date_published: null` | 78 篇 placeholder 转 null(让脚本读到 null 不是字面 '未知') |
| `confidence`(评论顶层) | `provenance.confidence` | 移到 provenance(若 provenance 已存在 confidence,以现有为准) |
| `collected_by` / `collected_at`(顶层) | `provenance.collected_by` / `provenance.fetched_at` | 移入 provenance |

**关键判断 — `source` 字段歧义**:
- 145 评论里 `source: pdf.dfcfw.com` 类(域名)→ 应改 `source_account`(若是公众号名)或保留为 `provenance` 子字段
- 145 评论里 `source: wewe-rss`(系统标识)→ 不要改(这是 v3 也用的 `source: wewe-rss` 标识符)
- 实际:**先 grep 看 145 评论里 source 字段值的分布**,再决定如何映射

**协议**(走 SKILL.md §6 重抓重入例外):
1. 备份原文件到 `0_raw/_archive/commentaries/{filename}__pre_v3_migration_<timestamp>.md`
2. 修改 fm:重命名字段
3. 加 audit 字段:
   ```yaml
   provenance:
     # 原字段保留
     fm_v3_migrated_at: '2026-05-06T...+08:00'
     fm_v3_migrated_from_v2: true
   ```
4. body 完全不改

**验证**:
```bash
python3 _meta/scripts/validate_l1.py --commentaries-only --json | python3 -c "
import json, sys
from collections import Counter
d = json.load(sys.stdin)
c = Counter((v['level'], v['code']) for v in d['violations'])
for k, n in sorted(c.items(), key=lambda x: -x[1]):
    print(f'  {n} {k[0]} {k[1]}')
"
```
target:
- `schema_v2_alias` warns:223 → 0
- `bad_date_format`(date='未知')errors:78 → 0
- `missing_required` errors:120 → ≤30(只剩真缺字段的早期 PDF 评论)

## 实现策略

写 oneshot 脚本 `_meta/scripts/oneshot_l12_baseline_purge_3a.py` + `oneshot_baseline_v2_to_v3_3b.py`:
- `--dry-run`(默认)只报会改什么,不写
- `--apply` 真改 + 备份
- 每篇文件输出:before / after fm + audit 字段位置
- 进度条 + 错误列表

## 已知风险

1. **3a 14 评论删字段**:这些字段对应的业务判断信息(scores 等)迁移时**没**进 `_meta/business_view/`,删了就丢失。但 — handoff `2026-04-29` Stage 1 已说明这些是"reclassify 漏净化",且评论本身不需要 business_view scores(那是政策才有)。**确认丢失这些字段无下游消费者**(grep 确认无脚本读这 14 评论的 scores)
2. **3b source 字段歧义**(见上)— 必须先 sample 看分布
3. **3b 145 文件批量改 raw**:任一 bug 影响 145 篇。**强烈建议**:
   - 先 dry-run 全 145,人工 spot-check 5 篇 before/after
   - 确认无误后再 --apply
   - apply 后立即 git diff 看实际写了什么
4. **wewe-rss 同源评论可能 v3 已经齐**:确认 145 篇都是非 wewe-rss 的早期评论(grep `^source: wewe-rss`)
5. **v2 评论里部分字段值含特殊格式**(如 `date: 未知` 已经是字符串非日期)— 重命名时要处理 null/未知/空值的 case

## 验证步骤(逐项 check)

每完成一项跑:

```bash
cd "/Users/shaoziyuan/Documents/Zayn Main/政策分析"

# 1. 数据合规
python3 _meta/scripts/validate_l1.py --commentaries-only
python3 _meta/scripts/oneshot_l12_residue_audit.py --commentaries-only

# 2. 备份完整
ls 0_raw/_archive/commentaries/ | wc -l   # 应 = 14 + 145 = 159

# 3. 数据流验证(stance 抽取能拿到 source domain 了吗)
# 不必跑全量 P5b — 只 sample 几个改过的评论,看 prepare_commentary_change 的输出
python3 _meta/scripts/rebuild_l2.py prepare --trigger commentary_change --commentaries "<改过的评论文件名 1>,<改过的 2>" 2>&1 | grep -A2 "linked commentaries"
# (此命令会真 stage 5 batches,如不想跑只是 dry-test,改到测试目录)
```

## Commit 节奏

**强烈建议**:**3a 和 3b 各自一个独立 commit**(handoff "提交节奏:小步、可回滚"):
1. commit "fix(L1.2 净化): 14 评论 fm 删 LLM 派生残留字段"
2. commit "fix(v3 migration): 145 评论 fm 字段名 v2 → v3"

**不要**一个大 commit 把两个任务揉一起。

## 不做事项

- ❌ **不重跑 stance / 不重生 opinions-summary**(L3 范畴,留给后续)
- ❌ **不动政策侧 fm**(政策 v3 已合规,只评论侧需修)
- ❌ **不删除评论 body**(只改 fm)
- ❌ **不动评论 `related_policy` / `related_policy_source` / `related_policy_matched_at`**(B4 LLM 重判结果,合规)

## 工具速查

```bash
cd "/Users/shaoziyuan/Documents/Zayn Main/政策分析"

# audit 工具(本任务输入)
python3 _meta/scripts/oneshot_l12_residue_audit.py --commentaries-only --json
python3 _meta/scripts/validate_l1.py --commentaries-only --json

# 文件清单(本 handoff 附录)
python3 _meta/scripts/oneshot_l12_residue_audit.py --commentaries-only --json | python3 -c "
import json, sys
d = json.load(sys.stdin)
for f in sorted({v['file'] for v in d['items'] if v['level']=='violation'}):
    print(f)
"  # → 14 篇

python3 _meta/scripts/validate_l1.py --commentaries-only --json | python3 -c "
import json, sys
d = json.load(sys.stdin)
for f in sorted({v['file'] for v in d['violations'] if v['code']=='schema_v2_alias'}):
    print(f)
"  # → 145 篇

# git
git log --oneline -7   # 应看到本 handoff 之前 6 commit:3369d8e → c2cf47c
```

## 关键判断准则

**走前问 3 句**(handoff `2026-04-30-l1-l2-completeness-handoff.md` 的关键判断准则):
1. 这个改动是 L1 还是 L2?(L1 — raw 写入)
2. raw immutable 检查通过吗?(走 §6 重抓重入例外协议:备份 + audit 字段)
3. 是 push 还是 demand-pull?(demand — stance source 命中率 / lint baseline 清理触发)

**raw 写入操作的 safety check**(每篇文件改前):
- 备份到 `_archive/commentaries/` 已完成?
- audit 字段已加?
- body 完全不动?
