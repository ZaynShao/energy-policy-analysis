---
title: 回送给 skill 建设 session 的需求队列
purpose: L3 月报实战 session 在 reproduce / 月报实战中发现的 L1/L2 数据问题,逐条记录,等 skill session 排期处理
last_updated: 2026-04-28
---

# Back to skill session

L3 实战 session 按 handoff §5 约定:发现 L1/L2 数据缺陷不自己改,追到本队列等 skill session 在他的 commit 里处理。

每条格式:
- **背景**:在哪发现的
- **问题**:具体数据/字段
- **影响**:对月报哪部分
- **建议方案**:具体怎么修(spec)

---

## 队列

### #1 entity 抽取缺 theme 关联(高优先级)

**背景**:reproduce 2026-03 v6 时,`_docx_data.json` 的 `theme_coverage` 字段 5 个主题全部 `covered=0 blank=0`(空)。

**问题**:`prep_docx_data.py` 通过 `policy_entities[pid]` 查找 `theme_id in policy_entities[pid]` 判断政策是否归属某主题,但 entity 抽取产物 `1_extracted/entities/_extractions.jsonl` 里 policy 实体行没有 theme 字段(或 theme_id 字段未关联)。具体表现:

```python
for pid in policy_entities:
    if theme_id in policy_entities[pid]:  # 永远 False
        ...
```

L2 已在 `entities/registry.yaml` 加了 5 个 type=theme 实体(VPP/ESS/GAS/ER/GREEN),但 `_extractions.jsonl` 里 policy 行没填 `themes` 字段,或者 theme_id 命名 prep 拿不到。

**影响**:月报 §7 主题×31 省份缺口矩阵渲染为空表;蓝本 §3 §7 这是核心章节。

**建议方案**:
1. 重跑 `extract_entities.py`,对每篇 policy 通过 `tags` / `keywords` 匹配 5 个新 theme 实体的 aliases,把命中 theme 写到 policy 实体的 `themes: [...]` 字段
2. 新加 3 个 theme(VPP_THEME / GAS_STATION_TRANSITION / GREEN_POWER_TRADING)需让 prep 端可见 — 要么在 `prep_docx_data.py` 里加(L3 自己改),要么 entities/registry.yaml 在 prep 加载点能 enumerate
3. 验证:重跑 prep 后,`theme_coverage[VPP].covered` 应至少 ≥3(VPP_THEME 主题结晶页有 73 政策)

**判定 done**:`_docx_data.json` 里 `theme_coverage` 5 个主题(或扩到 8 主题)的 `covered + blank = 31`,且至少 3 个主题 covered ≥3。

---

### #2 month_dist 字段陈旧 + entity_canonical / relations 计数过期(中优先级)

**背景**:`_docx_data.json` 的 `data_health` 字段值与 `_global_index.md` 当前快照不一致:

```
            _docx_data.json     _global_index.md
entity_canonical    88              94
relations_total     198             298
crystallized_themes 3               8
lint_errors         1               0
```

**问题**:不确定是 prep 硬编码,还是 prep 读了某个静态 JSON 没更新。

**影响**:小 — 蓝本 §3 已淘汰"数据健康度小卡",renderer 不应消费这个字段。但留着字段对将来仍可能误用。

**建议方案**:
- 优先级 A:L3 prep 自己改,删除 `data_health` 字段生成(本 session 自己处理,不打扰 skill session)
- 备选:让 prep 改读 `2_crystallized/_global_index.md` frontmatter

**判定 done**:本队列条目可关闭(由 L3 实战 session 自行处理)。

---

### #3 _extractions.jsonl 引用孤儿 pid(中优先级)

**背景**:跑 `gen_march_dryrun.py` 时 `KeyError: 'P_2024_OTHERD347_052923d9'`。这个 pid 出现在 `policy_entities` 字典(从 `_extractions.jsonl` 读),但不在 `0_raw/policies/` 目录里(本月 A 类清理 26 篇政策解读重分类时,可能把它移到 `commentaries/` 或 dedup 时删了)。

**问题**:`_extractions.jsonl` 没在 A 类清理后同步重抽。可能还有其它孤儿 pid 没暴露(只是没被本次循环触发)。

**影响**:任何遍历 `_extractions.jsonl` 后访问 `0_raw/policies/{pid}` 的下游脚本都会 KeyError。L3 自己已就地加防御性 `if pid not in all_p: continue`,但根因在 L2。

**建议方案**:
1. 写一个 lint:`set(extraction pids) - set(0_raw policies pids)` 应为 ∅
2. 在 A 类清理 / dedup 后自动触发 entity 重抽(或至少删除孤儿条目)
3. `daily_lint.py` 加这一项作为 warning

**判定 done**:`_extractions.jsonl` 里所有 policy id 都在 `0_raw/policies/{id}*.md` 找得到。

---

### #4 (示例条目预留 — 后续追写格式参考)

**背景**:

**问题**:

**影响**:

**建议方案**:

**判定 done**:

---

## 追写指引(给后续 L3 session 看)

发现 L1/L2 问题时:
1. 不要自己修 `0_raw/` `1_extracted/` `2_crystallized/`(只读)
2. 在本文件追一条新 entry,用 ## 标题 + 4 段格式
3. 月报里那条相关论断改用最弱表述 + 注明数据局限,继续推进
4. 如果发现是 L3 自家脚本(`prep_*` `render_*` `gen_*report*`)的问题,在 L3 这边改,但反馈一份心智模型到本队列(可选)

skill session 在他下一个工作 cycle 会读本队列,排期处理。
