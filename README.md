# 政策分析 Vault

能源政策分析项目的**数据层**。政策 raw、评论 raw、派生产物、canonical 配置、工作日志在本仓。

工程层(脚本 / SOP / 中间产物)在另一仓:`~/dev/政策分析-pipeline/`。
两仓通过 [SCHEMA.md](SCHEMA.md)(数据契约)解耦。

```
~/Documents/Zayn Main/政策分析/   ← 本仓(vault)
~/dev/政策分析-pipeline/           ← 工程仓
~/政策分析-legacy-archive/         ← 已废弃的旧脚本/产物(物理隔离)
```

## 在本仓内做什么

- 读数据(`0_raw/` / `1_extracted/` / `2_crystallized/` / `_meta/business_view/`)
- 维护背景资料和 canonical 词表(`00 背景资料/` / `_meta/themes_registry.yaml` / `_meta/issuer_review_queue.yaml`)
- 写人工工作日志(`开发日记/`)
- 在 `2_crystallized/` 做人工 polish

## 不在本仓做什么

- 不写脚本(去 pipeline)
- 不建工程目录(audit / staging / tmp 全部去 pipeline `state/`)
- 不修改 raw 内容(详见 [SCHEMA.md](SCHEMA.md) §0 + §C 白名单)
- 不参考 `~/政策分析-legacy-archive/`(已隔离的废弃产物,**禁止读**)

详细约束见 [CLAUDE.md](CLAUDE.md)。

## 目录速览

```
0_raw/                  L1 raw(不可改)
  policies/             政策原文
  commentaries/         评论原文
  _archive/             归档 raw(版本替换)
  _duplicates/          dup 隔离

1_extracted/            L2 派生(可重抽)
  policy_summaries.jsonl
  relations/            9 类关系 jsonl + 反链页
  entities/
  opinions/
  commentary_audit/

2_crystallized/         L3 结晶(主题/区域聚合)
  themes/
  regions/
  _global_index.md
  _reports/

3_lints/                lint 报告

_meta/
  business_view/        业务派生(评分/影响分析/行动建议)
  themes_registry.yaml  主题 canonical
  business_tags_legacy.jsonl  legacy 暂存
  issuer_review_queue.yaml    机构 canonical 评审
  backlog/

00 背景资料/             业务背景 / 渠道目录 / 评分体系
SCHEMA.md               数据契约(与 pipeline 仓同步)
开发日记/                人工工作日志
```

## 当前规模

数字由 pipeline 仓的 status 脚本生成,见 `~/dev/政策分析-pipeline/state/STATUS.md`。
本 README 不手写"当前数字"以避免过期。

## 当前阶段范围

聚焦 **L1 完整采集 + L2 高质量派生**。
**L3 月报 / 决策卡片不在本阶段范围**——`2_crystallized/_reports/` 既存月报作为历史数据保留,不再更新。

## 架构层

| 层 | 职责 | 落地 | 当前阶段 |
|---|---|---|---|
| L1 raw | 政策/评论原始入库 | `0_raw/` | ✓ 重点(市级覆盖扩展) |
| L2 派生 | 实体/关系/评分/摘要 | `1_extracted/` + `_meta/business_view/` | ✓ 重点(质量审计) |
| L3 结晶 | 主题页/区域页 | `2_crystallized/themes,regions/` | 维持 |
| L3 渲染 | 月报 / 决策卡片 | `2_crystallized/_reports/` | — 暂不维护 |

数据流 + 哲学详见 [SCHEMA.md](SCHEMA.md) §0。
