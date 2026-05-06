---
title: 2026-05-06 Phase 1 信息源根治 — Handoff to 主 session
date: 2026-05-06
session_origin: this side session (audit_2026-05-06)
target_session: main session
commit: c30fc57
status: Phase 1 完成 / Phase 2 待办清单已列
---

# Handoff:Phase 1 信息源根治成果 + Phase 2 待办

本文件供主 session 合并使用。本 session 已 commit (c30fc57),vault 干净,可继续工作。

---

## 1. 本 session 起因

用户做"虚拟电厂主题江苏省 0 条"展示数据时发现 vault 漏抓江苏 VPP 政策。诊断后是采集策略系统性偏向(国家级 + 直辖市倾斜),不是个案——浙江/广东/山东/河北/河南/安徽全主题大量漏。

## 2. 本 session 决策

13 主题(9 现有 + 4 新增) × 31 省 × 重点地市 矩阵全量根治。新增 4 主题:加油零售合规 / 居住区充电 / 配电网开放 / 聚合商准入。

## 3. Phase 1 执行成果

| 指标 | Before | After | 增幅 |
|---|---:|---:|---:|
| raw policies | 273 | **664** | +143% |
| 13×31 矩阵覆盖率 | 28.0% | **60.5%** | +116% |
| 非零 cells | 113 | 244 | +131 |
| business_view yaml | 526 | 603 | +77 |
| 9 类关系总条数 | — | **1202** | — |

各主题省份覆盖(After):
- V2G **18/31**(原 6)
- VPP **25/31**(原 9)
- 储能 **26/31**(原 11)
- 电力市场 **26/31**(原 12)
- 充电基础 **22/31**(原 13)
- 配电网开放(新) **27/31**
- 聚合商准入(新) **23/31**
- 居住区充电(新) **18/31**
- 加油零售合规(新) 4/31(待 Phase 2 重抓)

江苏 VPP 主题命中:成功(含苏发改能源发〔2025〕1198 号 等省级文件)。

## 4. 8 阶段执行链路(已落档)

| Stage | 工作 | 产出 |
|---|---|---|
| A | Tavily 矩阵 411 query | 2865 URL |
| B | 候选渠道晋升 156 任务 | 全 ok |
| C | 引用反扫补抓 100 文号 | 全 ok |
| D | 三路聚合去重 | 2296 候选(446 多路) |
| E | trafilatura 抓正文 | 484/600 ok |
| F | normalize → 0_raw/policies/ | 330 新 raw |
| G | trigger A 全套 | 14 subagent + apply + deterministic |
| H | 验证 + 落档 | 开发日记 + handoff |

## 5. Stage G 14 subagent 产出汇总

5C 派生(330 政策完整 schema:summary/scores/影响分析/行动建议):
- 7 batch × 48 = 330 政策全覆盖
- 110 derives_from 进 backlog(L1.3 demand-pull 候选)

rel_judge(196 关系):
- cites_basis +110 → 193
- aligns_with +34 → 124
- clarifies +22 → 106
- iterates +8 → 33
- extends +22 → 32

## 6. 文件位置索引

### 工具脚本(`_meta/audit_2026-05-06/`)
- 主题/地市配置: `themes_13.yaml`, `target_cities.yaml`
- audit 三件套(本地无 API): `local_coverage_baseline.py`, `audit_official_number_seq.py`, `audit_citation_gaps.py`
- Tavily 工具链: `gen_tavily_queries.py`, `run_tavily_matrix.py`, `run_candidate_promotion.py`, `run_citation_backfill.py`
- 抓取链: `fetch_candidates.py`(trafilatura + 强 chardet), `normalize_to_raw.py`, `fix_missing_dates.py`
- subagent 编排: `split_subagent_batches.py`
- 启动包: `PHASE1_PLAYBOOK.md`, `PHASE2_PLAYBOOK.md`

### 数据/审计产物(`_meta/audit_2026-05-06/`)
- `tavily_queries.jsonl` (411) / `tavily_results_merged.jsonl` (411 ok / 2865 URL)
- `candidate_promotion_tasks.jsonl` (156) / `promotion_merged.jsonl`
- `citation_gaps.json` (314 引用未收) / `citation_results.jsonl`
- `candidates_to_fetch.jsonl` (2296) / `candidates_top600.jsonl` / `candidates_rest.jsonl` (1696)
- `coverage_matrix.json` / `coverage_baseline.md` (After 60.5%)
- `official_number_audit.md` / `official_number_gaps.json`
- `new_pids.txt` (本批 330 个 pid) / `new_files.jsonl`

### 开发日记
- `开发日记/2026-05-06/日志.md`

## 7. Phase 2 待办(主 session 接手)

### P0 (优先做)

1. **4 新主题 entities 重跑**
   - 当前:`themes_registry.yaml` 已加 4 主题,`entities/registry.yaml` 已加 4 type=[theme] entry
   - 问题:`entities/_extractions.jsonl` 在 trigger A prepare 时已跑过,4 新主题 alias 没参与匹配,4 主题 _input.json 当前 0 命中
   - 动作:`python3 _meta/scripts/extract_entities.py` 全量重跑 + `crystallize_theme.py --all`
   - 预计影响:加油零售合规 / 居住区充电 / 配电网开放 / 聚合商准入 4 主题命中数从 0 → 30-50 政策(基于 grep 推算)

2. **160 个 isolated 政策 review**
   - rebuild_l2 audit 报告:160 政策 0 inbound + 0 outbound
   - 多数是新加入的 raw,可能是 rel_judge 漏抽 / 真无 vault 引用
   - 动作:跑 `python3 _meta/scripts/relations_coverage_metric.py --isolated-list`,挑 P0 主题(VPP/储能/电力市场)的 isolated 派 rel_judge 重抽

3. **issuer / region "未知" 50+ 篇 LLM 修复**
   - 本批 normalize 时 URL 域名不在 DOMAIN_REGION 表(媒体白名单 in-en.com / bjx.com.cn)的 raw 标 issuer "未知机构"、region.name "未知"
   - 动作:写 LLM-based 抽取脚本(扫 body 头 1KB + title)修复
   - 影响:这些 raw 在主题 crystallize 时省份匹配可能错位

### P1 (近期做)

4. **audit 三件套接 weekly cron**
   - 三脚本已就绪:`local_coverage_baseline.py` / `audit_official_number_seq.py` / `audit_citation_gaps.py`
   - 动作:写 `_meta/scripts/weekly_audit.py` 串起来 + macOS launchd plist / cron entry
   - 告警阈值见 `PHASE2_PLAYBOOK.md` §1

5. **policy-watch skill 升级到主题×省份矩阵 daily query**
   - 现有 skill 走固定 51 query 偏向国家级
   - 动作:把 `gen_tavily_queries.py` 复用到 daily,每日跑覆盖率最低的 50 cells

6. **DOCX 抓取兜底**
   - 本批 fail 42 个 .docx 文件(含湖南 VPP 实施细则等高价值)
   - 动作:`pip install mammoth python-docx`,改 `fetch_candidates.py` 加 docx handler,跑 42 个 + 持续

### P2 (后续做)

7. **trafilatura 抓 1696 个低优候选**(`candidates_rest.jsonl`)
   - 量力而行,可分多批

8. **江苏 jsdsm 6 篇代理路径单独抓**
   - `jsdsm.fzggw.jiangsu.gov.cn` 6 个 URL 全 connection refused,可能 DNS/SSL 问题
   - 动作:换网络环境(VPN/代理)或用浏览器导出

9. **候选渠道晋升结果回写《渠道目录.md》**
   - `promotion_merged.jsonl` 156 任务结果未回写
   - 命中 ≥3 P0 主题 → 晋升正式段;0 命中 → 删候选

10. **5C subagent prompt 改进**
    - 本次 D1<3 时 影响分析=null,但 apply 校验要 dict,我用 fix 脚本补 4 键 dict
    - 动作:改 `derive_business_view.py` PROMPT 让 LLM 输出 4 键 dict(值 = "无影响")

## 8. 已知问题/坑(主 session 注意)

1. **encoding 处理**:trafilatura 第一轮所有抓取乱码,修了强 chardet detect (HTML meta → HTTP header → chardet → fallback)。如果再扩展抓取,沿用 `fetch_candidates.py` 的逻辑。

2. **subagent context 限制**:330 pid 一次喂 1 个 subagent 会超 200K context,本次拆 7 batch × 48 = 14 subagent 并发解决。后续 trigger A 处理 ≥100 pid 时需类似拆批。

3. **5C schema 校验严格**:apply --stage 5c 要求 影响分析 必须 dict。fix 脚本 `_meta/audit_2026-05-06/(已 inline 在 commit 里)`。

4. **9 主题 vs 13 主题 crystallize**:`crystallize_theme.py --all` 当前只跑 themes_registry 里 entities/registry 同时有 entry 的主题。4 新主题 entry 已加,但因 _extractions.jsonl 没重跑,目前 0 命中。Phase 2 P0 #1 解决。

5. **160 isolated 政策**:不一定是 bug,部分是新闻/媒体白名单文章本身没引用 vault。但 P0 主题的 isolated 值得 review。

## 9. 撞车 / 备份

- 本 session 进行中另一 session "Optimize policy analysis vault integrity" 也在跑,备份在 `_l2_rebuild_state_backup_2026-05-06_14-00/`(已加 .gitignore,不入 commit)
- 我跑 trigger A 时该 session 也 commit 了 2 个改动(13b5d46 + 7dbccb7),不同文件无冲突
- 备份目录可删除:`rm -rf _l2_rebuild_state_backup_2026-05-06_14-00/`

## 10. 资源消耗

- Tavily: ~580 调用(2 个 dev key 混用,均未超额度)
- Firecrawl: 0 调用(SDK/key 缺,全走 trafilatura)
- subagent: 14 个(opus 4.7,各 5-10 min)
- wall time: 2.5h(14:00-16:30)

## 11. 江苏 VPP 临时补救包(早上做的)

发现漏抓时给用户的临时补救:
- `_meta/topic_distribution_jiangsu_vpp_patch.json` (6 江苏 VPP 政策的手工补全 JSON)
- 已被 Phase 1 全量覆盖,但保留作为示例

主 session 如要在前端展示,跑 `_meta/scripts/build_topic_distribution.py` 重新生成 `_meta/topic_distribution.json`(13 主题完整版)。

## 12. 一句话总结

> vault 从 273 raw 增长到 664 raw,13 主题 × 31 省矩阵覆盖率从 28% 跃升到 60.5%,本 session commit c30fc57 完成 Phase 1。Phase 2 还有 10 项待办(P0:3 / P1:3 / P2:4),最重要的是把 4 新主题 entities 重跑让其 0 命中 → 真实数据。
