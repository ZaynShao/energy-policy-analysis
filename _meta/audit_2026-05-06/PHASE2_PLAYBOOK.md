---
title: Phase 2 启动包(audit 三件套接 cron + DOCX 抓取)
date: 2026-05-06
purpose: 让漏抓机制不再发生 — 持续运行的 audit + 增量补抓
---

# Phase 2 启动包

Phase 1 已把 vault 从 273 → 603 raw,矩阵覆盖率 28% → 60.5%。
Phase 2 目标:**让漏抓机制不再发生**。3 件事:

## 1. audit 脚本三件套接 weekly cron

3 个本地 audit 脚本(无 API,可立即跑):
- `_meta/audit_2026-05-06/local_coverage_baseline.py` — 13×31 矩阵覆盖度
- `_meta/audit_2026-05-06/audit_official_number_seq.py` — 文号序列缺号扫
- `_meta/audit_2026-05-06/audit_citation_gaps.py` — 引用-收录差扫

写一个 `_meta/scripts/weekly_audit.py` 把三件套串起来,加 macOS launchd 或 cron:

```bash
# 每周日 9:00 跑
0 9 * * 0 cd /Users/shaoziyuan/Documents/Zayn\ Main/政策分析 && \
  python3 _meta/audit_2026-05-06/local_coverage_baseline.py && \
  python3 _meta/audit_2026-05-06/audit_official_number_seq.py && \
  python3 _meta/audit_2026-05-06/audit_citation_gaps.py && \
  python3 _meta/scripts/audit_alert.py  # 发现高优缺口 → 邮件 / 通知
```

**告警阈值**:
- 矩阵覆盖率单周下降 > 5% → 告警
- citation_gap 新增 > 50 → 告警
- 任一 P0 主题(VPP/储能/电力市场/V2G/聚合商/配电网)在任一 P0 省(京沪苏浙粤鲁)零命中 → 告警

## 2. policy-watch skill 升级

现有 policy-watch skill 跑 cron(每日 9:00),但走的是固定 51 query 偏向国家级。
**升级**:替换为主题×重点省矩阵 query(50-100 query/日,基于 audit 矩阵稀疏度动态生成)。

升级路径:
1. 把 `_meta/audit_2026-05-06/gen_tavily_queries.py` 拷到 `_meta/scripts/gen_daily_queries.py`
2. 改 query 选取逻辑:每日只跑覆盖率最低的 50 cells × 1 query 各
3. 接八步采集法 Step 2(替换原 Step 2 query 来源)
4. 保留 Step 8 缺口反哺(自动)

## 3. DOCX 抓取兜底(本次 Phase 1 跳过的 42 个)

42 个 .docx 文件用 mammoth/python-docx 加进 fetcher:

```bash
pip install python-docx mammoth
# 修 fetch_candidates.py 加 docx handler:
#   if url.endswith('.docx') or 'application/msword' in ct:
#       import mammoth
#       result = mammoth.convert_to_markdown(io.BytesIO(resp.content))
#       body = result.value
```

## 4. 渠道目录候选晋升 — 把本次 promotion_results 落档

Stage B 的 156 任务结果还没回写到 `00 背景资料/渠道目录.md`。需要:
- 命中 ≥3 P0 主题政策的域名 → 晋升正式段
- 0 命中域名 → 删候选

```bash
python3 _meta/audit_2026-05-06/apply_promotion_to_channel_dir.py
```
(此脚本 Phase 2 写)

## 5. Phase 1 trigger A 完成后必跑

```bash
# 本次 Phase 1 入库后必须跑(在 Stage G 之后):
python3 _meta/scripts/rebuild_l2.py deterministic --scope post-llm
# = crystallize 9+4=13 主题 + regions + global_index + reverse_links
```

## 6. 数据质量后修

本次 normalize 出来的 330 raw 中:
- **issuer "未知机构"** ~50 篇:URL 域名不在 DOMAIN_REGION 表中(如新闻媒体 in-en.com,bjx.com.cn)
  - 修法: Phase 2 跑一遍 LLM-based issuer 抽取(从 body 头部 1KB),覆盖现有
- **region "未知"** ~40 篇:同上
  - 修法: 同样 LLM 抽取
- **date "1900-01-01"** ~ 10 篇:title/body 都没找到日期
  - 修法: subagent 5C 输出 schema 加 inferred_date 字段

## 时间预估

| 任务 | 工期 |
|---|---|
| weekly_audit.py 写完 + cron 配置 | 1-2 小时 |
| policy-watch skill 升级到矩阵 query | 半天 |
| DOCX 兜底加 fetcher + 跑 42 篇 | 1 小时 |
| 候选渠道晋升回写 | 半天 |
| LLM-based issuer/region/date 修复 | 半天 |

**总计 1-2 个工作日,Phase 2 不阻塞 Phase 1 出效果。**
