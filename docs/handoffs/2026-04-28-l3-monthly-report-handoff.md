# Handoff · L3 月报实战 session

**交接日期**:2026-04-28
**交接方**:skill 建设 session(继续做 superpowers skill 等)
**接收方**:L3 月报实战 session(本文档读者)
**前置阅读时间**:15-25 分钟
**首次实战预估**:2-4 天(2026-04 月报)

---

## 0. 你的任务范围

**目标**:用 L1 + L2 已建好的数据底座,产出 **2026-04 月度政策动向月报**(给公司决策层),并把流程模板化让 5 月、6 月每月可跑。

**不在你范围**(交还给 skill 建设 session):
- L1 采集层修改(8 步法升级 / PDF 抽取 / 高规格渠道补)
- L2 schema 升级 / 抽取脚本重构
- 通用 superpowers skill 建设
- registry / 关系层 / themes 的进一步扩抽

如果你发现 **L2 数据不够支撑某个月报论断**,**不要自己改 L2**,而是:
1. 在 `docs/handoffs/back-to-skill-session.md` 追写一条具体需求(有 spec)
2. 月报里那条论断**用最弱形式表述 + 注明数据局限**,继续推进

---

## 1. 如何启动(第一天就读这 4 个文件)

按顺序读:

1. **`README.md`**(10 分钟)
   三层架构 + 当前状态 + 文件树
2. **`00 背景资料/滴滴能源-政策分析背景.md`**
   业务定位、四维决策框架 — 月报最终读者要的视角
3. **`00 背景资料/策略-L3月报需求原型.md`**(286 行,**最关键**)
   L3 月报规范:目标/边界/章节结构/双格式(Word + HTML)/数据流
   这是 2026-03 月报 v1→v6 实战提炼的成果,本月就是按这个跑
4. **`2_crystallized/_global_index.md`**
   当前数据全貌仪表盘(政策数 / 关系网 / opinion 覆盖率 / 健康指标)

读完上面 4 个,你就知道月报"长什么样"+"用什么数据"。

---

## 2. 当前政策知识库建设进度(2026-04-28 23:00 快照)

### L1 采集层(0_raw/)

| 项 | 数量 |
|---|:-:|
| 政策原文(`0_raw/policies/`) | **263 篇**(本月清理后) |
| 评论(`0_raw/commentaries/`) | **364 篇** |
| dedup 档案(`0_raw/_duplicates/`) | 71 篇 |
| 政策正文完整性 | 100%(无 PDF 二进制失败) |
| gov.cn 高规格采集占比 | 99.6% |

frontmatter 健康度:
- 必填字段(id/title/date/region/provenance):**100% 齐全**(0 errors)
- `issuer_canonical` 字段已加(本月新):87.9% 命中率
- region.level=未知:**0 篇**(本月修完)

### L2 知识图谱层(1_extracted/ + 2_crystallized/)

#### 实体注册(`1_extracted/entities/registry.yaml`)

| type | 数量 |
|---|:-:|
| stakeholder | 51 |
| org | 25 |
| region | 9 |
| concept | 8 |
| **theme** | **5**(本月新增,见下) |
| **总计** | **94** |

新加 theme 实体(本月):
- `vpp_theme` 虚拟电厂
- `energy_storage_theme` 新型储能
- `gas_station_transition_theme` 加油站转型
- `equipment_renewal_theme` 以旧换新
- `green_power_trading_theme` 绿电交易

#### 关系层(`1_extracted/relations/`)

| 关系类型 | 边数 | 反链覆盖 target 数 | 含义 |
|---|:-:|:-:|---|
| supersedes | **2** | 2 | 显式废止 |
| iterates | **12** | 11 | 版本升级(年度续作) |
| extends | **8** | 4 | 范围扩展 |
| clarifies | **46** | 17 | 实施细化 |
| references | **172** | 57 | 文号 + 标题引用 |
| aligns_with | **4** | 4 | 同向对齐 |
| **conflicts_with** | **0** ⚠️ | 0 | 口径冲突(见 §4 caveat) |
| **cites_basis** | **54** ⭐ | 22 | 制定依据(月报最强数据源) |
| **总边数** | **298** | — | |

**反链页**:`1_extracted/relations/_index_by_policy/<P_id>.md` 共 71 个,自动维护,Obsidian wikilink 跳转。

**演进差异**:`1_extracted/diffs/<new>__from__<old>.md` 共 22 个(本月补齐),每个含维度差异表 + 滴滴三业务影响 + 行动建议。**月报"演进对比"段落直接用这些。**

#### 评论观点(`1_extracted/opinions/`)

- **54 个 policy 舆论矩阵**(共识/分歧/中性观察/待跟进)
- 覆盖率仅 **20.5%**(54/263)⚠️
- 数据稀疏根因:大部分 commentary 是 reposted_original/news_report,无 stance
- **月报怎么用**:有 opinion 的 54 个政策可写"业界观点矩阵";其余必须**诚实标注 "数据未覆盖"**,不能凭空编

#### 主题结晶(`2_crystallized/themes/`)8 个主题

| 主题目录 | 政策数 | opinion 覆盖 | 备注 |
|---|:-:|:-:|---|
| `V2G/` | (旧建,未重抽) | — | 蓝本主题 |
| `CHARGING_INFRA/` | (旧建) | — | 蓝本主题 |
| `POWER_MARKET/` | (旧建) | — | 蓝本主题 |
| `VPP_THEME/`(新) | 73 | 22 (30%) | 山东 fact-check 必需 |
| `ENERGY_STORAGE_THEME/`(新) | 79 | 21 (27%) | |
| `GAS_STATION_TRANSITION_THEME/`(新) | 25 | **1 (4%)** ⚠️ | opinions-summary 标 data_sparsity:severe |
| `EQUIPMENT_RENEWAL_THEME/`(新) | 84 | 11 (13%) | 关系入度最高 |
| `GREEN_POWER_TRADING_THEME/`(新) | 45 | 15 (33%) | |

每个主题目录 4 件套:
- `overview.md` — 主题界定 / Top 10 关键政策 / 时间脉络 / 滴滴三业务影响
- `timeline.md` — 国家级 → 省级 → 地市 时间线
- `regional-coverage.md` — 区域覆盖矩阵 + 空白发现
- `opinions-summary.md` — 业界观点(strict 模式,带覆盖率标注 + 未覆盖政策清单)

**月报怎么用**:这 8 个主题是月报"按主题汇总"段落的直接素材。

#### 区域索引(`2_crystallized/regions/`)9 个

上海市(25 篇) / 重庆市(21) / 北京市(20) / 福建省(6) / 湖南省(4) / 深圳市(4) / 辽宁省(3) / 吉林省(3) / 山东省(3)

**月报怎么用**:"按地域分布"段落 + 跨省比较直接用这些索引页。

#### 全局仪表盘(`2_crystallized/_global_index.md`)

顶层数据快照,月报开篇"数据规模"段落可直接引用。

### L3 报告层(已有资产,这是你的工作主场)

#### 蓝本

- **`00 背景资料/策略-L3月报需求原型.md`**(286 行,**唯一规范**)
  - 月报章节结构(8 节)
  - 双格式(Word docx + HTML 单文件)同源数据
  - 政策选取规则(重要性阈值 / 主题分布 / 影响维度)
  - 比较级论断的诚实标注规则(防 LLM 幻觉)

#### 已跑通的脚本(2026-03 月报实战留下的)

| 脚本 | 用途 |
|---|---|
| `_meta/scripts/gen_march_dryrun.py` | 生成月报 dry-run JSON |
| `_meta/scripts/prep_docx_data.py` | 准备 docx 渲染数据 |
| `_meta/scripts/render_docx.js` | 渲染 .docx(node.js) |
| `_meta/scripts/render_html.py` | 渲染 HTML 单文件 |
| `_meta/scripts/render_march_charts.py` | 渲染图表 |

#### 已有中间数据(2026-03 月报留下的参考样本)

```
_meta/march_report_dryrun.json          # 整月 dryrun 数据
_meta/march_report_batches/
├── march_detail.json                    # 详细政策清单
├── march_detail_result.jsonl            # LLM 处理结果
├── effective_all.jsonl                  # 全部 effective(已合并)
├── effective_batch_{1..5}.json          # 5 batches 输入
├── effective_result_{1..5}.jsonl        # 5 batches LLM 输出
├── _consolidated.json                   # 合并后数据
├── _docx_data.json                      # docx 渲染数据
└── charts/                              # 图表中间文件
```

**月报最终产物**(.docx / .html)未在 git 里(可能在你前任电脑上)。需要重新跑或直接看 `_docx_data.json` 内容理解 v6 长什么样。

---

## 3. 建议实战路径(第一周)

按风险递增:

### 选项 A — 先 reproduce 2026-03 v6(推荐第一步,2 天)

1. 跑 `gen_march_dryrun.py` 重新生成 march dryrun
2. 对比 `_meta/march_report_dryrun.json` 看是否一致(数据有变化是预期 — A 类清理后)
3. 跑 `prep_docx_data.py` + `render_docx.js`,出 march v6 重制版
4. 人工读一遍,记录现在 v6 哪些段落因 L2 数据更新而失真 / 改善

**目的**:熟悉 pipeline + 触底所有脚本 + 知道 v6 的"原貌"。

### 选项 B — 跑 2026-04 月报 v1(本月主菜,2-3 天)

按蓝本规范:
1. 改 `gen_march_dryrun.py` → `gen_april_dryrun.py`(参数化月份)
2. 跑全 pipeline 出 v1
3. 4 维诚实标注 self-review(对照蓝本 §5/§6/§7 章节规范)
4. 出 v1 → v2 → v3 迭代到可发布(参考 v6 经验值)

### 选项 C — 模板化(让 5/6 月可跑,1-2 天)

把 `gen_march_dryrun.py` 重构成 `gen_monthly.py --month YYYY-MM`,所有月份都用同一脚本。

---

## 4. ⚠️ 已知数据局限(月报必须诚实标注)

按局限严重度排序:

### 严重(直接限制论断范围)

1. **opinions 覆盖率仅 20.5%**(54/263)
   - 影响:月报"业界观点矩阵"只能覆盖这 54 篇
   - 应对:章节开头标"基于 N 篇有舆论数据的政策" + 列空白政策清单
   - **绝不允许**:对未覆盖政策编造观点

2. **conflicts_with = 0 条**
   - 影响:月报"风险维度 / 部委口径冲突"无数据支撑
   - 根因诊断:body_500 不够判,真冲突在 commentary critical stance / 执行层面
   - 应对:本月跳过这维度 OR 用 `1_extracted/relations/_summary_conflicts_round1.md` 里 161 候选 + 8 aligns 反推"潜在张力"
   - 留下一轮 skill session 二轮扩 body_3000 + commentary stance 反推

3. **加油站转型主题 opinion 覆盖仅 4%**(1/25)
   - `2_crystallized/themes/GAS_STATION_TRANSITION_THEME/opinions-summary.md` 已标 `data_sparsity: severe`
   - 影响:加油业务专题段落业界观点几乎空白
   - 应对:照实陈述,作为 L3 反推 L1 commentary 补采集需求的证据

### 中等(部分论断需弱化)

4. **issuer 标准化 87.9% 命中**:35 篇低频地级市机构未命中(在 `_meta/issuer_review_queue.yaml`)
   - 影响:跨省 issuer 统计可能微偏(<5%)
   - 应对:月报"按发文方"段落用 `issuer_canonical` 字段,空值的政策另列"其他"组

5. **A 类残余 12 篇政策解读未移**(模糊 + audit 漏 catch)
   - 影响:政策时间线可能混入解读文章
   - 应对:月报选取规则加白名单过滤"标题不含 解读/答记者问/署名/转载"

6. **diffs 22 个但部分 confidence ≤0.7**(尤其 PDF 二进制 / 门户导航截断的)
   - 影响:演进对比段落部分维度可能粗
   - 应对:月报展示 diff 时带 confidence,低 conf 标"待原文核对"

### 轻微(可接受)

7. **references title_match 86 条新边** confidence 0.8(未经 LLM 进一步 judge)
   - 应对:仅用作"提及网络",不作为 cites_basis 严格依据

8. **关系网密度 4.32 ‰** 偏稀疏(政策树形演进特征,不是 bug)
   - 应对:月报不做"全局密度"论断

---

## 5. 跨 session 协作约定

### 何时回来找 skill session

> 用户在 skill session 那边持续做 superpowers skill 建设。你这边遇到下面情况之一才打扰:

1. L1 数据缺陷阻塞月报(如某关键政策未采集到)→ 写 spec 追到 `docs/handoffs/back-to-skill-session.md`
2. L2 抽取出错(如某条 cites_basis 显然错抓)→ 同上
3. 发现新的 schema 升级需求(如月报需要新字段)→ 同上
4. 你想跑 LLM(用 subagent 即可,你自己有这个能力)

### 何时不打扰

1. 月报内容编排 / 章节顺序调整 / 论断措辞 → 你独立决策
2. 跑 render_docx.js / render_html.py / 改图表样式 → 你自己上
3. dryrun JSON 数据格式微调 → 你自己上
4. 发现轻微数据局限(见 §4)→ 标"诚实告知"继续推进,不必停下

### 数据流约定

- **只读**:`0_raw/` `1_extracted/` `2_crystallized/`
- **读写**:`_meta/april_report_*` / `2_crystallized/_reports/2026-04/`(创建)
- **不动**:`_meta/scripts/extract_*` `_meta/scripts/build_*`(L1/L2 抽取脚本)
- **可改**:`_meta/scripts/gen_*report*` `_meta/scripts/prep_*` `_meta/scripts/render_*`(L3 自己的)

### git 提交风格

- `feat(L3): april report v1 完整 pipeline`
- `chore(L3): 改 docx 模板字号`
- `docs(L3): april report 实战日记`

不要在你的 commit 里改 L1/L2 文件。如果必须改(比如 L2 的某个数据 typo),先在 `docs/handoffs/back-to-skill-session.md` 追一条,让 skill session 在他的 commit 里改。

---

## 6. 第一周 checklist

```
[ ] Day 1 上午:读 §1 的 4 个文件 + 本 handoff(2-3 小时)
[ ] Day 1 下午:跑 gen_march_dryrun.py 重生成 march dryrun + 对比差异
[ ] Day 2:跑全 march pipeline 出 v6 重制版,记录 L2 数据更新对 v6 论断的影响
[ ] Day 3:基于蓝本 + v6 经验,设计 april v1 数据流(可能需要新建 gen_april_dryrun.py)
[ ] Day 4:出 april v1 → 4 维 self-review → v2
[ ] Day 5:v2 → v3 迭代到可发布
[ ] Day 6:模板化(选项 C)+ 写实战日记
[ ] Day 7:回顾 + 给 skill session 反馈"L2 数据哪些段落最需要扩"
```

---

## 7. 关键文件路径速查表

```
# 蓝本
/Users/shaoziyuan/Documents/Zayn Main/政策分析/00 背景资料/策略-L3月报需求原型.md
/Users/shaoziyuan/Documents/Zayn Main/政策分析/00 背景资料/滴滴能源-政策分析背景.md
/Users/shaoziyuan/Documents/Zayn Main/政策分析/00 背景资料/政策重要性打分体系.md

# schema(必要时翻)
/Users/shaoziyuan/Documents/Zayn Main/政策分析/_meta/schema_v3.md

# 已跑通脚本
/Users/shaoziyuan/Documents/Zayn Main/政策分析/_meta/scripts/gen_march_dryrun.py
/Users/shaoziyuan/Documents/Zayn Main/政策分析/_meta/scripts/prep_docx_data.py
/Users/shaoziyuan/Documents/Zayn Main/政策分析/_meta/scripts/render_docx.js
/Users/shaoziyuan/Documents/Zayn Main/政策分析/_meta/scripts/render_html.py
/Users/shaoziyuan/Documents/Zayn Main/政策分析/_meta/scripts/render_march_charts.py

# 数据底座
/Users/shaoziyuan/Documents/Zayn Main/政策分析/2_crystallized/_global_index.md   # 仪表盘
/Users/shaoziyuan/Documents/Zayn Main/政策分析/2_crystallized/themes/             # 8 主题
/Users/shaoziyuan/Documents/Zayn Main/政策分析/2_crystallized/regions/            # 9 区域
/Users/shaoziyuan/Documents/Zayn Main/政策分析/1_extracted/diffs/                 # 22 演进差异
/Users/shaoziyuan/Documents/Zayn Main/政策分析/1_extracted/opinions/              # 54 政策舆论矩阵
/Users/shaoziyuan/Documents/Zayn Main/政策分析/1_extracted/relations/_index_by_policy/  # 71 反链页

# 历史迭代
/Users/shaoziyuan/Documents/Zayn Main/政策分析/_meta/march_report_dryrun.json
/Users/shaoziyuan/Documents/Zayn Main/政策分析/_meta/march_report_batches/

# lint(每天跑一次,确保数据干净)
/Users/shaoziyuan/Documents/Zayn Main/政策分析/_meta/scripts/daily_lint.py
/Users/shaoziyuan/Documents/Zayn Main/政策分析/3_lints/daily/
```

---

## 8. 跑通环境检查(Day 1 第一件事)

```bash
cd "/Users/shaoziyuan/Documents/Zayn Main/政策分析"

# 1. python deps
python3 -c "import yaml, json; print('OK')"

# 2. node(给 render_docx.js 用)
node --version

# 3. lint 通过(确认数据干净)
python3 _meta/scripts/daily_lint.py

# 4. 验证 8 主题 4 件套都齐
for d in 2_crystallized/themes/*/; do
  echo "$d  $(ls "$d"/*.md 2>/dev/null | wc -l) files"
done

# 5. 验证关系数据
wc -l 1_extracted/relations/*.jsonl
```

应得:
- daily_lint exit 0(0 errors / 0 warnings)
- 每 theme 目录 ≥4 个 .md(overview/timeline/regional-coverage/opinions-summary)
- supersedes:2 / iterates:12 / extends:8 / clarifies:46 / references:172 / aligns_with:4 / conflicts_with:0 / cites_basis:54

---

## 9. 最近 git 历史(本月本知识库的所有 commit)

```
1161ed0 docs: 2026-04-28 终篇日记
a598516 feat(L2/L3): 派生层补全 — regions / _global_index / daily_lint
1194c2d chore(L2): conflicts_with 第一轮归档 — 0 conflicts / 161 候选
8ae4804 feat(L2): diffs 补跑 13 + 删 4 孤儿 → 22 全齐
8895d3c feat(L2): 关系层信号召回率优化 + 反链重建
eac1027 chore(L1): A 类 26 篇政策解读重分类 → commentaries
cd153e8 docs: 2026-04-28 下半场日记
1a263cc feat(L2): 5 主题结晶页 — 业务覆盖补全
4507022 feat(L2): registry.yaml 加 5 个 type=theme 实体
32d6027 chore(L1): issuer 标准化 + 6 region 补全
cd0c447 docs(spec): L1 地基整改 + L2 themes 业务覆盖补全 设计文档
804364d docs: 2026-04-28 dev journal — P0-2 v2 重抽追写
2852660 feat(L2): supersedes/iterates v2 重抽 — 多源融合 + LLM 判定
fe12bdb chore(L0): cleanup pass 2 — inline 删除 firecrawl 标记
d700863 feat(L2): B 阶段反链层 _index_by_policy/ 全量生成
2ae3ea7 chore(L0): 清理 firecrawl 抓取残留装饰污染 1880 行
235f0ca feat(L2): 加 cites_basis 第 8 类 typed relation
53b7def docs: 2026-04-27 dev journal — L3 蓝本完成 + handoff
5390fc5 init: L1 collection + L2 wiki v3 + L3 monthly report prototype
```

---

## 10. 最后:你不必怕

- 数据底座**完整且诚实**(每个主题/政策都有 confidence + 覆盖率标注)
- 蓝本规范**经过 v1→v6 实战验证**,不是纸面理论
- 5 个 render 脚本**跑得通**(2026-03 已实战)
- 局限性已**全部摆出来**(§4),你按"诚实标注"原则推就稳

遇到拿不准的措辞 / 章节取舍,**优先按 v6 模式**,不要自己发明。
有真不会判的,在 `docs/handoffs/back-to-skill-session.md` 追问,不要硬猜。

加油 — 月报是这整个三层架构的**唯一对外产出**,你做得好,L1+L2 才有意义。
