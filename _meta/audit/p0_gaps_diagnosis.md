---
title: P0 主题 × P0 省 漏抓诊断
generated_at: 2026-05-07T23:13:57+08:00
generated_by: _meta/scripts/diagnose_p0_gaps.py
p0_themes: 8
p0_provinces: 6
cells_total: 48
  cat_✓_健康: 41
  cat_R3_promote_漏: 3
  cat_R2_部分_fetch_失败: 1
  cat_R2_fetch_全失败: 3
---

# P0 主题 × P0 省 漏抓诊断(2026-05-07T23:13:57+08:00)

## 总览

| category | cells |
|---|---:|
| ✓ 健康 | 41 |
| R3 promote 漏 | 3 |
| R2 fetch 全失败 | 3 |
| R2 部分 fetch 失败 | 1 |

## 漏抓矩阵(P0×P0)

| 主题 | 省 | vault | tavily q/r | top600 | top600 失败 | rest | category |
|------|-----|------:|------:|------:|------:|------:|---------|
| V2G(车网互动) | 浙江 | 0 | 2/8 | 0 | 0 | 2 | R3 promote 漏 |
| 虚拟电厂 | 江苏 | 0 | 3/17 | 3 | 1 | 6 | R2 部分 fetch 失败(1/3) |
| 充电基础设施 | 江苏 | 0 | 3/17 | 1 | 1 | 10 | R2 fetch 全失败 |
| 新型储能 | 江苏 | 0 | 3/16 | 0 | 0 | 11 | R3 promote 漏 |
| 聚合商接入 | 江苏 | 0 | 3/16 | 0 | 0 | 8 | R3 promote 漏 |
| 配电网开放 | 江苏 | 0 | 2/11 | 2 | 2 | 6 | R2 fetch 全失败 |
| 绿电交易 | 江苏 | 0 | 1/3 | 1 | 1 | 2 | R2 fetch 全失败 |

## 重点 cells 详情(非健康)

### V2G(车网互动) × 浙江

- **vault 命中**: 0
- **Tavily**: 2 queries / 8 results
- **top600 候选**: 0(0 fetch 失败)
- **rest 候选**(promote 漏): 2
- **category**: R3 promote 漏
- **action**: rest 中有 2 候选,本次修 promote 后会进 top600
- **rest url(前 10)**:
  - https://www.nea.gov.cn/20250425/6c21959a140744a6bb35916e634cc9b6/c.html
  - https://zjic.zj.gov.cn/zkdtx/202410/t20241018_22942029.shtml

### 虚拟电厂 × 江苏

- **vault 命中**: 0
- **Tavily**: 3 queries / 17 results
- **top600 候选**: 3(1 fetch 失败)
- **rest 候选**(promote 漏): 6
- **category**: R2 部分 fetch 失败(1/3)
- **action**: 重抓失败的 url + 检查为何 ok url 也未入库
- **fetch 失败 url(前 10)**:
  - http://jsdsm.fzggw.jiangsu.gov.cn/dsmsite/dlggjs/2776.jhtml

### 充电基础设施 × 江苏

- **vault 命中**: 0
- **Tavily**: 3 queries / 17 results
- **top600 候选**: 1(1 fetch 失败)
- **rest 候选**(promote 漏): 10
- **category**: R2 fetch 全失败
- **action**: 走 SKILL §A.6 fallback chain(playwright/手动)
- **fetch 失败 url(前 10)**:
  - http://jsdsm.fzggw.jiangsu.gov.cn/dsmsite/2jdxw/5407.jhtml

### 新型储能 × 江苏

- **vault 命中**: 0
- **Tavily**: 3 queries / 16 results
- **top600 候选**: 0(0 fetch 失败)
- **rest 候选**(promote 漏): 11
- **category**: R3 promote 漏
- **action**: rest 中有 11 候选,本次修 promote 后会进 top600
- **rest url(前 10)**:
  - http://jsdsm.fzggw.jiangsu.gov.cn/dsmsite/2jdxw/4684.jhtml
  - http://www.ditan.com/industry/energy-storage/6797.html
  - http://www.nea.gov.cn/1310757632_17036659274831n.doc
  - https://tzxm.fzggw.jiangsu.gov.cn/portalopenPublicInformation.do?method=goPromotionPage
  - https://tzxm.fzggw.jiangsu.gov.cn/portalopenPublicInformation.do?method=querybeianExamineAll&pageSize=20&pageNo=8&apply_project_name=&id=026260a6da4e4110bd2d8c429548bf6b
  - https://tzxm.fzggw.jiangsu.gov.cn/tzxmweb/portalopenPublicInformation.do?method=queryExamineAll
  - https://www.changzhou.gov.cn/ns_news/185177439890074
  - https://www.suzhou.gov.cn/szsrmzf/zfbgswj/202205/c2fda710427a4ab8a5da2eb878a66953/files/9b996439d54547379db320f7f7e77a9b.pdf
  - https://www.wnd.gov.cn/doc/2022/08/11/3730532.shtml
  - https://www.wxlx.gov.cn/doc/2023/01/06/3859868.shtml

### 聚合商接入 × 江苏

- **vault 命中**: 0
- **Tavily**: 3 queries / 16 results
- **top600 候选**: 0(0 fetch 失败)
- **rest 候选**(promote 漏): 8
- **category**: R3 promote 漏
- **action**: rest 中有 8 候选,本次修 promote 后会进 top600
- **rest url(前 10)**:
  - http://www.szwz.gov.cn/szwz/bmdt/202512/3dfc0be5d98d448494ddc7be4f910798.shtml
  - https://mchuneng.in-en.com/html/chunengy-53602.shtml
  - https://www.nanjing.gov.cn/xxgkn/jytabljggk/2024njytabl/shizxta/202411/t20241120_5013567.html
  - https://www.nanjing.gov.cn/xxgkn/jytabljggk/2025njytabl/shizxta/202512/t20251203_5704597.html
  - https://www.nanjing.gov.cn/zdgk/202601/t20260121_5774264.html
  - https://www.suzhou.gov.cn/szsrmzf/zfbgswj/202205/c2fda710427a4ab8a5da2eb878a66953/files/9b996439d54547379db320f7f7e77a9b.pdf
  - https://www.zgjssw.gov.cn/yaowen/202411/t20241120_8427783.shtml
  - https://www.zgjssw.gov.cn/yaowen/202501/t20250114_8447507.shtml

### 配电网开放 × 江苏

- **vault 命中**: 0
- **Tavily**: 2 queries / 11 results
- **top600 候选**: 2(2 fetch 失败)
- **rest 候选**(promote 漏): 6
- **category**: R2 fetch 全失败
- **action**: 走 SKILL §A.6 fallback chain(playwright/手动)
- **fetch 失败 url(前 10)**:
  - http://jsdsm.fzggw.jiangsu.gov.cn/dsmsite/2jdxw/5407.jhtml
  - http://jsdsm.fzggw.jiangsu.gov.cn/dsmsite/u/cms/www2/201904/16095053p98b.pdf

### 绿电交易 × 江苏

- **vault 命中**: 0
- **Tavily**: 1 queries / 3 results
- **top600 候选**: 1(1 fetch 失败)
- **rest 候选**(promote 漏): 2
- **category**: R2 fetch 全失败
- **action**: 走 SKILL §A.6 fallback chain(playwright/手动)
- **fetch 失败 url(前 10)**:
  - http://jsdsm.fzggw.jiangsu.gov.cn/dsmsite/2jdxw/5393.jhtml
