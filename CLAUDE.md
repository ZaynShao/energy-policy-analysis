# 政策分析 Vault · CLAUDE.md

## 这是什么仓

这个仓库是**政策分析项目的"数据层"**——政策 raw、评论 raw、派生产物、canonical 配置、工作日志全在这里。

**工程层**(脚本 / SOP / 中间产物 / 工程文档)在另一个仓:`~/dev/政策分析-pipeline/`。

两仓通过 [SCHEMA.md](SCHEMA.md)(数据契约)解耦。

```
~/Documents/Zayn Main/政策分析/   ← 本仓(vault,数据 + SCHEMA 副本)
~/dev/政策分析-pipeline/           ← 工程仓(脚本 + SOP + 状态)
~/政策分析-legacy-archive/         ← 已废弃的旧脚本/产物(物理隔离,本仓不读)
```

---

## 在本仓内 AI 应该做什么

- **可以读**:任何数据文件(`0_raw/` / `1_extracted/` / `2_crystallized/` / `_meta/business_view/` / `00 背景资料/` / `开发日记/`)
- **可以读**:[SCHEMA.md](SCHEMA.md) 了解数据契约
- **可以做**:在 `开发日记/` 写日志、在 `00 背景资料/` 维护数据/配置类文档、在 `2_crystallized/` 做人工 polish

## 在本仓内 AI 应该不做什么

- **不要写脚本**:任何 Python / Node 脚本应该写到 `~/dev/政策分析-pipeline/scripts/`,不写 vault
- **不要建工程目录**:audit / staging / tmp / candidates 这类工程中间产物全部进 pipeline `state/`
- **不要修改 raw**:`0_raw/policies/` 与 `0_raw/commentaries/` 入库后 immutable(详见 SCHEMA §0 + §C 白名单边界)
- **不要在 raw frontmatter 加非白名单字段**:LLM 派生字段一律走派生层
- **不要参考** `~/政策分析-legacy-archive/`:已废弃的旧脚本和产物,物理隔离,**禁止读取**

如果用户在本仓内要求做工程类工作,引导切到 pipeline 仓:

```
cd ~/dev/政策分析-pipeline
```

---

## 数据原则(必读)

### Raw immutable

`0_raw/` 一旦入库,任何后续流程禁止修改其内容(frontmatter 业务字段 + body)。
唯一例外:重抓重入 → 旧版迁 `_archive/`,新版用 `_v2` 后缀,**不就地覆盖**。

边界例外白名单(允许 pipeline 后置回填到 raw frontmatter):
- 评论的 `related_policy` / `related_policy_source` / `not_policy_related` / `commentary_type`
- 详见 SCHEMA §C

### 派生分层

任何对 raw 的解读、评分、关系判断、LLM 生成内容,统一落派生层:
- `1_extracted/` — 通用派生(公开)
- `_meta/business_view/` — 业务私有派生
- `2_crystallized/` — 结晶层

详见 SCHEMA §1。

### 可追溯 + 可重现

每个派生产物指回 raw 源(`pid` / `policy_id` / `sanitized_from`),LLM 调用记录 prompt + temperature + 模型版本。

---

## 目录速览

```
0_raw/                  L1 raw 层(不可改)
  policies/             1020 篇政策原文
  commentaries/         评论原文
  _archive/             归档 raw(版本替换)
  _duplicates/          dup 隔离

1_extracted/            L2 派生层(可重抽)
  policy_summaries.jsonl 政策客观摘要
  relations/            9 类关系 jsonl + 反链页
  entities/             实体抽取产物
  opinions/             评论观点抽取
  commentary_audit/     评论审计

2_crystallized/         L3 结晶层(主题/区域聚合页)
  themes/
  regions/
  _global_index.md
  _reports/

3_lints/                L2 lint 报告

_meta/
  business_view/        业务侧派生(评分 / 影响分析 / 行动建议)
  themes_registry.yaml  主题 canonical 词表
  business_tags_legacy.jsonl  legacy 业务标签(等 canonical 化退役)
  issuer_review_queue.yaml    机构 canonical 评审队列
  backlog/                    数据状态 backlog

00 背景资料/             业务背景 / 渠道目录 / 评分体系(数据/配置类文档)
SCHEMA.md               数据契约(与 pipeline 仓同步)
开发日记/                按日期组织的人工工作日志
```

---

## 用户偏好

- **语言**:中文为主,技术词英文
- **风格**:直接,不堆废话;有不一致先指出再做
- **方向问题**:列大框架 todo 再行动
- **提交节奏**:用户明确要求才 commit,小步、可回滚

---

## 项目特定外部约束

- **位置**:中国大陆,Tavily / Firecrawl / Claude API 走代理
- **vault 文件名**:中文带 `【】`,Obsidian 用 `aliases` 解析 `[[P_xxx]]` 到正确文件
- **git repo 根**:本目录就是 git 根
