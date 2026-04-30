# LLM Wiki 5 原则 + 白名单字段全清单

摘自项目级 `CLAUDE.md` §1-§2(本 skill 的根本约束,任何冲突以 CLAUDE.md 为准)。

## 5 原则速查

### §1 Raw immutable(不可修改原则)

`0_raw/` 一旦入库,任何后续流程禁止修改其内容。包括但不限于:
- L2 关系抽取脚本不得回写 raw frontmatter
- L3 月报渲染过程不得编辑 raw body
- 评分/标签/解读迭代不得"就地"改 raw
- 反链/索引重建不得插入 frontmatter 字段
- LLM 总结不得替代 raw 原文

**唯一例外:重抓重入**(如发现 raw 抓取错误)。命名后缀 `_v2` 区分,旧版迁 `_archive/`,不就地覆盖。

→ 实操见本 skill SKILL.md §6「重抓重入」例外协议

### §2 派生分层(derivation layers)

所有对 raw 的解读、评分、关系、对比、业务判断、**LLM 生成内容(摘要/语义标签/分类)** — 都属派生层,split 到对应位置:

**L2 通用层**(公开,`1_extracted/`):
- `policy_summaries.jsonl` — 政策客观描述(LLM 生成但中性)
- `relations/*.jsonl` — 9 类关系
- `entities/` — 实体抽取
- `2_crystallized/themes/` — 主题结晶(本质是 L3,但与 L2 entities 同根)

**L2 业务私有层**(`_meta/business_view/`,可加 .gitignore):
- `_meta/business_view/{pid}.yaml` — 公司视角判断:
  - `scores` / `重要性` / `行动分类` / `价值标签`
  - `影响分析`(分业务四段:加油/充电/电力_储能_V2G_交易/乡村)
  - `行动建议`(A 立即 / B 研究 / C 关注)
  - `didi_impact_one_liner`(可选)

**关键判定**:**任何 LLM 生成或推断的内容都是派生**,即使看起来"很客观"(如摘要)。

### §3 Append-only(派生迭代不回灌 raw)

派生错了的修复路径:
1. 改派生抽取脚本
2. 重跑派生层
3. 派生文件被覆盖
4. **raw 完全不动**

错误的修复路径(本项目曾经踩过):
- 派生发现 raw 描述不准 → 直接编辑 raw frontmatter / body
- L3 月报渲染缺字段 → 回头给 raw frontmatter 加字段
- 评分逻辑变了 → 逐篇 raw 改「重要性」字段

### §4 可追溯(每个派生指回 raw)

每个派生文件必须能指回 raw 源:
- `_meta/business_view/{pid}.yaml` 的 `sanitized_from` / `extracted_by` 字段
- `1_extracted/relations/*.jsonl` 的 `from` / `to` 字段
- `2_crystallized/themes/*.md` 的 `cites:` 段引 `[[<raw 文件>]]`

### §5 可重现(同 raw + 同规则 → 同派生)

- 抽取脚本 + 输入 raw + 配置 = 同一份输出
- LLM 调用如不可避免随机性,记录 prompt + temperature + 模型版本到 `_meta/scripts/` 旁的 log
- 每个派生文件 frontmatter 标 `extracted_at` + `extracted_by` + `extracted_model`

---

## 白名单字段:**允许写 raw frontmatter 的例外**

> CLAUDE.md §2 例外条款:指向 vault 内其他文档的链接型字段,**允许**写到 raw frontmatter,即使生成过程用了 LLM。

### 政策 raw frontmatter 白名单

| 字段 | 类型 | 来源 | 备注 |
|---|---|---|---|
| `id` / `aliases` | str / list | 入库时定 | pid 命名约定见 vault 历史 |
| `title` | str | raw 原文 | 不可改(除 typo 修正) |
| `official_number` | str | raw 原文 | 同上 |
| `issuer` / `issuer_canonical` | list | raw + 实体规范化 | 入库时定 |
| `date` | str | raw 落款 | 抓错可重抓修正(走「重抓重入」例外)|
| `region` | dict | raw 推断 | 入库时定 |
| `provenance` | dict | 采集元信息 | 含 `body_refetched_*` audit 字段(重抓时加)|
| `dup_aliases` / `dedup_at` / `dedup_rule` | dedup 元 | dedup 流程写 | 是 vault 关系网字段 |
| `related: [P_xxx, ...]` | list | L2 关系层结果回填 | **白名单** ← LLM 可写 |

### 评论 raw frontmatter 白名单

| 字段 | 类型 | 来源 | 备注 |
|---|---|---|---|
| `title` / `source_account` / `source_url` / `date_published` | 抓取时定 | RSS / Web | 不改 |
| `commentary_type: 解读/分析/案例/数据/转发` | str | LLM 分类 | **白名单** |
| `business_tag` | str | 抓取时定 | 不改 |
| `source: wewe-rss` 等 | str | 抓取时定 | 不改 |
| `related_policy: [P_xxx, ...]` | list | LLM 匹配/重判 | **白名单** ← P3/P4 模式写 |
| `related_policy_source` | str | LLM 来源标记(B1/B2/B3/B4) | **白名单** |
| `related_policy_confidence` | float | LLM | **白名单** |
| `related_policy_matched_at` | str | timestamp | **白名单** |
| `not_policy_related: true` | bool | LLM 判断或人工 | **白名单** |

### 不在白名单 → 必写派生层

任何 LLM 生成的"自由文本"或"业务判断" — 必写派生层(`_meta/business_view/<pid>.yaml` 或 `1_extracted/`):
- 摘要 / summary_one_liner / reading_value
- scores(D1-D6)/ 重要性 / 行动分类 / 价值标签
- 影响分析(分业务段)
- 行动建议(A/B/C)
- didi_impact_one_liner

如发现这些字段写在 raw → **是污染**,需走类似 L1.2 的净化(本项目历史教训)。

---

## 判定流程图

```
要写 0_raw/?
    │
    ├─ 是「重抓重入」(整篇 raw 重抓 / body 修复 / fact 字段轻量错改)?
    │    └─ YES → 走 SKILL.md §6 重抓协议(备份 + audit 字段)
    │
    ├─ 是 vault 关系网链接型字段(related / related_policy / commentary_type)?
    │    └─ YES → 允许写白名单字段
    │
    ├─ 是 dedup 元(dup_aliases / dedup_at)?
    │    └─ YES → 允许(dedup 流程白名单)
    │
    └─ 都不是 → ❌ 违 §1,改去派生层
```

---

## 历史踩坑

| 时间 | 错误 | 修复路径 | 教训 |
|---|---|---|---|
| L1.1 之前 | 八步采集法 SOP 把「影响分析」「scores」「重要性」直接写 raw frontmatter | L1.1 改 SOP + L1.2 净化 247 篇 + 移到 business_view yaml | 从 SOP 层杜绝违规 |
| L1.2 后 | crystallize_theme.py / global_index / regions 还读 raw 「重要性」 | 改读 business_view yaml + fallback raw | L1 字段迁移要全库 audit 下游脚本 |
| 不详 | 14 篇 PDF body 是二进制乱码,5C 派生基于 garbage | PDF 重抓协议(本会话 2026-04-30) | 抓取 source_type=A 但 body 不可读 → 入库前要校验 |
| 不详 | stance_batches 与 vault commentary 集合错位(171/248 unknown) | P5b 重抽全部 | LLM 派生 ↔ raw 对齐要 audit |
