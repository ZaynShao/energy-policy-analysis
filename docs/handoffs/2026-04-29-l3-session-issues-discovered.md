---
date: 2026-04-29
source_session: L3 月报实战 session(2026-04-28 ~ 2026-04-29)
target_session: skill 建设 session
purpose: 整合本 session 在 reproduce 2026-03 v6 + 起草 2026-04 月刊过程中陆续发现的 vault 系统性问题,交回 skill 建设 session 自行排期与判断
status: 仅描述问题与证据,**不含解决建议**(用户要求)
supersedes: docs/handoffs/back-to-skill-session.md(原 3 条已并入)
issue_count: 16
---

# vault 系统性问题清单 — L3 实战 session 发现

## 阅读说明

本文档每条问题独立成段,含:**编号 · 标题 · 触发场景 · 证据(file:line)· 范围 · 严重度**。按"根因深度"分组,从最深(SOP 蓝本)到最浅(单脚本输出)。同根因的问题会标注关联条目编号。

严重度:🔴 P0 / 🟡 P1 / 🟢 P2

不写修复路径,由 skill 建设 session 判断。

---

## A. SOP 蓝本与数据架构层(根因最深)

### A1 · 八步采集法 SOP 把 L2 业务判断列为 L1 入库必须项

**触发**:追溯月刊 §三(三) 山东 VPP "山东是公司电力业务的首批可落地省份" 一句的来源

**证据**:
- `00 背景资料/策略-八步采集法.md:271`:
  > | 初步影响分析(D1/D2 参考) | — | ✅ 必须 | 分业务三段:加油/充电/电力 |
- 八步采集法 Step 5(打分 + 入库)绑定执行:抓原文 + 写 ## 摘要 + 写 ## 初步影响分析 + 写 ## 六维评分 + frontmatter 加 scores/重要性/行动分类/价值标签 + 入库 — **全部塞进 0_raw/policies/{文件}.md 一份文件**
- 反向证据:无任何脚本写 `0_raw/policies/`(grep 27 个 `_meta/scripts/*.py *.js` 文件 0 命中目录写操作,0 命中"初步影响分析"字符串)
- git log 显示典型 L1 文件就 1-2 个 commit(init + 偶尔字段标准化)— 没有"事后污染"过程

**含义**:0_raw/ 命名暗示 raw source,但 SOP 设计层把 L2 派生判断与 L1 raw 政策原文合并存储,违反 L1 = raw source 原则。

**范围**:263 篇全量 L1 政策文件均按此 SOP 入库

**严重度**:🔴 P0

**关联**:A2(具体表现)、A3(同源数据污染)

---

### A2 · L1 政策原文 frontmatter / body 含品牌名 + 业务策略判断

**触发**:A1 在具体政策文件上的表现 — sanitize 月刊时 grep `滴滴`

**证据**(典型样本):
- `0_raw/policies/【山东省促进虚拟电厂高质量发展方案】-山东省能源局-1ffc.md:56`:
  > **电力业务**: 山东是滴滴电力业务首批可落地省份,本方案为商业模式落地提供操作依据
- 同类污染至少 14 篇(grep `滴滴` 在 `0_raw/policies/`):
  - 国务院《全国统一电力市场体系实施意见》(...e389.md:56):「滴滴电力业务**全国扩展**的最高层级政策依据」
  - 上海经信委 407 号(...5d8d.md:65):「为**滴滴电力业务**在沪发展提供量化空间」
  - NEA《新能源消纳和调控指导意见》1360 号(...7280.md:63):「为**滴滴电力业务**长期发展提供完整顶层路径」
  - 广州车网互动 255 号、深圳碳达峰试点、电力辅助服务市场基本规则、电力中长期市场规则、新能源集成融合发展指导意见、加强电网调峰储能...等共 14+ 篇

**含义**:
- 业务策略判断(「首批可落地」「全国扩展依据」「市场化收益路径」)与品牌名「滴滴」沉淀进政策原文层
- L3 月刊「重点关注」段直接复制 L1 内嵌业务判断,等于把 L1 文本升级为公司决策建议(责任归属模糊)
- 数据外泄风险:vault 一旦备份/共享/审计,直接暴露公司业务规划

**范围**:`0_raw/policies/` 至少 14 篇命中"滴滴";完整 audit 范围未做

**严重度**:🔴 P0

**关联**:A1(根因)

---

### A3 · vault 上海政策标题/文号/来源 URL 字段混淆错抓

**触发**:月刊 fact-check 山东 VPP 是否为「NDRC 357 后省级首批」时,独立 web 核查发现

**证据**:
- vault 现有 `0_raw/policies/【上海市用户侧虚拟电厂建设实施方案(2025-2027年)(沪经信运〔2025〕407号)】...5d8d.md`:文件名/frontmatter 标题之间字段已对齐
- 但 L3 蓝本 `00 背景资料/策略-L3月报需求原型.md:138` fact-check 反例引用为「上海市虚拟电厂**高质量发展实施方案** SH_407(2025-06)」 — 该标题对应**另一份不同的文件**:
  - 真份①:**2024-07** 上海市发改委《上海市虚拟电厂**高质量发展工作方案**》(fgw.sh.gov.cn 链接) — **早于 NDRC 357 9 个月**
  - 真份②:**2025-06-23** 上海市经信委《上海市**用户侧**虚拟电厂建设实施方案(2025-2027 年)》(沪经信运〔2025〕407 号,sheitc.sh.gov.cn 链接) — 晚于 NDRC 357

- 蓝本 §5.1 把"标题 ① 高质量发展工作方案"和"日期文号 ② 沪经信运 407"硬合并为单一指代

**含义**:L1 采集"标题 vs 文号 vs 来源 URL"未做交叉校验;L3 蓝本反例基于这种混淆数据建立

**范围**:已确认 1 处(蓝本 §5.1);其他类似混淆需 audit

**严重度**:🟡 P1

---

## B. L2 派生层

### B1 · entity 抽取产物 `_extractions.jsonl` 缺 theme 关联

**触发**:reproduce 2026-03 v6 时检查 `_docx_data.json` 发现 `theme_coverage` 5 主题全部 covered=0/blank=0(空)

**证据**:
- `_meta/march_report_batches/_docx_data.json`:`theme_coverage = {"V2G/车网": {covered: 0, blank: 0}, ...}` 全空
- `_meta/scripts/prep_docx_data.py` 通过 `theme_id in policy_entities[pid]` 判断政策↔主题归属,但 `1_extracted/entities/_extractions.jsonl` 里 policy 行没有 themes 字段
- 反向:本月 L2 已在 `entities/registry.yaml` 加 5 个 type=theme 实体(VPP/ESS/GAS/ER/GREEN),但 `_extractions.jsonl` 未同步重抽加 theme 关联字段

**含义**:月刊 §7 主题×31 省份缺口矩阵渲染为空表;蓝本 §3 §7 是核心章节

**范围**:全量 263 篇 policy 实体行

**严重度**:🟡 P1

---

### B2 · `prep_docx_data.py` 未做 linkage_type 蓝本 §6.3 重映射

**触发**:检查 `_docx_data.json.deep_dive_witnesses[*].linkage_type` 字段值

**证据**:
- `_docx_data.json` linkage_type 出现频次:`Counter({'主题对应*': 6, '借鉴框架': 3})`
- `00 背景资料/策略-L3月报需求原型.md` §6.3 要求 prep 阶段重映射:
  - 直接落地 → 直接落地
  - 借鉴框架 → 补充细化
  - 主题对应 → 同向部署
- `_meta/scripts/prep_docx_data.py` 未实现这个 sanitize

**含义**:月刊 §5 落地证据表 linkage 列显示旧术语,违反蓝本

**范围**:9 条 linkage 证据(本月 march dryrun);后续每月可能复发

**严重度**:🟢 P2

---

### B3 · L2 关系层未覆盖 4-12 之后入库的政策

**触发**:月刊起草时查 ⭐≥4 三篇 4 月新政的 cites_basis / references / 反链页

**证据**:
- 山东消纳方案(P_2026_SD_0401ca27)、碳达峰考核办法(P_2026_CCGO_041241d4)、节能降碳意见(漏抓,A4)— 三篇都没有反链页(`_index_by_policy/{pid}.md` 不存在)
- L2 关系层 cites_basis / references 抽取批次截止日早于 4-12

**含义**:月刊关联表只能手动梳理,无法用 L2 自动产物

**范围**:4-12 之后入库政策(约 4-5 篇)

**严重度**:🟡 P1

---

### B4 · `_extractions.jsonl` 引用孤儿 pid

**触发**:reproduce 时跑 `gen_march_dryrun.py` 报 `KeyError: 'P_2024_OTHERD347_052923d9'`

**证据**:
- `_extractions.jsonl` 里 `policy_entities` 字典含 pid `P_2024_OTHERD347_052923d9`
- 但该 pid 不在 `0_raw/policies/` 目录(已被 A 类清理 / dedup 删除,见 git log `eac1027 chore(L1): A 类 26 篇政策解读重分类 → commentaries`)
- entity 抽取产物未在 A 类清理后同步重抽

**含义**:任何下游脚本遍历 `_extractions.jsonl` 后访问 `0_raw/policies/{pid}` 都会 KeyError(L3 已就地加防御性 skip,但根因在 L2)

**范围**:已暴露 1 个孤儿;完整 audit 未做

**严重度**:🟢 P2

---

## C. L3 渲染/工具层

### C1 · `prep_docx_data.py` theme 列表硬编码与 L2 registry 不同步

**触发**:reproduce v6 时检查 theme_coverage 字段

**证据**:
- prep 硬编码 5 主题:V2G / 电力市场 / 充电基建 / 新型储能 / 设备更新
- L2 本月新加 5 个 type=theme 实体:VPP / ENERGY_STORAGE / GAS_STATION_TRANSITION / EQUIPMENT_RENEWAL / GREEN_POWER_TRADING
- 重叠仅 2 个(ESS、ER);prep 完全不读 VPP / GAS / GREEN

**含义**:月刊 §7 主题覆盖矩阵缺失新主题维度

**范围**:`_meta/scripts/prep_docx_data.py` + `_meta/scripts/gen_march_dryrun.py`

**严重度**:🟡 P1

**关联**:B1(同根)

---

### C2 · `prep_docx_data.py` 输出陈旧的 `data_health` 字段

**触发**:reproduce v6 时检查 `_docx_data.json.data_health`

**证据**:
- 当前输出:vault_policies=263 ✓ / entity_canonical=88(实际 94)/ relations_total=198(实际 298)/ crystallized_themes=3(实际 8)/ lint_errors=1(实际 0)
- 蓝本 §3 已把"数据健康度小卡"列为淘汰章节,但 prep 仍生成

**含义**:渲染端若引用此字段,数字与现实不符;且字段本身违反蓝本

**范围**:`prep_docx_data.py` + 任何 renderer 引用 `data.data_health`

**严重度**:🟢 P2

---

### C3 · `render_march_charts.py` 字体链不含 ⭐ glyph

**触发**:reproduce v6 跑 charts 时 6 处 UserWarning

**证据**:
- 警告 `Glyph 11088 (\N{WHITE MEDIUM STAR}) missing from font(s) STHeiti`
- 字体链当前是 STHeiti / PingFang(蓝本 §7),但二者均不含 ⭐ Unicode glyph
- 蓝本 §4.4 emoji 规则保留 ⭐ 用于评分体系,所以是要展示的;chart 里 ⭐ 渲染成方框

**含义**:chart 视觉降级

**范围**:01_timeline.png、02_2x2_matrix.png、04_evolution_chain.png 含 ⭐ 的图

**严重度**:🟢 P2

---

### C4 · `gen_march_dryrun.py` 章节目录是 v1 时期(蓝本已淘汰)

**触发**:reproduce v6 dryrun.md 输出

**证据**:
- 输出 `~/Desktop/能源政策月报-2026-03-DRYRUN.md` 目录(L14-31)含「§6 舆论温度计」「§10 数据健康度小卡」「§C 数据出处与方法论」
- 蓝本 §3「禁用章节(已淘汰)」明确这 3 节已淘汰
- gen_march_dryrun 是 v1 期脚本,未随蓝本升级而调整

**含义**:dryrun 骨架预览与 v6 真实月报章节结构不一致(但 dryrun 仅用于内部预览,不直接影响交付)

**范围**:`_meta/scripts/gen_march_dryrun.py`

**严重度**:🟢 P2

---

## D. L1 采集层与蓝本规则

### D1 · L1 commentaries 全量来自政府/央媒,无 mp.weixin 公众号独立评论

**触发**:起草 4 月月刊「§三(一) §三(二) 政策解读」段,启发式筛 commentary 找独立观点

**证据**:
- 启发式筛(host=mp.weixin OR source_type∈{B,C}AND not gov AND conf≥0.8 AND 主题命中{节能降碳/碳达峰/虚拟电厂/消纳/绿电/电力市场/储能/充电})49 篇候选
- 49 篇全部 host 为 ndrc.gov.cn / mee.gov.cn / cctv.com / people.com.cn / nea.gov.cn / 各省政府门户
- 0 篇 mp.weixin.qq.com

**含义**:vault commentary 实际是"政策原文/官方解读再转载",不是独立观点矩阵;月刊「业界观点」段几乎无可用引用源

**范围**:360 篇 commentaries 全量

**严重度**:🟡 P1

---

### D2 · 节能降碳意见(2026-04-24,中办国办)L1 漏抓

**触发**:WebSearch 4 月国家级政策时发现

**证据**:
- 4 月最重磅政策《关于更高水平更高质量做好节能降碳工作的意见》(中办国办联合,2026-04-24 发布)
- vault `0_raw/policies/` 0 篇此文件;`grep "节能降碳"` 命中的是 2023 年发改环资〔2023〕178 号(早期文件)
- 月刊本期通过 web fetch 获得文本要点完成分析,实际未入库

**含义**:本月最高规格政策未入 vault,影响后续 L2 关系层抽取与未来月报追溯

**范围**:1 篇(高规格 ⭐5)

**严重度**:🔴 P0

---

### D3 · 会议讲话级信号未在 L1 8 步采集法覆盖范围

**触发**:WebSearch 4 月信号时发现

**证据**:
- 国务院 2026-04-20 第十九次专题学习「统筹能源安全和绿色低碳转型」(总理主持)
- 国家能源局电力司 2026-04-27 司长发言(算电协同纳入十五五、VPP 全国 470 个/1685 万千瓦、民营企业占比过半)
- 两类「会议讲话级信号」`0_raw/policies/` 与 `0_raw/commentaries/` 均无入库
- `策略-八步采集法.md` Step 1-3「政策发现」未列入这两类来源(政府工作会议、领导讲话)

**含义**:月刊战略基调与领导信号段需 web 实时补漏

**范围**:每月数次会议/讲话信号

**严重度**:🟡 P1

---

### D4 · L3 蓝本 §5.1 fact-check 反例本身基于不全的信息

**触发**:月刊 fact-check 山东 VPP "省级首批" 时 web 跨数据源核查

**证据**:
- 蓝本 `00 背景资料/策略-L3月报需求原型.md:138`:
  > **反例(本轮已修正):** 山东 VPP 方案 3-27 不是 NDRC 357 后省级首批 — 上海 SH_407(2025-06)早 9 个月。山东实际是第 2 个,前序应注明。
- web 跨数据源核查后实际(2025-04-11 NDRC 357 至 2026-03-26 山东方案之间):
  - 浙江 2025-05《浙江省虚拟电厂运营管理细则(试行)》
  - 上海经信委 2025-06《上海市用户侧虚拟电厂建设实施方案(2025-2027 年)》(沪经信运〔2025〕407 号)
  - 广州市工信局 2025-08《广州市虚拟电厂高质量发展实施方案》
  - 深圳虚拟电厂可调负荷已达 310 万千瓦(实操早于方案,文件时间待考)
  - 山东实际是第 3-4 个,不是第 2 个

**含义**:蓝本 §5.1 把"防 LLM 幻觉"的反例本身写错了;蓝本规则未强制"web 跨数据源核查"作为比较级声明前置必经流程,导致 fact-check 流程仍可能基于 vault grep 的有限信息

**范围**:蓝本 §5.1 反例 + 月刊 §5 落地证据 fact-check 路径

**严重度**:🟡 P1

**关联**:A3(同根 — 上海政策字段混淆)

---

## 根因关系层(事实陈述,不是修复建议)

```
A1 (SOP 设计违反 L1 raw 原则)
  └── A2 (L1 政策原文含品牌名 + 业务判断 14+ 篇)
  └── (隐性)所有"按 SOP 入库"的 263 篇都受影响

A3 (上海政策字段混淆)
  └── D4 (蓝本 §5.1 fact-check 反例不完整 — 沿用 A3 的混淆数据)

B1 (entity 缺 theme 关联)
  └── C1 (prep theme 列表硬编码与 L2 不同步)
  └── 月刊 §7 主题覆盖矩阵空

D2 / D3 (L1 漏抓 4-24 节能降碳意见 + 会议讲话信号)
  └── 间接导致 D1 (commentary 也无相关公众号评论可采)

C2 (data_health 陈旧)、C3 (chart ⭐ 缺字体)、C4 (dryrun 章节 v1)
  └── 互相独立,都是 L3 工具层的局部问题
```

---

## 本 session 已就地处理的项

仅记录,不需 skill session 重做:

- `_meta/scripts/gen_march_dryrun.py:122` 加防御性 `if pid not in all_p: continue`(对应 B4)— L3 自家脚本,handoff §5 数据流约定允许
- 月刊 v2 山东 VPP "重点关注" 段已重写为基于政策本身的判断,移除对 A2 内容的直接引用
- `00 背景资料/滴滴能源-政策分析背景.md` 加油业务段加了「不关注方向」澄清,以减少未来分析重复 A2 类污染

---

## 备注

- 本 session 不直接动 0_raw/、1_extracted/、2_crystallized/themes 等 vault 数据(handoff §5 数据流约定);所有问题原样移交
- 严重度仅本 session 视角的初判,skill session 自行重新评估
- 修复路径完全交回 skill session 判断 — 因为 A1 涉及 SOP 蓝本改写、A2 涉及 14+ 篇 L1 数据迁移,触及 vault 设计基线,不是单 session 能定夺
