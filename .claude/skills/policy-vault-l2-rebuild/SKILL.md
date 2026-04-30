---
name: policy-vault-l2-rebuild
description: 在「政策分析」vault(0_raw/policies + 0_raw/commentaries 路径下)做了 L1 改动(新政策入库/raw body 重抓/评论 frontmatter 改/关系修正/dedup)后,触发 L2 派生 + L3 结晶的全链路重建,杜绝漏跑 opinions/关系/反链/主题/business_view 等任何下游层。任何时候用户在此 vault 提到"加新政策""重抓政策""评论审阅""5C 派生""business_view yaml""反链 stale""主题 stale""opinions 失效""我刚改了 raw"——即使没说 rebuild——都必须使用此 skill。本 skill 避免了过去发现的 staleness 黑洞:opinions-summary/W1+W2 关系层/L3 重要性 bug。
---

# Policy Vault L2 Rebuild

服务于 `/Users/shaoziyuan/Documents/Zayn Main/政策分析/` vault(滴滴能源政策分析项目)。**L1 raw 一旦改动,L2/L3 派生层会出现 staleness**,本 skill 教会你识别 trigger 类型 + 跑 `_meta/scripts/rebuild_l2.py` 编排器完成全链路重建。

---

## 0. 触发判定(立即决定 trigger 类型)

读完用户当前请求,立即归类到 1 种 trigger:

| 用户做了什么 | trigger | 信号词 |
|---|---|---|
| 新政策入库(write 到 `0_raw/policies/`) | **A. pid_change** | "采集 X 政策"、"L1.3 W3"、"加 N 篇政策"、新 P_xxx 出现 |
| 现有 raw body 重抓(替换 body,frontmatter 不动) | **A. pid_change** | "重抓 PDF"、"OCR 重做"、"body 替换" |
| 评论 frontmatter 改(`related_policy` / `not_policy_related` 字段变) | **B. commentary_change** | "评论审阅"、"P4 重判"、"重新链接评论"、"批量标 not_policy_related" |
| 关系层手动加边(supersedes 等) | **C. 仅跑 deterministic post-llm** | "20 号令 supersedes 15 号令"、"加 cites_basis" |
| L1 dedup / 文件名改(pid 不变) | **C. 仅跑 deterministic post-llm** | "dedup"、"文件名规范化" |
| 全量校验或 deterministic 全跑 | **D. deterministic --scope all** | "全部重跑一遍"、"audit"、"vault 体检" |

**关键判定**:看用户是否动了 `0_raw/`。raw 没动只是 deterministic 重跑的(C/D)不需要 LLM subagent。

---

## 1. 通用工作流框架

任何 trigger 都按 4 阶段:

```
trigger → prepare(stage) → 派 subagent → apply → deterministic post-llm
            ↑                    ↑           ↑              ↑
       脚本自动             用户手动      脚本自动         脚本自动
```

主编排脚本: **`_meta/scripts/rebuild_l2.py`**(已实现,见 `--help`)

LLM 任务的 staging 状态目录: **`_l2_rebuild_state/`**(在 cwd 下,本地 only,已在 .gitignore)

---

## 2. Trigger A: pid_change(新政策 / body 重抓)

完整 5 步:

### A.1 准备阶段(`prepare`)

```bash
cd "/Users/shaoziyuan/Documents/Zayn Main/政策分析"
python3 _meta/scripts/rebuild_l2.py prepare --trigger pid_change --pids P_xxx,P_yyy,P_zzz
```

脚本自动:
- 跑 `extract_relations_regex.py --references-only`(references 重抽)
- 跑 `extract_entities.py`(W3 新政策实体入 registry)
- stage `_l2_rebuild_state/5c/inputs.jsonl` + `prompt.md`(5C 派生 LLM 任务)
- stage `_l2_rebuild_state/rel_judge/{inputs.jsonl, vault_index.jsonl, prompt.md}`(关系 LLM judge 任务)

### A.2 派 2 个 subagent(opus 4.7,可并行后台)

读 `_l2_rebuild_state/5c/prompt.md` 和 `_l2_rebuild_state/rel_judge/prompt.md` 各派 1 subagent(`run_in_background: true`)。subagent 的 results 必须写到:
- `_l2_rebuild_state/5c/results/results.jsonl`
- `_l2_rebuild_state/rel_judge/results/results.jsonl`

提示词模板已经在 prompt.md 里完整写好,不需要再加工 — 直接 copy 给 subagent 即可。如需调整决策规则,见 `references/subagent-prompts.md`。

### A.3 应用 LLM 结果(2 个 apply)

```bash
python3 _meta/scripts/rebuild_l2.py apply --stage 5c
python3 _meta/scripts/rebuild_l2.py apply --stage rel
```

`apply --stage 5c` 内部走 `oneshot_apply_5c_subagent_results.py`,写 3 处:
- `_meta/business_view/{pid}.yaml`
- `1_extracted/policy_summaries.jsonl`(upsert)
- `1_extracted/relations/derives_from.jsonl`(replace by from)

`apply --stage rel` 把 5 类关系增量写到 `1_extracted/relations/{cites_basis,iterates,extends,clarifies,aligns_with}.jsonl`(防重 by `(from, to)`)。

### A.4 跑 post-LLM deterministic

```bash
python3 _meta/scripts/rebuild_l2.py deterministic --scope post-llm
```

链:`crystallize_theme.py --all`(9 主题刷新 _input.json + timeline + regional-coverage)→ `build_regions.py` → `build_global_index.py` → `build_reverse_links.py`

### A.5 验证 + commit

```bash
git status --short | head -20
# 应看到:0_raw/policies/<新加的>.md(新增)、_meta/business_view/<新加的>.yaml(新增)、
#   1_extracted/relations/*.jsonl(增量)、2_crystallized/(刷新)、_index_by_policy/(同步)
git add ... && git commit -m "..."
```

**特例 — body 重抓**(如 14 PDF 乱码案):多一个前置步骤,见 `references/body-refetch-pattern.md`。核心:`0_raw/_archive/policies/` 备份 + `provenance.body_refetched_at` audit 字段。

---

## 3. Trigger B: commentary_change(评论 frontmatter 改)

完整 5 步(双 LLM 阶段):

### B.1 准备阶段(stance)

```bash
# 全量重抽 191 linked
python3 _meta/scripts/rebuild_l2.py prepare --trigger commentary_change --all-commentaries

# 或只重抽指定评论
python3 _meta/scripts/rebuild_l2.py prepare --trigger commentary_change --commentaries X.md,Y.md
```

stage 4 batches `_l2_rebuild_state/stance/batch_{1..4}.jsonl` + `prompt.md`。

### B.2 派 4 个 subagent(stance,可并行)

读 `_l2_rebuild_state/stance/prompt.md`,派 4 subagent 各跑 1 batch,results 写 `_l2_rebuild_state/stance/results/batch_{1..4}.jsonl`。

### B.3 apply --stage stance(自动级联)

```bash
python3 _meta/scripts/rebuild_l2.py apply --stage stance
```

内部:
- 备份现有 stance_batches → `_pre_rebuild_l2_backup/`
- 4 batch 合并 → 5 等份切回 `agent_{1..5}_stances.jsonl`
- 跑 `aggregate_opinions.py` → `1_extracted/opinions/<pid>.md` 重写
- 清理 stale opinion .md(>60s 未更新)
- 跑 `crystallize_theme.py --all` 刷新 9 主题 _input.json(opinion_pids 新值)
- **自动 stage opinions-summary 第 2 LLM 阶段** → `_l2_rebuild_state/opinions_summary/spec_{1..3}.json`

### B.4 派 3 个 subagent(opinions-summary,可并行)

读 `_l2_rebuild_state/opinions_summary/prompt.md`,派 3 subagent 各 1 spec(每 spec 含 3 主题)。subagent **直接 Write 到 vault 路径** `2_crystallized/themes/<theme_dir_name>/opinions-summary.md`(2_crystallized 是 L3 派生层,允许写)。

### B.5 apply --stage opinions-summary

```bash
python3 _meta/scripts/rebuild_l2.py apply --stage opinions-summary
```

校验 9 个 opinions-summary.md 都 fresh + 跑 `build_reverse_links.py` 同步。

---

## 4. Trigger C: 关系层手动加 / dedup(无 LLM)

不需要 prepare/apply,直接 deterministic:

```bash
# 加边到 jsonl 后(如手动加 supersedes)
python3 _meta/scripts/rebuild_l2.py deterministic --scope post-llm
```

或全量:

```bash
python3 _meta/scripts/rebuild_l2.py deterministic --scope all
# = references + entities + 9 主题 crystallize + regions + global_index + reverse_links
```

---

## 5. LLM Wiki 5 原则速查(每次操作前自查)

| # | 原则 | 操作时检查 |
|---|---|---|
| 1 | **Raw immutable** | 你在写 `0_raw/`?除非是「重抓重入」例外(见 §6),否则停手。如果是写 frontmatter 字段,确认是否在白名单(`related_policy / related_policy_source / not_policy_related / commentary_type`)— 不在白名单就违规 |
| 2 | **派生分层** | L2 通用层 (`1_extracted/`) vs L2 业务私有 (`_meta/business_view/`) — scores / 影响分析 / 行动建议属业务私有,绝不写 raw frontmatter |
| 3 | **Append-only** | 派生发现错了,改派生抽取脚本 + 重跑;**绝不**回灌修改 raw |
| 4 | **可追溯** | 派生文件必须含 `extracted_at` + `extracted_by` + `extracted_model`(本 skill 模板已加) |
| 5 | **可重现** | LLM 任务记 prompt + 模型版本(本 skill 用 `claude-opus-4-7`,prompt 在 prompt.md 留痕) |

**白名单字段**(允许写 raw frontmatter,见 CLAUDE.md §2 例外):
- 政策的 `related: [...]`(L2 关系层结果回填)
- 评论的 `related_policy / related_policy_source / not_policy_related / commentary_type`
- raw 抓取错误的轻量字段修正(如 date 字段错)+ 加 audit 字段

不在白名单的 LLM 生成字段(摘要 / scores / 影响分析 / 价值标签 / 一句话精髓)→ **必须**写派生层。

---

## 6. 「重抓重入」例外协议(body PDF 乱码 case)

当发现 raw body 是 PDF 二进制 / 抓取失败的乱码:

1. **不改 frontmatter 的 fact 字段**(id/title/official/issuer/date)
2. **备份**原文件到 `0_raw/_archive/policies/{filename}__pre_<reason>_<timestamp>.md`
3. **替换 body**(保留 `# title` + metadata 块 + `## 政策原文` 标题,只替换 `## 政策原文` 之后的内容)
4. **加 frontmatter audit 字段**(在 `provenance` 下)
   ```yaml
   provenance:
     # ...原字段保留
     body_refetched_at: '<now ISO>'
     body_refetched_method: pdfplumber|textutil|trafilatura
     body_refetched_from: <下载的 url>
     body_pre_refetch_len: <被替换内容字符数>
   ```
5. 然后走 trigger A 全套(因为 body 变了 → 5C/关系层都要重抽)

详见 `references/body-refetch-pattern.md`。

---

## 7. 加新主题(L2 themes 扩容)

新主题(如 RURAL_REVITALIZATION)只需改 1 处:

```bash
# 1. 编辑 _meta/themes_registry.yaml 加一块
# 2. 编辑 1_extracted/entities/registry.yaml 加 type=[theme] entry(同 id)
# 3. 跑 deterministic post-llm
python3 _meta/scripts/rebuild_l2.py deterministic --scope post-llm
```

`crystallize_theme.py --all` 会自动循环 registry 中全部主题。

---

## 8. 常见漏跑 / 陷阱(本会话踩过的坑)

| 陷阱 | 表现 | 防止 |
|---|---|---|
| 关系层 LLM judge 漏跑 | 新政策 `cites_basis / iterates / extends / clarifies / aligns_with` 全 0 边,在 graph 里几乎是孤岛 | 必须 trigger A.2 派 rel_judge subagent |
| opinions-summary.md 漏跑 | `crystallize_theme.py` 不写它(脚本注释明说),frontmatter `last_updated` 没刷新 | 必须 trigger B.4 派 opinions-summary subagent |
| L3 工具链读 raw 旧字段 | `timeline.md "重要性≥4 = 0"` — 因 L1.2 把「重要性」迁到 business_view yaml,但脚本还读 raw fm | 已修复(crystallize/global/regions 改读 yaml),但若新写 L3 脚本注意同样 pattern |
| stance source domain 缺失 | LLM 输出 `source: "?"`,共识门槛 ≥3 distinct domain 命中率低 | 在 stance prompt 强制提取 source domain(已加进 prompt.md) |
| stance batches 与 commentary 集合不对齐 | filter 时大量 drop_unknown(comment_filename 找不到对应 vault 文件) | 重抓而不是 filter;或确认 stance batches 与当前 commentary 同源 |
| 14 PDF 重抓时 P_2024_TJ_01010970 title-body 错配 | URL 指向其他文件,内容与 title 不符 | 重抓后 LLM 应 flag,人工 audit |

---

## 9. 不要做的事

- ❌ 用 `git add .` 或 `git add -A`(可能纳入 macOS cruft / 临时文件;用具体路径)
- ❌ 修改 raw frontmatter 非白名单字段(违 LLM Wiki §1)
- ❌ 跳过 prepare 直接跑 apply(staging 数据缺失)
- ❌ 派 subagent 时写 vault 内任何路径**除了** `2_crystallized/`(opinions-summary 例外)
- ❌ 删 `_l2_rebuild_state/_pre_*_backup/`(回滚保险)
- ❌ 在用户没明说时 commit(CLAUDE.md "提交节奏:用户明确要求才 commit")
- ❌ 用 console API key 模式(`derive_business_view.py` 直接跑)— 用户是 Max 订阅无 API key,必须走 subagent

---

## 10. 速查 — 命令 cheatsheet

```bash
# 入口
python3 _meta/scripts/rebuild_l2.py --help

# trigger A (新政策 / body 重抓)
python3 _meta/scripts/rebuild_l2.py prepare --trigger pid_change --pids P_xxx,P_yyy
# (派 2 subagent: 5c, rel_judge)
python3 _meta/scripts/rebuild_l2.py apply --stage 5c
python3 _meta/scripts/rebuild_l2.py apply --stage rel
python3 _meta/scripts/rebuild_l2.py deterministic --scope post-llm

# trigger B (评论变)
python3 _meta/scripts/rebuild_l2.py prepare --trigger commentary_change --all-commentaries
# (派 4 subagent: stance batch_{1..4})
python3 _meta/scripts/rebuild_l2.py apply --stage stance
# (派 3 subagent: opinions-summary spec_{1..3})
python3 _meta/scripts/rebuild_l2.py apply --stage opinions-summary

# trigger C/D (deterministic only)
python3 _meta/scripts/rebuild_l2.py deterministic --scope all
python3 _meta/scripts/rebuild_l2.py deterministic --scope post-llm
python3 _meta/scripts/rebuild_l2.py deterministic --scope themes

# 单主题(本 skill 一般不用,registry --all 更省事)
python3 _meta/scripts/crystallize_theme.py --theme power_market --aliases "电力市场,电力交易" --theme_zh "电力市场"

# 查看现状(在做任何决策前)
git log --oneline -5
git status --short | awk '{print $2}' | sed 's|/.*||' | sort | uniq -c
ls -la _l2_rebuild_state/ 2>/dev/null  # 看是否有未完成的 staging
```

---

## 11. 决策树(快速归类)

```
用户提到此 vault 改动
    │
    ├─ 改了 0_raw/policies/?  ─── YES ──→ trigger A (pid_change)
    │
    ├─ 改了 0_raw/commentaries/ frontmatter? ─── YES ──→ trigger B (commentary_change)
    │
    ├─ 手动加 supersedes / 关系边 / dedup? ─── YES ──→ trigger C (deterministic post-llm)
    │
    ├─ 提到 stale (opinions / themes / 反链 / 主题)? ──→ 看哪一层 stale
    │   ├─ opinions / opinions-summary stale ──→ trigger B
    │   ├─ themes timeline / regional 所有都旧 ──→ trigger D 全跑
    │   └─ 仅反链页 stale ──→ build_reverse_links.py 单跑
    │
    ├─ 想全量校验? ──→ trigger D (deterministic --scope all)
    │
    └─ 不确定? → 默认 trigger D 跑 deterministic --scope all 兜底
                  (deterministic 是幂等的,跑多次无害)
```

---

## 参考资料

- `references/subagent-prompts.md` — 各 subagent prompt 模板细节(rebuild_l2.py 自动 stage,但要改 prompt 看这里)
- `references/body-refetch-pattern.md` — PDF 乱码重抓详细协议(本会话 14 篇案例)
- `references/llm-wiki-rules.md` — LLM Wiki 5 原则 + 白名单字段全清单(摘自项目 CLAUDE.md §2)
- vault 内 `CLAUDE.md` — 项目级权威规则(本 skill 是它的执行手册)
- vault 内 `_meta/schema_v3.md` — 9 类关系 + jsonl schema 权威规范

如本 skill 与 CLAUDE.md 冲突,**以 CLAUDE.md 为准**。
