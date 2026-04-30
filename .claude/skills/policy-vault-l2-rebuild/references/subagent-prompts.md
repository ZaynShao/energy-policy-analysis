# Subagent Prompt 模板细节

`rebuild_l2.py prepare` 自动 stage 的 prompt 都在 `_l2_rebuild_state/<stage>/prompt.md`,本文档解释 prompt 设计思路 + 改动指南。

## 4 个 LLM 任务一览

| 任务 | 触发 trigger | 模型 | 并行度 | 单任务 token 估 |
|---|---|---|---|---|
| 5C 派生 | A | opus 4.7 | 1 subagent / 不切批 | 50K-150K(取决于 pid 数 + raw 长度) |
| 关系 LLM judge | A | opus 4.7 | 1 subagent / 不切批 | 30K-80K |
| stance 重抽 | B | opus 4.7 | **4 subagent 并行**(48 commentary/批) | 100K-200K/agent |
| opinions-summary 重生成 | B | opus 4.7 | **3 subagent 并行**(3 主题/批) | 70K-130K/agent |

## 5C 派生 prompt 设计要点

输入:每行 1 个 pid + 完整 raw_md(截 14000 字)。
输出:每行 1 个完整 5C JSON(summary / scores / 影响分析 / 行动建议 / national_source)。

关键决策规则(prompt 已含):
- D1≥3 才填 影响分析 / 行动建议;否则 null/[]
- 国家级文件 `is_national_level_originated=true` → primary_source.title=本政策标题,linkage_type=null
- 省/市级文件 → primary_source 是上层国家文件,linkage_type ∈ {直接落地, 借鉴框架, 主题对应}
- 多上层 → secondary_sources

如要调 prompt:改 `_meta/scripts/rebuild_l2.py` 的 `_5c_prompt_template()`(原始 prompt 在 `_meta/scripts/derive_business_view.py` 的 PROMPT 常量,可参考)。

## 关系 LLM judge prompt 设计要点

输入:每行 1 target pid 完整 raw_md + 共享 vault_index.jsonl(271 候选)。
输出:每行 1 条新关系边({from, to, rel, evidence, confidence, ...})。

只抽 5 类:
- `cites_basis`(引用为依据)— "根据/依据/按照《XXX》"
- `iterates`(迭代)— 同主题升级版
- `extends`(扩展)— 范围扩到新领域
- `clarifies`(细化)— 解读 / 操作指引 / 答记者问
- `aligns_with`(对齐)— 同向部署但无明引

不抽:
- `references`(extract_relations_regex 已抽)
- `supersedes`(单独判,需 from.date > to.date)
- `derives_from`(5C 派生覆盖)

confidence 门槛:>=0.7 才输出。

## stance 重抽 prompt 设计要点

输入(per commentary):
- comment_filename / comment_type / source_account / source_domain / date
- related_policy_pids(多个 — 一对多展开)
- policies_context(每 pid 的 title/official/date)
- body_excerpt(前 5000 字)

输出:每个 (commentary, target_policy) pair 1 行 — 即输出行数 ≥ 输入行数。

单个 pair 含 0-3 个 stance:
- `reposted_original` 类 stances=[]
- `news_report` 0-1 中性 stance
- `commentary` 1-3 stance

aspect 抽具体议题(商业模式/试点范围/价格机制/电池质保/补贴细则),不能空泛(避免"政策本身"这类无意义)。

evidence 必须 body 真实片段(≤120 字),可截断不可改写。

source 取 source_domain;若为空写 "?"(后续 P5c 共识聚合会过滤)。

**已知改进点**:source domain 提取率低(很多评论 source_url 为空)。如要改进,在 prompt 中要求 LLM 从 body 提取作者机构 / 出处线索作为补充 source(如"国家能源局答复" → source 可记 "www.nea.gov.cn")。

## opinions-summary 重生成 prompt 设计要点

输入(per theme,3 主题/spec):
- theme_id / theme_dir_name / theme_zh / aliases
- total_policies / opinion_policy_count
- opinion_pids 列表
- **opinions_md**: {pid: 完整 opinion .md 内容(含 stances + source)}
- uncovered_pids(最多 20)+ uncovered_total
- policies_brief: title lookup

任务:5 段聚合写到 `2_crystallized/themes/<theme_dir_name>/opinions-summary.md`(直接 Write 到 vault):
- §1 共识:aspect 同向归并,**≥3 distinct domain** 同 polarity
- §2 分歧:同 aspect ≥2 不同 polarity 不同 source → 表格
- §3 中性观察:polarity=neutral 独立条目
- §4 待跟进:claim 含 ?/待/未明
- §5 未覆盖政策清单:`[[P_xxx]] - title`(从 policies_brief 查)

**严格门槛副作用**:本会话 9 主题中 4 主题 0 共识(VPP/储能/绿电/+1)— 因 source 多 `?` 或同 domain。这是真实信号 — 评论 source 多样性不够。改进方向:扩 RSS 订阅源 / 提升 source domain 提取率。

frontmatter 必填:
```yaml
title: <theme_zh> 业界观点
theme_id: <theme_id>
opinion_coverage: "<X>/<Y> (<Z>%)"
last_updated: <ISO timestamp>
```

## prompt 改动后的回归

改任意 prompt 后,跑 trigger 全套验证:
1. `python3 rebuild_l2.py prepare --trigger pid_change --pids <test_pid>`
2. 派 1 subagent,看 results 质量
3. 不行就回滚,行就 commit

## subagent 调用建议

主 session 用 Agent tool:
- `subagent_type: general-purpose`(全工具访问 — Read/Write/Bash 都需要)
- `model: opus`
- `run_in_background: true`(并行可同时 4-9 个)
- prompt 直接 copy `_l2_rebuild_state/<stage>/prompt.md` 完整内容

注意:subagent 沙箱 cwd 与主 session 一致(`_l2_rebuild_state/` 在 cwd 下,可读可写)。**严禁** subagent 写 vault 任何路径(除 opinions-summary 任务允许写 `2_crystallized/themes/<X>/opinions-summary.md`)。
