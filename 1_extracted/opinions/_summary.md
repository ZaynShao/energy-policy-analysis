---
title: Step 8 评论 stance 抽取汇总
date: 2026-04-26
---

# Step 8 · 评论 stance 抽取汇总

- 处理评论: **248**
- 抽出 stance: **334**
- 政策有 ≥1 stance: **54**

## 评论类型分布
- reposted_original: 126 (51%)
- commentary: 78 (31%)
- news_report: 26 (10%)
- unknown: 18 (7%)

## polarity 分布
- supportive: 255
- critical: 44
- neutral: 27
- mixed: 8

## 关键发现
- ⚠️ **51% 评论是政策原文转载**(L1 step6_comments.py 召回质量需提升,真观点占比低)
- ⚠️ supportive 占 76%,critical 仅 13% — 评论选择偏官方/支持向(媒体覆盖偏差)

## Top 政策(stance 最多)

- `P_2025_NDRC_1745_c`:21 stance,{'supportive': 19, 'neutral': 1, 'critical': 1}
- `P_2025_NDRC_1656_a`:19 stance,{'supportive': 15, 'mixed': 1, 'critical': 3}
- `P_2025_MIIT_24_a`:13 stance,{'critical': 4, 'neutral': 3, 'supportive': 5, 'mixed': 1}
- `P_2024_MOFCOM_58_a`:13 stance,{'supportive': 10, 'neutral': 1, 'mixed': 1, 'critical': 1}
- `P_2024_MOFCOM_75_b`:12 stance,{'supportive': 7, 'neutral': 2, 'critical': 3}
- `P_2025_CQ_122582ad`:12 stance,{'supportive': 12}
- `P_2025_NDRC_632_c`:11 stance,{'mixed': 1, 'critical': 2, 'supportive': 7, 'neutral': 1}
- `P_2025_OTHER0858_255`:10 stance,{'supportive': 6, 'neutral': 2, 'critical': 2}
- `P_2024_SC_12_a`:8 stance,{'neutral': 2, 'supportive': 5, 'critical': 1}
- `P_2020_NDRC_889`:8 stance,{'neutral': 1, 'supportive': 4, 'critical': 3}