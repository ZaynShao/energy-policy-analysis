---
title: Phase 1 启动包(信息源根治)
date: 2026-05-06
purpose: vault 全量积累 + 不再漏抓 — 一次性补漏 + 持续机制建设
constraints:
  - 5h limit:大量 API 调用 14:47 后再开
  - 不动 0_raw 直到本批所有 raw 准备好
  - 不动 _l2_rebuild_state 除自己创建的(已备份在 _l2_rebuild_state_backup_2026-05-06_14-00/)
---

# Phase 1 启动包

## 现状(轻量准备完成)

| 准备工件 | 路径 | 用途 |
|---|---|---|
| 13 主题清单 + aliases | `_meta/audit_2026-05-06/themes_13.yaml` | Tavily query 输入 |
| 重点地市清单(~80 市) | `_meta/audit_2026-05-06/target_cities.yaml` | 矩阵第二维 |
| 本地覆盖度 baseline | `_meta/audit_2026-05-06/coverage_baseline.md` | 漏抓 cell 清单 |
| Tavily 矩阵 query 计划 | `_meta/audit_2026-05-06/tavily_queries.jsonl` | 411 query |
| 候选渠道晋升任务 | `_meta/audit_2026-05-06/candidate_promotion_tasks.jsonl` | 156 任务 |
| 文号序列审计 | `_meta/audit_2026-05-06/official_number_audit.md` | 缺号 → site:filter |
| **引用反扫缺口** | `_meta/audit_2026-05-06/citation_gaps.json` | **314 篇高价值补抓清单** |

## 关键 baseline 数据

```
vault 现状:
  - 273 篇 raw policies / 1170+ commentaries
  - 13 × 31 矩阵覆盖率: 28% (113/403 cells 非零)
  - 漏抓 cells: 290
  - vault 内部引用未收: 314 个文号

漏抓重点省(P0 主题零省):
  - 江苏: 仅 2 篇 raw
  - 浙江: 仅 1 篇
  - 广东: 3 篇
  - 山东: 3 篇
  - 河北/河南/安徽/湖北: 0-2 篇
```

## 47min 后启动序列

### Stage A: Tavily 矩阵 baseline (预估 15-20 min, 411 API calls)

```bash
cd /Users/shaoziyuan/Documents/Zayn\ Main/政策分析
# 接 Tavily API 跑 411 query,写结果 JSONL
python3 _meta/audit_2026-05-06/run_tavily_matrix.py \
  --queries _meta/audit_2026-05-06/tavily_queries.jsonl \
  --output _meta/audit_2026-05-06/tavily_results.jsonl \
  --concurrency 5
```
> ⚠ run_tavily_matrix.py 还没写,Stage A 启动前 5 分钟先写它(模板可参考
> `_meta/scripts/refetch_low_quality.py` 里 Tavily 调用)

### Stage B: 候选渠道晋升验证 (预估 5-8 min, 156 API calls)

```bash
python3 _meta/audit_2026-05-06/run_candidate_promotion.py \
  --tasks _meta/audit_2026-05-06/candidate_promotion_tasks.jsonl \
  --output _meta/audit_2026-05-06/promotion_results.jsonl
```

### Stage C: 引用缺口检索 (预估 8-12 min, 314 API calls)

```bash
# 对 citation_gaps.json TOP 100 高频文号跑 Tavily
python3 _meta/audit_2026-05-06/run_citation_backfill.py \
  --gaps _meta/audit_2026-05-06/citation_gaps.json \
  --top 100 \
  --output _meta/audit_2026-05-06/citation_results.jsonl
```

### Stage D: 缺口聚合 + 去重 (本地, 2 min)

```bash
# 三路结果合并 → 候选 URL 池 → 与 vault 已收去重(by official_number / title hash)
python3 _meta/audit_2026-05-06/aggregate_candidates.py \
  --tavily _meta/audit_2026-05-06/tavily_results.jsonl \
  --promotion _meta/audit_2026-05-06/promotion_results.jsonl \
  --citation _meta/audit_2026-05-06/citation_results.jsonl \
  --output _meta/audit_2026-05-06/candidates_to_fetch.jsonl
```

### Stage E: Firecrawl/trafilatura 抓正文 (预估 30-60 min, 200-600 抓取)

```bash
# 走八步采集法 Step 4 链路: Firecrawl 首选,trafilatura 兜底
python3 _meta/scripts/step4_batch_fetch.py \
  --candidates _meta/audit_2026-05-06/candidates_to_fetch.jsonl \
  --output 0_raw/policies_staging/ \
  --concurrency 3
```
> ⚠ 抓取后落 staging,不直接进 0_raw/policies/。等下一步 dedup + scoring 通过才正式入库。

### Stage F: dedup + step4.5 deterministic 抽取 + scoring (10-15 min)

```bash
# 走八步采集法 Step 5: dedup + 结构化抽取 + 综合分
python3 _meta/scripts/step5_ingest_pipeline.py \
  --staging 0_raw/policies_staging/ \
  --baseline _meta/audit_2026-05-06/dedup_baseline.jsonl \
  --threshold 1
```
> 阈值 1 = 全入库(高分进 ingested,低分进 ingested-low-score)

### Stage G: trigger A → 5C/rel_judge subagent (派,等)

```bash
# 收集本批所有新 pid,prepare trigger A
NEW_PIDS=$(ls 0_raw/policies/ --newer-than "1h" | extract pid)  # 占位
python3 _meta/scripts/rebuild_l2.py prepare \
  --trigger pid_change \
  --pids "$NEW_PIDS"
```

派 2 个 subagent(5c + rel_judge,可并行后台):
- 读 `_l2_rebuild_state/5c/prompt.md` → write to `_l2_rebuild_state/5c/results/results.jsonl`
- 读 `_l2_rebuild_state/rel_judge/prompt.md` → write to `_l2_rebuild_state/rel_judge/results/results.jsonl`

```bash
python3 _meta/scripts/rebuild_l2.py apply --stage 5c
python3 _meta/scripts/rebuild_l2.py apply --stage rel
python3 _meta/scripts/rebuild_l2.py deterministic --scope post-llm
```

### Stage H: 验证 + commit

```bash
# 验证矩阵
python3 _meta/audit_2026-05-06/local_coverage_baseline.py
# 比较 before/after,看覆盖率从 28% 升到多少
```

## 时间预算

| Stage | 时长 | 累计 |
|---|---|---|
| 14:47 现在 | — | 0:00 |
| A. Tavily 矩阵 | 15-20 min | 0:20 |
| B. 候选晋升 | 5-8 min | 0:28 |
| C. 引用补抓 | 8-12 min | 0:40 |
| D. 聚合去重 | 2 min | 0:42 |
| E. Firecrawl 批抓 | 30-60 min | 1:42 |
| F. dedup + 5A | 10-15 min | 1:57 |
| G. trigger A subagent | 25-40 min | 2:37 |
| H. 验证 commit | 5 min | 2:42 |

**总耗时预估 2.5-3h,在 5h limit 内有 buffer。**

## 风险点 + 应对

1. **Tavily 限流** — 并发 5 应该 OK,如限流降到 2
2. **Firecrawl 额度耗尽** — 兜底 trafilatura(SOP 有 plan B)
3. **subagent crash** — 沿用 SKILL.md §A.2 协议,失败重派
4. **新主题(4 个)entities 未注册** — Stage E 后,Stage F 前需要更新
   `1_extracted/entities/registry.yaml` + `_meta/themes_registry.yaml` 加 4 主题
5. **大量入库后业务字段需补** — `business_view/` 由 5C subagent 派生,自动覆盖

## 不在本 Phase 范围

- 公众号订阅扩容(C 路 ingest)— 涉及 wewe-rss 配置,放 Phase 2
- 垂直数据库爬取(E 路 ingest:北极星/能源国资委)— 放 Phase 2
- audit 脚本接 cron — 放 Phase 2
- policy-watch skill 升级到主题×省份矩阵节奏 — 放 Phase 2

## Phase 2 简要

Phase 1 完成后,vault 应已从 273 → ~600-800 raw,覆盖率 28% → ~70%。

Phase 2 的目标是**让漏抓机制不再发生**:
1. audit 脚本三件套接 weekly cron(每周日跑覆盖度 + 文号 + 引用反扫,缺口告警)
2. policy-watch skill 升级:daily-scan 走主题×重点省矩阵(~50 query/日)
3. wewe-rss 公众号清单扩容(每省 3-5 本地号)
4. 八步采集法 SOP 升级(Step 2 强制矩阵 + Step 2.5 候选晋升 + Step 8 自动反哺)
