# CLAUDE.md · 项目工作准则(政策分析 / 滴滴能源)

> 本文件供 Claude 在本项目工作时自动加载。与 `~/.claude/CLAUDE.md`(全局规则)合并使用,本文件优先级高。

---

## 项目身份

- 滴滴能源政策分析项目,Obsidian vault + git repo
- 服务对象:决策层政策简报(L3 月报 / 主题结晶页 / 政策反链)
- 数据流:八步采集法 → L1 raw → L2 派生 → L3 渲染(详见 [`00 背景资料/策略-八步采集法.md`](00%20背景资料/策略-八步采集法.md))
- 工具栈:Tavily / Firecrawl / trafilatura / Claude / Obsidian

---

## LLM Wiki 设计原则(本项目的核心架构基线)

本项目奉行 **Karpathy LLM Wiki 思路** — raw 是不可变事实层,派生是可变解读层。具体落到 5 条:

### 1. Raw immutable(不可修改原则)

`0_raw/` 一旦入库,**任何后续流程禁止修改其内容**。包括但不限于:
- L2 关系抽取脚本不得回写 raw frontmatter
- L3 月报渲染过程不得编辑 raw body
- 评分/标签/解读迭代不得"就地"改 raw
- 反链/索引重建不得插入 frontmatter 字段
- LLM 总结不得替代 raw 原文

唯一例外:**重抓重入**(如发现 raw 抓取错误)。命名后缀 `_v2` 区分,旧版迁 `_archive/`,不就地覆盖。

### 2. 派生分层(derivation layers)

所有对 raw 的解读、评分、关系、对比、业务判断、**LLM 生成内容(摘要/语义标签/分类)** — 都属派生层,落到独立目录:
- `_meta/business_view/{pid}.yaml` — 业务侧字段:
  - `summary`(2-3 句摘要,LLM 生成)
  - `business_tags`(V2G/储能/充电... 语义分类,LLM 推断)
  - `scores` / `重要性` / `行动分类` / `价值标签`(评分体系)
  - `影响分析`(分业务三段判断)
- `1_extracted/relations/*.jsonl` — 关系层(supersedes/cites_basis/iterates 等)
- `1_extracted/entities/` — 实体抽取
- `2_crystallized/themes/` — 主题结晶
- `_meta/march_report_batches/` 或类似目录 — L3 月报中间产物

派生文件可以无限重抽、覆盖、删除 — 都不影响 raw。

**关键判定**:**任何 LLM 生成或推断的内容都是派生**,即使看起来"很客观"(如摘要)。Step 4.5 只做 deterministic 字面提取(文号/日期/标题/机构);LLM 生成内容统一在 Step 5C 异步派生。

**例外(vault 内部关系网)**:指向 vault 内其他文档的链接型字段,**允许**写到 raw frontmatter,即使生成过程用了 LLM:
- 政策的 `related: [...]`(L2 关系层结果回填)
- 评论的 `related_policy / related_policy_source / not_policy_related`(Step 6.5 反向匹配结果)
- 评论的 `commentary_type: 解读/分析/案例/数据/转发`(类型分类)

**判定标准**:
- 是「指向 vault 已有文档的链接」或「枚举型分类标签」 → vault 关系网,**允许**写 raw frontmatter
- 是「LLM 生成的自由文本」(摘要/影响分析/语义标签) → 派生层,**禁止**写 raw

理由:vault 关系网字段本质是 graph 结构的事实层(A 评论 → 关联到 B 政策),LLM 在这里只是"事实匹配工具",输出是 deterministic 的 link 而非自由生成内容。Obsidian 的反链 / Dataview 查询依赖 frontmatter 读关系链接,把这些字段下沉到派生层会导致 graph 失效。

### 3. Append-only(派生迭代不回灌 raw)

派生错了的修复路径:
1. 改派生抽取脚本
2. 重跑派生层
3. 派生文件被覆盖
4. **raw 完全不动**

错误的修复路径(本项目曾经踩过):
- 派生发现 raw 描述不准 → 直接编辑 raw frontmatter / body
- L3 月报渲染缺字段 → 回头给 raw frontmatter 加字段
- 评分逻辑变了 → 逐篇 raw 改 `重要性` 字段

这些都是把派生层污染倒灌回 raw 层。一旦发生,raw 就不再是单一事实源。

### 4. 可追溯(每个派生指回 raw)

每个派生文件必须能指回 raw 源:
- `_meta/business_view/{pid}.yaml` 的 `sanitized_from` 字段
- `1_extracted/relations/*.jsonl` 的 `pid` / `source_pid` / `target_pid` 字段
- `2_crystallized/themes/*.md` 的 `cites:` 段引 `[[<raw 文件>]]`

无法追溯的派生 = 失去 trust 锚点,相当于幻觉。

### 5. 可重现(同 raw + 同规则 → 同派生)

派生抽取必须是确定性流程:
- 抽取脚本 + 输入 raw + 配置 = 同一份输出
- LLM 调用如不可避免随机性,记录 prompt + temperature + 模型版本到 `_meta/scripts/` 旁的 log
- 每个派生文件 frontmatter 标 `extracted_at` + `extracted_by`(脚本路径或脚本+commit-hash)

---

## 目录速览

```
0_raw/                  L1 raw 层(不可改)
  policies/             263 篇政策原文
  commentaries/         1170 篇评论
  _duplicates/          dup 隔离

1_extracted/            L2 派生层(可重抽)
  relations/            7 类关系 jsonl + 反链页
  entities/             实体注册 + 抽取产物
  opinions/             评论观点抽取
  commentary_audit/     评论审计

2_crystallized/         L3 结晶层(主题/区域聚合页)
  themes/               32 主题
  regions/              9 区域

_meta/
  business_view/        业务侧派生(评分/重要性/影响分析)
  scripts/              抽取脚本与一次性工具
  schema_v3.md          数据 schema 文档
  march_report_batches/ L3 月报中间产物

00 背景资料/             SOP / 蓝本 / 渠道目录(读我必读)
docs/handoffs/          session 间交接文档
开发日记/                按日期组织的工作记录
```

---

## 关键禁止事项(违反即停手)

1. **不要回写 raw**:任何脚本写 `0_raw/` 之前先问"我是在重抓还是在编辑?如果是编辑,是否能改去派生层"
2. **不要在 L1 frontmatter 加非白名单字段**:白名单见 [`00 背景资料/策略-八步采集法.md`](00%20背景资料/策略-八步采集法.md) Step 5A
3. **不要把 L3 渲染需要的字段反加到 L1**:L3 缺字段 → 改 L3 渲染脚本去查 `_meta/business_view/`,而不是给 L1 加
4. **不要在评分/打分迭代时改 L1 frontmatter `重要性`**:评分变化只更新 `_meta/business_view/{pid}.yaml`
5. **不要混用月报命名**:输出目录不要硬编码 `march_report_batches/`,应 `{month}_report_batches/` 或 month-agnostic 命名

---

## 用户偏好

- **语言**:中文为主,技术词英文
- **风格**:CLAUDE.md(全局)的 Think Before Coding / Simplicity First / Surgical Changes / Goal-Driven Execution 全适用
- **方向问题列大框架 todo**:A/B/C 选项前先列全局 TODO,标出推进/解锁/不触哪几条
- **开发日记格式**:`开发日记/<YYYY-MM-DD>/日志.md`
- **提交节奏**:用户明确要求才 commit,小步、可回滚

---

## 项目特定外部约束

- **位置**:中国大陆,Tavily / Firecrawl / Claude API 走代理
- **vault 文件名**:中文带 `【】`,**Obsidian 用 `aliases` 解析 `[[P_xxx]]` 到正确文件**(263 政策已加 aliases)
- **subagent 沙箱**:不能直接读 vault,不能写 /tmp/。让 subagent 把 JSONL 输出在 final_report markdown code block 里,主 session 提取保存
- **git repo 根**在 `政策分析/` 子目录,不在 vault 根。`.obsidian/app.json` 不在 git 里
