---
title: 政策分析 L2 知识图谱 schema v3
version: 3.0
date: 2026-04-25
supersedes: 00 背景资料/schema/政策分析-领域schema.md (v2)
status: active
---

# 政策分析-领域 Schema v3

> 架构哲学:**Karpathy LLM Wiki v2 思想 + 三层分离**
> 服务对象:滴滴能源决策层(参见 [[滴滴能源-政策分析背景]])
> 上承 L1(`策略-八步采集法.md`),下接 L3(`policy-report` skill,未实施)

---

## 0. 设计哲学

1. **raw 永远是 source of truth**:289 政策 + 338 评论是底座,所有派生品(实体页/关系/主题/大盘)都能从 raw 全量重建。raw 不写关系字段,关系外置到 1_extracted/。
2. **canonical 优先**:每个实体只能有一个 canonical id,所有别名归并到它。**抽取阶段就规范化**,而不是事后去重(避免 backup v2 那种"充电运营商"出现 7-8 个变体的痼疾)。
3. **observation 分层**:政策正文里的"事实"(fact)和评论里的"观点"(opinion / stance)是两类东西,schema 严格分清。

---

## 1. 三层目录结构

| 层 | 路径 | 性质 | 谁能写 |
|---|------|-----|--------|
| L0 raw | `0_raw/` | 唯一真相源 | L1 policy-watch skill 写入 / 人工允许校正 |
| L1 extracted | `1_extracted/` | 机器派生中间产物 | 派生管道全权 / **禁止手改** |
| L2 crystallized | `2_crystallized/` | 给人看的结晶页 | 派生管道生成 / 允许人工 polish |
| Lint | `3_lints/` | 健康检查报告 | lint 任务自动写 |
| Meta | `_meta/` | schema / 管道 / 全局日志 | 人工维护 |

**全量重建口令**(将来):`policy-rebuild --from raw` 把 1_extracted 与 2_crystallized 全删重跑。

---

## 2. 实体类型(Node Types)

5 类核心实体,统一注册在 `1_extracted/entities/registry.yaml`:

| type | 含义 | 例子 |
|------|------|------|
| `org` | 政策的发文/监管机构 | 国家发改委、国家能源局、北京市发改委 |
| `stakeholder` | 受政策影响的群体/企业角色 | 充电基础设施运营商、负荷聚合商、电网企业 |
| `concept` | 业务/技术概念 | V2G、虚拟电厂、需求响应、绿证 |
| `theme` | 政策主题(用于结晶页聚合) | 充电基建、电力市场、设备更新、储能 |
| `region` | 行政区划(独立实体) | 北京市(110000)、广东省(440000)、深圳市(440300) |

实体可以多 type(如"国家电网" 既是 `org` 又是 `stakeholder`),registry 字段 `type: [...]` 接数组。

---

## 3. Canonical Entity Registry

### 3.1 文件位置

`1_extracted/entities/registry.yaml`(单一文件,版本受控,**所有实体名归这里管**)。

### 3.2 条目格式

```yaml
- id: charging_operator                        # 唯一,小写下划线
  canonical_name: 充电基础设施运营商                # 标准名(中文)
  type: [stakeholder]                          # 单值或数组
  parent: new_energy_service_provider          # 上位实体 id(可选)
  aliases:
    - 充电运营商
    - 充电站运营商
    - 充电_换电基础设施运营商
    - 充电桩、储能、虚拟电厂运营商
    - 充电桩_虚拟电厂_储能等新业态运营商
  examples: [滴滴能源, 特来电, 星星充电, 国家电网]    # 具体公司
  desc: 直接运营充电桩 / 换电站 / 综合能源补给站的市场主体
  added_at: 2026-04-25
  added_by: registry_v0_init
  confidence: 0.95
```

### 3.3 抽取规则(强制)

| 阶段 | 规则 |
|------|------|
| 抽实体词 | LLM 抽完后**必须先匹配 aliases** |
| 命中 | 落 canonical id |
| 未命中 | 进 `_review_queue.yaml`,LLM 自判 confidence ≥ 0.85 自动进 registry,否则人工 review |
| 新词建页 | **不允许**,必须先入 registry |
| 别名重叠 | 同一别名不能归到两个 id(weekly lint 检查) |

### 3.4 实体页生成

`1_extracted/entities/<type>/<id>.md` 由 registry + 政策反链**自动派生**,不允许手写。

---

## 4. Policy(0_raw/policies/)frontmatter

锁死最小集 + provenance,**关系字段不写在这里**。

```yaml
---
# === 身份(必填) ===
id: P_2024_NDRC_718              # 派生主键: P_<year>_<issuer_short>_<num>
title: 关于推动车网互动规模化应用试点工作的通知
official_number: 发改办能源〔2024〕718号
issuer: [国家发展改革委, 国家能源局]    # 多机构联合发文用数组
date: 2024-01-05

# === 区域(必填) ===
region:
  level: 国家                     # 国家/省/市/区
  code: "000000"                # 行政区划代码;国家级用 000000
  name: 全国

# === 来源链(provenance) ===
provenance:
  url: https://www.ndrc.gov.cn/...
  source_type: A                # A 政府/B 媒体/C 公众号/D PDF
  fetched_via: firecrawl        # firecrawl / tavily+trafilatura
  fetched_at: 2026-04-25T09:02:14+08:00
  collected_by: policy-watch
  collected_mode: cron-daily    # cron-daily / url-intake / manual
  confidence: 0.95

# === 业务标签(L1 已抽,继承) ===
tags: [V2G, 充电基础设施, 试点]

# === 打分(L1 已抽,继承) ===
scores: {D1: 5, D2: 4, D3: 4, D4: 4, D5: 4, D6: 5}
重要性: 4
行动分类: A
价值标签: [合规, 机会, 壁垒]

# === archive 标记(可选,仅 <3 分) ===
archive: low_score
---
```

### 4.1 id 生成规则

```
P_<year>_<issuer_short>_<num>
```

- `<year>`:发布年(date 字段年份)
- `<issuer_short>`:首发机构英文缩写(NDRC=国家发改委,NEA=国家能源局,MIIT=工信部,MOF=财政部,MEE=生态环境部,MOHURD=住建部,STA=税务总局,SC=国务院,GO=国办,PBOC=人行,等;省级用 `BJ_DRC`/`SH_DRC` 等)
- `<num>`:文号尾号(无文号用日期 + 标题哈希前 4 位,如 `20240105_a3f5`)

碰撞处理:同年同机构同号 → 加 `_a` `_b` 后缀。

### 4.2 issuer 与 region 推导

- `issuer`:从 frontmatter `source` 字段拆,多机构联合发文时按原文顺序入数组
- `region`:从 issuer 第一项推断
  - 国家级机构(发改委/能源局/工信部 ...)→ `level: 国家, code: 000000`
  - "X 省 / X 自治区 / X 直辖市 ..." 前缀 → `level: 省, code: <2 位 + 0000>`
  - "X 市" 前缀且不在直辖市 → `level: 市`
  - "X 区" 前缀(京沪津渝下辖)→ `level: 区`

---

## 5. Commentary(0_raw/commentaries/)frontmatter

```yaml
---
id: C_2024_yyyy                  # C_<year>_<source_short>_<hash4>
type: commentary
source: 北极星售电网              # 公众号或媒体名
source_type: C                  # A/B/C/D
url: <原文URL>
date: 2024-01-08
related_policy: [P_2024_NDRC_718]   # 评论的政策(可多个)
provenance:
  fetched_via: firecrawl
  fetched_at: ...
  confidence: 0.7              # 权威号 0.9 / 行业媒体 0.7 / 匿名 0.5
---
```

观点(stance)**不写在 frontmatter**,由派生管道抽到 `1_extracted/opinions/<policy_id>.md`(见第 8 节)。

---

## 6. 政策 ↔ 政策 关系(8 类)

每类一份独立 jsonl,放在 `1_extracted/relations/<rel>.jsonl`。

| 关系 | 含义 | 抽取方式 |
|------|------|---------|
| `supersedes` | 显式废止("废止 X 文〔YYYY〕Z 号" / "X 文同时废止") | 正则文号引用 + LLM 验证 |
| `iterates` | 升级版/v2("在 X 文基础上修订" / 同一主题年度更新) | LLM 标题与摘要对比 |
| `extends` | 范围扩展(试点 → 全国 / 省级 → 国家级) | LLM + region 跳变检测 |
| `clarifies` | 实施细则/操作指引/解读 | 标题正则("X 实施细则 / X 操作指引 / X 解读")+ LLM |
| `references` | 引用但不修改 | 正则文号交叉引用 |
| `aligns_with` | 不同部门同主题对齐 | LLM + 主题向量相似度 |
| `conflicts_with` | 内容冲突(罕见但关键,如部委间口径差异) | LLM 仅扫高分政策对(成本控制) |
| `cites_basis` | 显式"作为制定依据"引用("根据 X 政策"/"依据 X 文件" 出现在政策开头段) | 位置过滤(references 子集 + 开头段) + LLM 语义判定 + 标题引用补漏 |

### 6.1 jsonl 行格式

```json
{
  "from": "P_2024_NDRC_718",
  "to":   "P_2022_NDRC_xxx",
  "rel":  "supersedes",
  "evidence": "原文第3段:本通知发布之日起,〔2022〕XXX 号文同时废止",
  "confidence": 0.95,
  "extracted_by": "regex+llm",
  "extracted_at": "2026-04-25T..."
}
```

### 6.2 反链生成

每条关系自动在两端政策的派生侧栏(`1_extracted/relations/_index_by_policy/<id>.md`)互相反链,raw frontmatter 不动。详细文件结构见 §6.4。

### 6.3 cites_basis(第 8 类)特殊性

与 7 类典型 relation 不同的两点:

**(1) 是 references 的严格子集 + 标题引用补漏**

| 维度 | references | cites_basis |
|---|---|---|
| 抓取范围 | 全文所有〔YYYY〕XXX 号文号 | 仅政策开头 1-2 段"根据/依据/参照 X" |
| 语义 | 提及/引用(弱) | **作为制定依据**(强) |
| 位置 | 不分场合 | 限定 location=opening |
| confidence | 0.7 | ≥ 0.85 |

集合关系:
`cites_basis ⊂ (references ∩ location=opening ∩ semantic="basis") ∪ title_match_补漏`

其中 title_match 补漏:regex 抓不到的"无文号《xxx》引用"(开头段直接引政策标题、不附文号),需 canonical 别名表匹配。

**(2) jsonl 行扩展两个字段**

在 §6.1 标准格式基础上加 `location` 和 `semantic`:

```json
{
  "from": "P_2025_SD_xxx",
  "to":   "P_2025_SH_407",
  "rel":  "cites_basis",
  "evidence": "原文第1段:根据《上海市虚拟电厂运营管理办法》(沪经信运〔2025〕407号)...",
  "location": "opening",
  "semantic": "basis",
  "confidence": 0.92,
  "extracted_by": "regex_filter+llm_judge",
  "extracted_at": "2026-04-27T..."
}
```

枚举:
- `location` ∈ {`opening`, `body`, `supplementary`}:opening = 政策正文前 ~800 字符;supplementary = 附则
- `semantic` ∈ {`basis`, `clause_ref`, `context_mention`}:仅 `basis` 进 cites_basis;其余留在 references
- `extracted_by` ∈ {`regex_filter`, `llm_judge`, `title_match`, 组合(以 `+` 连接)}

### 6.4 反链文件结构(_index_by_policy/)

§6.2 声明的 `_index_by_policy/<id>.md` 反链文件标准结构:

```yaml
---
policy_id: P_2025_SH_407
title: 上海市虚拟电厂运营管理办法
inbound_edge_count: 12
last_updated: 2026-04-27T10:30:00+08:00
---

# 入向反链:P_2025_SH_407

## 被引为依据 (cited_as_basis_by) — 5
- [[P_2025_SD_xxx]] — 山东 VPP 政策(2025-09-15)
- ...

## 被废止 (superseded_by) — 0
(无)

## 被迭代 (iterated_by) — 1
- [[P_2026_SH_xxx]] — 2026 修订版(2026-03-10)

## 被引用 (referenced_by) — 4
- ...

## 被扩展 / 被细化 / 被对齐 / 被冲突 (extended_by / clarified_by / aligns_with_by / conflicts_with_by) — 略
```

**出向 → 入向命名表**:

| 出向 jsonl | 入向 section |
|---|---|
| supersedes | superseded_by |
| iterates | iterated_by |
| extends | extended_by |
| clarifies | clarified_by |
| references | referenced_by |
| aligns_with | aligns_with_by |
| conflicts_with | conflicts_with_by |
| cites_basis | **cited_as_basis_by**(语法通顺优先) |

**生成规则**:
- 每条 `1_extracted/relations/<rel>.jsonl` 行触发两端反链更新(target 的 _index_by_policy 文件追加一条)
- 反链文件**完全派生**,可全量重建(`policy-rebuild --reverse-links`)
- `[[P_xxx]]` 双链格式让 Obsidian 直接可点
- 反链生成脚本独立运行(B 阶段实施,A' 不实施)

### 6.5 覆盖率口径(4 象限分母,2026-04-29 修订)

**反链页面只为"有入向边"的政策生成**(否则页面是空骨架,无价值)。计算覆盖率时,**不能用 `已生成 / 总政策数` 做分母**——这会把"新政策时间未到"误算成缺陷。

**正确口径(4 象限分类):**

| 象限 | 出向 | 入向 | 含义 | 期望反链页 |
|---|---|---|---|---|
| ◆ 双向 | ≥1 | ≥1 | 网络中间节点 | ✓ 必须 |
| ← 仅入向 | 0 | ≥1 | 早年/上位/被引用政策 | ✓ 必须 |
| → 仅出向 | ≥1 | 0 | 新政策(还没被后辈引用) | ✗ 不需要(自身视角靠 outbound section) |
| ✗ 真孤立 | 0 | 0 | 完全没参与关系网 | ✗ 不需要 |

**真实覆盖率公式**:
```
真实覆盖率 = 已生成反链页数 / (双向 + 仅入向)
```

vault 263 政策(2026-04-29 实测):双向 58 / 仅入向 47 / 仅出向 70 / 真孤立 88 → 真实覆盖率 = 105 / 105 = **100%**。

(`已生成/总数` = 40% 是错误口径,会被新政策时间维度淹没。)

### 6.6 反链页面双向化(X1, 2026-04-29 引入)

仅入向投影对"仅出向新政策"是不可见的(b 政策引用了 a,但 b 自己的 .md 看不到这条边)。

**修订后反链页面双向化**:文件名仍叫 `_index_by_policy/<P_id>.md`,但内容包含两个区:

```markdown
# 入向反链:P_xxx
## 被引为依据 — N
## 被引用 — N
...

# 出向引用:P_xxx     ← 新增
## 引用了 — N
## 细化了 — N
## 迭代了 — N
...
```

仅出向政策(70 个)也会**生成反链页**(只有出向区,无入向区),让"新政策视角"可见。

---

## 7. 演进差异(diffs/)

每对 `supersedes` / `iterates` / `extends` 关系**自动触发** LLM diff 抽取,落:

```
1_extracted/diffs/<new_id>__from__<old_id>.md
```

### 7.1 diff 文件结构

```yaml
---
new: P_2024_NDRC_718
old: P_2022_NDRC_xxx
rel: supersedes
extracted_at: 2026-04-25T...
confidence: 0.85
---

## 演进核心差异

| 维度 | 旧政策 | 新政策 | 影响 |
|------|--------|--------|------|
| 适用范围 | 5 个试点城市 | 30 个城市 | 滴滴能源全网受惠 |
| 补贴标准 | 0.1 元/kWh | 0.2 元/kWh + 弹性 | 单桩日均 +30% |
| 准入门槛 | 注册资本 5000 万 | 1000 万 | 中小聚合商可入 |
| 执行时限 | 2024-12-31 | 2025-12-31 | 时窗延 1 年 |

## 对滴滴能源
- **加油**:无影响
- **充电**:门槛降低,需重新评估聚合商资质申报
- **电力**:补贴上限提升,V2G 经济性进一步好转
```

### 7.2 LLM 抽取 prompt 骨架

```
输入:旧政策正文(<= 5000 字)+ 新政策正文(<= 5000 字)+ 关系类型
输出 JSON:
{
  "diff": [
    {"dimension": "...", "old": "...", "new": "...", "impact": "..."}
  ],
  "didi_impact": {
    "加油": "...",
    "充电": "...",
    "电力": "..."
  },
  "confidence": 0.0-1.0
}
```

---

## 8. 评论观点(opinions/)

观点(stance)是评论的派生品,**不写在评论 frontmatter**,落 `1_extracted/opinions/<policy_id>.md`。

### 8.1 stance 抽取(每条评论)

```yaml
stances:
  - on: P_2024_NDRC_718
    aspect: 补贴力度                    # 议题
    polarity: critical                 # supportive / critical / neutral / mixed
    claim: "0.2 元/kWh 仍不足覆盖建桩与运维"
    evidence_quote: "...原文摘录..."
    confidence: 0.85
```

`polarity` 4 档(用户拍板):
- `supportive`:明确正面评价
- `critical`:明确负面评价
- `neutral`:中性观察/事实陈述
- `mixed`:同时包含正反两面

### 8.2 政策舆论矩阵(opinions/<policy_id>.md)

```markdown
# P_2024_NDRC_718 舆论矩阵

## 共识(≥3 独立来源同向)
- 🟢 政策方向正确(7 篇支持)— 中国能源报、北极星售电网、南方能源观察 ...
- 🟢 试点城市选择合理(4 篇)

## 分歧
| 议题 | 支持方观点 | 反对方观点 |
|------|----------|----------|
| 补贴力度 | "已是历史最高" — 中国充电联盟 | "覆盖不了建桩成本" — 充电桩资源 |

## 中性观察
- ⚪ 实施时间表偏紧 — IESPlaza
- ⚪ 跨省结算细则待出 — 电力低碳

## 待跟进
- 配套电网改造方案是否同步? — 多家媒体提问未答
```

### 8.3 共识 / 分歧判定规则

- **共识**:≥3 独立来源(不同公众号/媒体)持相同 polarity 且 aspect 相同
- **分歧**:同一 aspect 下出现 ≥2 不同 polarity(supportive vs critical)
- **中性观察**:polarity = neutral 的独立条目
- **待跟进**:LLM 在评论里识别为"开放问题"的句子(以"?"/"未明确"/"待出"等结尾)

---

## 9. 主题结晶页(2_crystallized/themes/<theme>/)

每个 theme 一个目录,4 个标准文件:

| 文件 | 内容 |
|------|------|
| `overview.md` | 主题综述 + 关键政策 Top N + 时间脉络要点 |
| `timeline.md` | 同主题政策按时间排序的时间线(国家 + 省级 + 地市) |
| `regional-coverage.md` | 区域覆盖矩阵 + 空白发现 |
| `opinions-summary.md` | 同主题下所有政策舆论的元分析 |

### 9.1 timeline.md 模板

```markdown
# V2G 政策时间线

## 国家级
- 2024-01  发改办能源〔2024〕718号(extends 北京/上海试点)
- 2024-06  ...

## 省级
- 2023-05  北京 V2G 试点方案
- 2023-09  上海 V2G 实施细则
- 2025-03  广东 V2G 行动方案(iterates)

## 演进逻辑
试点先于全国 → 国家文出后省级跟随 → 省级出后地市补操作细则
当前阶段:**省级铺开 + 地市落地**
```

### 9.2 regional-coverage.md 矩阵

```markdown
# V2G 区域覆盖

| 区域级别 | 已覆盖 | 空白(优先关注) |
|---------|-------|---------------|
| 国家级  | ✅ 1 篇 | — |
| 省级    | 京沪津渝 + 粤鄂闽川等 8 个 | **东北 3 省**, **西北 5 省** |
| 地市级  | 12 个 | (略) |

## 空白发现
东北 3 省全空 → 建议:Step 8 缺口分析将其加为 Type C 地方政策盲区
```

---

## 10. 全局大盘(2_crystallized/_global_index.md)

由派生管道生成,内容:
- 总政策数 / 总评论数 / 总实体数
- 按 theme / region / issuer 的分布
- 近 30 天新增 Top N(按重要性排序)
- 关系网密度(总关系条数 / 政策对数)
- 链接到所有 themes/

---

## 11. 派生管道(L1 → L2 衔接)

```
L1 daily-scan 完成入库(0_raw 新增)
        │
        ▼
[抽实体]  LLM 抽实体词 → 查 registry → 命中落 canonical id / 未命中进 _review_queue.yaml
        │
        ▼
[抽关系]  8 类关系并行
   ├─ supersedes:    正则文号引用 + LLM 验证
   ├─ iterates:      标题/摘要相似度 + LLM
   ├─ extends:       region 跳变检测 + LLM
   ├─ clarifies:     标题词("实施细则/操作指引")+ LLM
   ├─ references:    正则文号交叉引用
   ├─ aligns_with:   主题向量相似度 + LLM
   ├─ conflicts_with: LLM 仅扫高分政策对
   └─ cites_basis:   位置过滤(references 子集 + 开头 800 字符) + LLM 语义判定 + 标题引用补漏
        │
        ▼
[生成 diff]  对 supersedes / iterates / extends 关系,LLM 抽演进差异 → diffs/
        │
        ▼
[抽观点]  新评论 → LLM 抽 stance → opinions/<policy_id>.md 增量更新
        │
        ▼
[更新结晶]  受影响的 themes / regions 重新派生 timeline + matrix
        │
        ▼
[lint]  跑 daily lint(增量,见第 12 节)
```

---

## 12. Lint 设计

### 12.1 Daily lint(随 daily-scan 自动跑)

| 检查项 | 失败处置 |
|--------|---------|
| 新政策 frontmatter 必填字段齐全(id / title / date / region / provenance) | 标 `lint_error`,阻断派生 |
| `id` 全 vault 唯一 | 提示碰撞,加后缀重生成 |
| `supersedes` 引用的旧政策必须在 raw 里存在 | 标 dangling,进 review |
| `region.code` 与 `name` 一致(查行政区划代码表) | 修正或标 review |
| 抽取的实体词 100% 在 registry 命中 | 不阻断,_review_queue 累积 |
| `diffs/` 与 `supersedes.jsonl` 数量对齐 | 触发 diff 补跑 |

### 12.2 Weekly lint(单独 cron,周日 10:30)

| 检查项 | 处置 |
|--------|-----|
| 双向反链对齐(A→B 关系存在 ↔ entity B 反链页含 A) | 重建反链页 |
| 孤儿 canonical(registry 里有但无政策引用 ≥30 天) | 进归档候选 |
| 悬空别名(alias 从未被任何政策匹配) | 提示 review:删 / 保留作 SEO |
| 实体相似度聚类(simhash + LLM judge) | 提示"这 N 个可能是同一个 → 合并?" |
| 置信度衰减(关系 ≥6 月未触碰 confidence × 0.95) | 自动衰减 |
| 评论观点抽取覆盖率(已抽 stance / 评论总数) | 报告里列 |
| themes 时间线最新性(主题 >90 天未更新) | 提示是否归档 |

### 12.3 Lint 报告位置

```
3_lints/daily/<YYYY-MM-DD>.md
3_lints/weekly/<YYYY-MM-DD>.md
```

有 `lint_error` 级别问题时推决策频道(维护期)。

---

## 13. 与 v2 schema 的差异(迁移参考)

| 维度 | v2(已退役) | v3(当前) |
|------|-----------|----------|
| 目录布局 | `01 核心政策/` + `04 实体节点/` + `05 概念节点/` 等中文数字目录 | `0_raw/` + `1_extracted/` + `2_crystallized/` 三层 |
| 实体规范化 | 无,导致同实体 7-8 个变体 | canonical registry,抽取阶段强制规范化 |
| 关系类型 | 4 种(supercedes / iterates / supports / impacts) | 8 种(细化 + extends / clarifies / references / aligns_with / conflicts_with / cites_basis) |
| 关系存储 | 政策 frontmatter 内 | 外置到 `1_extracted/relations/*.jsonl` |
| 演进差异 | 无 | `diffs/` 显式 LLM 抽 |
| 观点表达 | 仅 Commentary 实体 | stance(polarity 4 档)+ 政策舆论矩阵 |
| 区域维度 | 无 | region 作独立实体 + 主题区域覆盖矩阵 |
| 主题结晶页 | 标"后续建设" | 第一类公民,4 标准文件 |
| Provenance | url + source_type | 完整结构化(fetched_via / fetched_at / collected_by / collected_mode) |
| Lint | 无 | daily + weekly |

---

## 14. 不做(明确边界)

- **不迁移 backup 470 历史文件**(0_raw 只装 289 + 338,backup 仅作 registry 种子参考)
- **不在 raw 里写关系**(关系一律外置)
- **不允许实体页手写**(必须经 registry 派生)
- **不做混合搜索**(P3,留待 L3 阶段)
- **不做 supersedes / cites_basis 之外的事实继承链自动推断**(本期 8 类关系够用;cites_basis 仅抓政策开头段的显式声明,不做隐式继承推断)

---

_v3 起草于 2026-04-25,与 L2 第二阶段同步落地_
