# Energy Policy Analysis

能源政策分析知识库 — 三层架构(L1 采集 / L2 知识图谱 / L3 报告产出)。

服务公司决策层,覆盖三大业务:加油 / 充电 / 电力(后者含储能·V2G·电力交易)。乡村是关注方向(非业务线)。

---

## 三层架构

| 层 | 职责 | 方法论 | 当前状态 |
|---|---|---|---|
| **L1 采集** | 政策发现 / 抓取 / 入库 | 8 步采集法 | 357 政策入库,日志在 `0_raw/policies/` |
| **L2 知识图谱** | canonical 实体 / 关系 / 主题结晶 | Karpathy LLM Wiki v2 (schema v3) | 9 个派生脚本跑通,3 个主题已结晶(V2G / 电力市场 / 充电基建) |
| **L3 报告产出** | 月报 / 决策卡片 / 深度报告 | 四维决策框架 | 月报蓝本完成(2026-03 v6) |

---

## 目录结构

```
.
├── 00 背景资料/         # L1+L2+L3 方法论文档
│   ├── 滴滴能源-政策分析背景.md   # 业务定位、决策框架
│   ├── 渠道目录.md                # 46 个已验证政策来源
│   ├── 政策重要性打分体系.md      # 六维打分 + 四象限
│   ├── 策略-八步采集法.md         # L1 SOP
│   └── 策略-L3月报需求原型.md     # L3 月报规范(本月新增)
├── 0_raw/               # L1 原始政策(frontmatter v3 + body)
│   └── policies/*.md    # 357 篇政策
├── 1_extracted/         # L2 派生:实体 / 关系 / 立场
│   ├── entities/
│   ├── relations/
│   └── stances/
├── 2_crystallized/      # L2 主题结晶页
│   └── themes/          # V2G / 电力市场 / 充电基建
├── 3_lints/             # L2 lint 报告(每周)
└── _meta/               # 工具链
    ├── scripts/         # L2 派生脚本 + L3 渲染脚本
    ├── schema_v3.md     # L2 schema 契约
    ├── pipeline.md      # 派生管道说明
    └── march_report_batches/  # L3 月报中间产物
```

---

## L3 月报生成管道

数据层 + 双 renderer 解耦,docx 和 html 同源:

```
prep_docx_data.py   →  _docx_data.json  ┬→  render_docx.js  →  *.docx
                                        └→  render_html.py  →  *.html

render_march_charts.py  →  charts/*.png  →  (两个 renderer 都用)
```

**重生成月报(当前手动 4 步,后续 OpenClaw cron 部署后自动):**

```bash
cd "/path/to/vault"
python3 _meta/scripts/render_march_charts.py    # chart 不变可跳
python3 _meta/scripts/prep_docx_data.py         # 数据层
NODE_PATH=/opt/homebrew/lib/node_modules \
  node _meta/scripts/render_docx.js             # docx
python3 _meta/scripts/render_html.py            # html
```

输出:`~/Desktop/能源政策月报-YYYY-MM.docx` + `.html`

---

## L2 派生管道

**daily mode**(单篇/小批量):

```bash
python3 _meta/scripts/upgrade_frontmatter_v2_to_v3.py    # 升级 frontmatter
python3 _meta/scripts/extract_entities.py                # canonical 实体
python3 _meta/scripts/extract_relations_regex.py         # 文号引用关系
python3 _meta/scripts/extract_relations_heuristic.py     # 启发式关系
python3 _meta/scripts/aggregate_opinions.py              # 立场聚合
python3 _meta/scripts/dedup_policies.py                  # 去重(3 规则)
python3 _meta/scripts/lint.py                            # 11 项 lint
```

**weekly mode**(全量重建主题结晶页):

```bash
python3 _meta/scripts/crystallize_theme.py --theme v2g --aliases ... --theme_zh "V2G/车网"
```

详见 `_meta/pipeline.md`。

---

## L1 采集

8 步采集法见 `00 背景资料/策略-八步采集法.md`。

当前为手动触发,未来通过 OpenClaw `policy-watch` skill 双模运行(daily cron 拉模式 + 频道触发推模式)。

---

## 重要规则(写入决策层文档前必读)

详见 `00 背景资料/策略-L3月报需求原型.md` 第 4-7 节,核心摘要:

- **业务表述:** 唯一合法是「公司三大业务(加油/充电/电力)」+「乡村能源关注方向」。禁用「四大业务」「乡村业务」等任何虚构业务线。
- **品牌:** 对内统一用「公司」,不用任何品牌名。
- **行动分类:** 4 级 = A 趁早 / B 研究 / C 跟进 / D 跟踪。不用「立即」(过激紧迫感)。
- **emoji:** 全文无 emoji,仅 ⭐ 用于重要性打分。
- **工具痕迹:** 不出现 Claude / docx-js / Agent / token / 自动生成 等。
- **比较级 fact-check:** 「首批 / 首个 / 首破」必须查 vault 验证,不能仅凭印象。
- **国家级 → 省级因果:** 同月发布属「同源并行」,非「派生因果」(省级专项起草周期 6-12 月)。
