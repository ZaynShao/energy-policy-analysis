---
title: L3 月报实战 · Day 1 reproduce 2026-03 v6
date: 2026-04-28
session: l3-monthly-report
type: 实战日志
related: docs/handoffs/2026-04-28-l3-monthly-report-handoff.md
---

# Day 1:reproduce 2026-03 v6

按 handoff 第一周 checklist 跑环境检查 + reproduce march pipeline,出 v6 重制版,记录 L2 本月更新对 v6 论断的影响。

## 1. 跑了什么

| Step | 命令 | 产物 | 状态 |
|---|---|---|---|
| 0 环境检查 | python deps / node v22 / `daily_lint.py` / 8 themes / 关系 wc -l | — | ✅ 0 errors / 0 warnings |
| 1 验证依赖 | `_consolidated.json` 11 march_detail / DEEP_DIVE_IDS 在位 | — | ✅ |
| 2 dryrun | `gen_march_dryrun.py`(中途 KeyError 防御性 fix 见下) | `~/Desktop/能源政策月报-2026-03-DRYRUN.md` 320 行 | ✅ |
| 3 prep + charts | `prep_docx_data.py` / `render_march_charts.py` | `_docx_data.json` 81.6KB / 6 张 PNG | ✅ |
| 4 render | `render_docx.js` / `render_html.py` | docx 782.7KB / html 1267.6KB | ✅ |

## 2. 关系数据(handoff §2 一致)

```
supersedes 2 / iterates 12 / extends 8 / clarifies 46
references 172 / aligns_with 4 / conflicts_with 0 / cites_basis 54
合计 298 边(+ 12 archive)
```

## 3. v6 重制版数据快照

```
march_count: 11      (baseline JSON 是 8,L1 后续补了 3 篇 march 政策)
march_strong: 4      ⭐≥4 业务命中
march_medium: 5
march_weak: 2
ge4_total: 124       (baseline 也是 124,一致)
march_opinions: 0    (opinions 覆盖 20.5% 未命中本月新政,handoff §4 已知)
```

deep-dive 3 篇:`P_2026_SC_0305e288`(政府工作报告)/ `P_2026_NPC_03132f88`(十五五规划纲要)/ `P_2026_NEA_0304ed54`(能源乡村振兴)— 与 v6 蓝本一致。

## 4. 蓝本合规校验

✅ 全部通过 sanitize:无「立即行动」「四大业务」「乡村业务」「滴滴」品牌名「Claude」「Anthropic」「docx-js」「matplotlib」「token」「自动生成」等违禁词。

✅ `biz_impact` 字段 keys 完全对齐蓝本 §4.1:`{加油, 充电, 电力_储能_V2G_交易, 乡村}`。

## 5. L2 数据更新对 v6 论断的影响(本次 reproduce 核心发现)

### 🔴 高优先级 — 渲染层与 L2 不同步

**5.1** `linkage_type` 未做蓝本 §6.3 重映射

`prep_docx_data.py` 把 `_consolidated.json` 里 Agent 旧 taxonomy 直接传给 renderer:

```
当前:Counter({'主题对应*': 6, '借鉴框架': 3})
蓝本要求:
  借鉴框架 → 补充细化
  主题对应 → 同向部署
```

结果:月报 §5 落地证据表的 linkage 列会显示旧术语,违反蓝本。**需要在 prep 阶段加 sanitize 字典做 1:1 替换。**

**5.2** `theme_coverage` 全部空 0/0(主题×省份覆盖矩阵)

```
V2G/车网: covered=0  blank=0
电力市场: covered=0  blank=0
充电基建: covered=0  blank=0
新型储能: covered=0  blank=0
设备更新: covered=0  blank=0
```

prep 期望 5 主题(蓝本 v1 时期硬编码),但本月 L2 加的 5 个 type=theme 实体(VPP/ESS/GAS/ER/GREEN)和 prep 列表只重叠 2 个(ESS=新型储能 / ER=设备更新),且 entity 抽取 jsonl 没把 theme 关联到 policy(`policy_entities[pid]` 没 theme_id 字段)→ 查找返回 0。

结果:**月报 §7 主题×省份缺口矩阵渲染为空表**。需要 entity 抽取重跑或 prep 改读 `2_crystallized/themes/*/regional-coverage.md`。

### 🟡 中优先级 — 数据陈旧 / 章节淘汰

**5.3** `data_health` 字段陈旧

```
当前 _docx_data.json:
  vault_policies: 263       ✓
  entity_canonical: 88      (handoff §2 当前 94)
  relations_total: 198      (当前 298)
  crystallized_themes: 3    (当前 8)
  lint_errors: 1            (实测 0)
```

而蓝本 §3 已把"数据健康度小卡"列为淘汰章节。两个修法:
- prep 不再生成 `data_health` 字段(更彻底)
- 或 renderer 忽略它

**5.4** `gaps` + `theme_coverage` 仍只用旧 5 主题

L2 本月新加的 VPP_THEME / GAS_STATION_TRANSITION / GREEN_POWER_TRADING 在月报 §7 完全缺席。这是新主题对月报覆盖的反映断点。

### 🟡 视觉降级

**5.5** chart 6 处 `Glyph 11088 (⭐) missing from font(s) STHeiti`

`render_march_charts.py` 里图表标题/标签的 ⭐ 渲染成方框。蓝本 §4.4 emoji 规则保留 ⭐ 用于评分体系,所以是要展示的;字体 fallback 链需要加 PingFang SC 或 Apple Color Emoji。

### 🟢 已就地修复(L3 自家脚本)

**5.6** `gen_march_dryrun.py` 在 theme→省份覆盖循环里访问 `all_p[pid]` 但 entity 抽取的 jsonl 引用了一个孤儿 pid `P_2024_OTHERD347_052923d9`(本月 A 类清理或 dedup 删了,entity 抽取没同步)。加一行 `if pid not in all_p: continue` 防御性 skip,exit 0。

补丁位置:`_meta/scripts/gen_march_dryrun.py:122` 加 `if pid not in all_p: continue`(line 122 之后,line 123 之前 — 确切在 `if theme_id in policy_entities[pid]:` 之前)。

**5.7** `gen_march_dryrun.py` 章节目录(line 14-31)还反映 v1 时期(含「舆论温度计」「数据健康度小卡」「数据出处与方法论」),与蓝本 §3 已淘汰章节冲突。但 dryrun 仅做骨架预览,真正 v6 章节由 prep + render_docx/html 决定 — 低优先级 cleanup,**未修**。

## 6. 给 skill session 的反馈(已追到 back-to-skill-session.md)

按 handoff §5:遇 L1/L2 数据缺陷不自己改,追到回送队列。

- 5.1 linkage_type 重映射 — **L3 prep 改即可,我不打扰 skill session**
- 5.2 theme_coverage 空 — entity 抽取需重跑加 theme 关联 → 追条
- 5.3 data_health 陈旧 — prep 改即可,顺带去掉淘汰字段
- 5.4 主题缺 VPP/GAS/GREEN — entity 抽取问题,跟 5.2 同根 → 追条
- 5.5 ⭐ glyph 缺字体 — L3 渲染脚本改即可
- 5.6 已就地 fix
- 5.7 dryrun 章节陈旧 — 低优先级,未列

## 7. 下一步(Day 2 推荐)

按选项 A 第 4 步 + 切到选项 B Day 3:

- [ ] 修 5.1 linkage_type 重映射(prep,~30 分钟)
- [ ] 修 5.5 ⭐ 字体 fallback(render_march_charts,~10 分钟)
- [ ] 修 5.3 prep 不再生成 data_health(顺手清淘汰字段,~10 分钟)
- [ ] 重跑 prep + charts + render → 出 v6 重制版 v2
- [ ] 5.2/5.4 等 skill session 重抽 entity 后再看

修完 5.1+5.3+5.5 后,reproduce 出来的 v6 重制版可以作为 2026-04 月报 v1 的脚手架。

## 附:输出文件位置

```
~/Desktop/能源政策月报-2026-03-DRYRUN.md     (15.6KB · gen_march_dryrun)
~/Desktop/能源政策月报-2026-03.docx          (782.7KB · render_docx)
~/Desktop/能源政策月报-2026-03.html          (1267.6KB · render_html)
_meta/march_report_batches/_docx_data.json   (81.6KB · prep)
_meta/march_report_batches/charts/*.png      (6 张 · render_march_charts)
```
