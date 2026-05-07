---
title: 2026-05-06 Phase 2 B6+B8 完成 handoff — 回主 session
date: 2026-05-06
prev_commits:
  - e771af1 feat(B8) 派生层 wiki link 显式化
  - e2de178 feat(B6) dangling pid 全景扫 + future_date cleanup
  - 100e403 feat(B5) opinions-summary 13 主题重生
  - 6d943ee feat(B2+B3)
  - e370cac feat(B1)
  - 8c7bbf3 fix(B0)
session: auto-mode subagent (按 2026-05-06-phase2-B6B8-handoff.md §1-§9 执行)
duration: ~25 min
status: ✅ 全部 deterministic 完成
---

# Phase 2 B6 + B8 完成 — 接回主 session

按 `docs/handoffs/2026-05-06-phase2-B6B8-handoff.md` §1-§9 全部执行完毕。
两个独立 commit:`e2de178`(B6)+ `e771af1`(B8)。指标稳定,可直接接 B7 或下个任务。

---

## 1. baseline → 终态对比

| 指标 | baseline | 终态 |
|---|---|---|
| vault_pids | 664 | 664 ✓ |
| relations metric (policies/edges/双向/孤立) | 664/1148/150/132 | 664/1148/150/132 ✓ |
| (a) jsonl from/to dangling | 0 | **0** ✓ |
| (b) 派生 .md wiki dangling | 2¹ | 2¹(同前) |
| (c) fm.date 未来日期 | 8 | **0** ✓ |
| (c) fm.date=1900 + recent fetch | 0 | 0 ✓ |
| 派生层 alias `[[P_xxx]]` 总数 | ~4500 | **0** ✓ |
| 派生层 explicit `[[stem|P_xxx]]` 总数 | ~75 | **4105** ✓ |
| opinions-summary §1-§5 裸 pid | 0 | 0 ✓ |
| alias collision | 0 | 0 ✓ |
| history (rel_judge / stance / opinions) | 781/189/22 | 781/189/22 ✓(无 LLM 调用) |

¹ 这 2 条都在 `_meta/schema_v3.md` 内是示例占位符 `P_2025_SD_xxx` / `P_2026_SH_xxx`(显式 `xxx` 后缀,文档说明用),非真 dangling — 不动。

---

## 2. B6 cleanup 8 个 future_date 明细

原 fm.date 全部为 `'2027-01-01'`(LLM 抽取时把"三年倍增 2025—2027"目标年错认为发文日)。

修复优先级:URL 路径模式 → body 文号 → fetched_at 回退。

| pid | old | new | method |
|---|---|---|---|
| P_1900_QH_af736607 | 2027-01-01 | 2024-09-20 | url_path_pattern |
| P_1900_SN_5f4dd35d | 2027-01-01 | 2025-10-16 | url_path_pattern |
| P_1900_QH_123e5b27 | 2027-01-01 | 2025-01-02 | url_path_pattern |
| P_1900_GZ_2dad70b3 | 2027-01-01 | 2026-01-04 | url_path_pattern |
| P_1900_HN_8fa9634d | 2027-01-01 | 2024-02-28 | url_path_pattern |
| P_1900_SN_1cd1e821 | 2027-01-01 | 2025-10-16 | url_path_pattern |
| P_1900_JX_33d58f3b | 2027-01-01 | 2026-05-06 | fetched_at_fallback ⚠ |
| P_1900_JX_91234f69 | 2027-01-01 | 2026-05-06 | fetched_at_fallback ⚠ |

⚠ 2 个江西 `drc.jiangxi.gov.cn` CMS URL 是内部 ID 不带日期(`/content/content_<snowflake>.html`),且 body 是摘要片段太短无 `〔YYYY〕`文号锚点 — 走 fetched_at 回退。`provenance.date_fixed_method=fetched_at_fallback` 全留 audit。后续可单独 refetch 完整正文再二次修。

8 个 raw 都有 `__pre_date_fix_2026-05-06_18-41-38.md` 备份在 `0_raw/_archive/policies/`(SKILL §6 协议)。

---

## 3. 新增产物清单

### 脚本(deterministic, 可重跑)
- `_meta/scripts/oneshot_build_pid_filestem_index.py` — 共用索引 builder
- `_meta/scripts/oneshot_scan_dangling_pids.py` — 4 类 dangling 全景扫
- `_meta/scripts/oneshot_cleanup_dangling.py` — future_date 修复(§6 协议)
- `_meta/scripts/oneshot_explicit_wiki_links.py` — alias → explicit 转换

### 索引 / audit
- `_meta/audit/vault_pids.txt`(664)
- `_meta/audit/pid_to_filestem.json`(664)
- `_meta/audit/dangling_scan_2026-05-06.json`
- `_meta/audit/dangling_cleanup_2026-05-06.json`

### 数据修改
- `0_raw/policies/` — 8 个 fm.date 修
- `0_raw/_archive/policies/` — 8 个 `__pre_date_fix_*.md` 备份
- `2_crystallized/themes/*` — opinions-summary / regional-coverage / timeline / _input.json 全显式化
- `2_crystallized/regions/*` — 同
- `2_crystallized/_global_index.md` — rebuild 重生
- `1_extracted/relations/_index_by_policy/_rev_*.md` — rebuild 重生 + 显式化
- `_meta/*_theme_input.json` × 13 — crystallize 缓存刷新

---

## 4. 用户验证步骤

1. **Obsidian 打开任意 `2_crystallized/themes/*/opinions-summary.md`**
   - 点 §1 / §2 / §3 中任意 `[[…|P_xxx]]` → 应**直接跳转**到 raw 政策文件
   - 之前点不动的 alias `[[P_xxx]]` 现在已全部带 file_stem 前缀

2. **看 graph view**
   - 8 个 P_1900 假未来日期(2027-01-01)节点 → 应已修复到真实/接近日期
   - dangling 节点(蓝色虚线)应只剩 schema_v3.md 里的 2 个文档示例

3. **抽样查看任一 _rev_*.md**(反链文件)
   - 例 `1_extracted/relations/_index_by_policy/_rev_P_2024_SC_7.md`
   - 全部入向链接现在是 `[[完整文件名|P_xxx]]` 格式

---

## 5. 已知尾巴 / 后续 P1

- **B7**(P1):132 个真孤立政策分类打 tag(B2 trigger F 已审 118 候选,剩余真孤儿)
- **2 个江西 fetched_at_fallback**:可单独写 refetch 脚本读完整正文,再二次修 fm.date
- **`_meta/schema_v3.md` 2 条 `P_2025_SD_xxx` / `P_2026_SH_xxx`**:文档示例,无需处理(已在 scan 报告里持续显示,可视为白名单)

---

## 6. 暗坑 / 工程细节(给主 session 注意)

1. **B8 必须在 deterministic post-llm rebuild 之后再跑一次**
   - 原因:`build_reverse_links.py` 重生 `_rev_*.md` 时输出 alias 形式,会覆盖 B8 第一次的显式化结果
   - 已在本次 cleanup 中处理(rebuild → B8 第二次),但**根治需要改 build_reverse_links.py 直接生成 explicit 格式**(下次有空可做,或加 post-rebuild hook)

2. **fetched_at_fallback 的 2 个江西文件可能在 B5 / B7 主题分析里看起来"很新"**(date=2026-05-06 = 当天)
   - 这是已知降级,audit 字段可追溯
   - 如对主题时间分布有影响,优先 refetch 而非用启发式猜日期

3. **fm 边界 regex `^---\s*\n(.*?)\n---\s*(\n|$)`** 已沿用 B3 模板,新脚本未踩 title 含 `---` 的坑

4. **没动 jsonl** — 因为扫描 (a) 类是 0 条,所有 from/to dangling 校验在 apply 阶段已生效

---

## 7. 一句话总结

> B6 + B8 全 deterministic 完成,~25 min。8 个 future_date(2027-01-01)
> 修到真实日期(6 个 URL 抽精准 + 2 个 fetched_at 回退);派生层 4500
> 个 alias 全转 4105 个显式 `[[stem|P_xxx]]`,Obsidian 100% 可点;0 LLM 调用,
> 0 history 增量,relations metric 稳定。下一步建议 B7 孤立分类。
