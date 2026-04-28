# L1 地基整改 + L2 themes 业务覆盖补全 — 设计文档

**日期**:2026-04-28
**作者**:Claude(brainstorming → spec)
**状态**:用户已认可(2026-04-28),待实施
**先决依赖**:P0-2 supersedes/iterates v2 重抽完成(commit `2852660`)

---

## 1. 目标与边界

### 1.1 目标

一次性完成两件事:

1. **L1 地基整改**:把 0_raw/ 里阻塞 L2 抽取与 themes 构建的 P0/P1 病灶修干净
2. **L2 themes 业务覆盖补全**:补 5 个新主题(虚拟电厂 / 新型储能 / 加油站转型 / 以旧换新 / 绿电交易),让 L3 月报"比较级论断"和"省级首批" fact-check 第一次有数据支撑

### 1.2 不在本轮范围(明确边界)

- ❌ **opinions 扩到 ≥40%**:链路诊断显示是 L1 commentary 池质量问题(news_report/reposted_original 占大头无法抽 stance),需独立工程,本轮拿掉
- ❌ **conflicts_with 抽取**:留给下一轮 P0 队列
- ❌ **references title_match 补漏**:留给下一轮 P1 队列
- ❌ **schema 升级**(加 `business_relevance` 字段等):需独立 RFC,不混入本轮
- ❌ **西部地区政策池补充 / 历史政策补**:L1 数据厚度已经够用(每候选主题 ≥69 篇),本轮不补采集

### 1.3 决策依据

L1 audit 关键发现(详见对话记录,Explore subagent 报告):

| 指标 | 数值 | 状态 |
|---|---|---|
| 政策完整性 | 289 篇正文 100% 完整,99.6% gov.cn | ✅ 优 |
| 5 候选主题政策池 | 69-94 篇 | ✅ 全过 ≥10 阈值 |
| issuer 标准化 | 23 种"国发改"写法共存 | ❌ **真 P0 阻塞** |
| registry.yaml type=theme 实体 | **0 个**(89 总实体) | ❌ **真 P0 阻塞** |
| 政策 vs 解读边界污染 | 2/40 = 5% | ⚠️ P1 顺手清 |
| region.level=未知 | 6 篇 | ⚠️ P1 顺手清 |
| 二手源标记缺失 | 1 篇 chinaenergyportal.org | ⚠️ P1 顺手清 |
| frontmatter.theme 字段缺失 | (audit 误报) | ✅ schema §4 没要求,无问题 |
| frontmatter.business_relevance 字段缺失 | (audit 误报) | ✅ schema §4 没要求,要加属架构升级 |

---

## 2. 模块设计

5 个模块按依赖顺序执行:`Module 1 → Module 2 → Module 3 → Module 4 → Module 5`。

### Module 1 / P0a — issuer 标准化

**问题**:`0_raw/policies/*.md` frontmatter 里 issuer 字段是字符串数组,同一机构存在 23 种写法(如"国家发展改革委" / "国家发展和改革委员会" / "国家发改委"),P0-2 same_issuer 配对时已踩过坑。

**方案**:写脚本 `_meta/scripts/standardize_issuer.py`,加新字段 `issuer_canonical: [org_id, ...]`,**不动原 `issuer` 字段**(可回滚)。

**实现细节**:

```
1. 读 1_extracted/entities/registry.yaml 所有 type=[org] 实体
   → 构建 {alias_str: canonical_id} 反查表
2. 扫 0_raw/policies/*.md (289 篇)
   - 解析 frontmatter
   - 对 issuer 数组逐项匹配:
     a. 完全匹配 alias → 命中
     b. 包含子串匹配 → 命中(如 "国家发改委等部门" 命中 "国家发改委")
     c. 未命中 → 进 _meta/issuer_review_queue.yaml
   - 写 issuer_canonical: [...] 到 frontmatter
3. 输出 summary:
   - 命中率(目标 ≥95%)
   - 未命中机构 Top 10(按出现频次)
   - 写到 _meta/issuer_standardize_summary.md
4. 人工 review _meta/issuer_review_queue.yaml,补 registry aliases,重跑直到命中率达标
```

**字段决策**(用户认可):加新字段 `issuer_canonical`,不动 `issuer`。理由:可回滚 + 不破坏现有抽取脚本的兼容性。

**验证**:
- 289 篇全部有 `issuer_canonical: [...]`,且数组不空
- 未命中率 ≤ 5%(即 ≤14 篇,需人工补 aliases 后重跑)
- 抽 5 篇人肉对照原 issuer 字符串与 canonical id 列表

**工作量**:2-3h(脚本 1h + 处理 review_queue 1-2h)

**风险**:registry org 实体的 aliases 不充分,导致大量未命中。**缓解**:第一遍跑完看 review_queue,批量补 aliases 后重跑。

---

### Module 2 / P0b — registry.yaml 加 5 个 type=theme 实体

**问题**:registry.yaml 89 个实体,type=theme 的有 **0 个**。已建 3 个 themes(V2G/CHARGING_INFRA/POWER_MARKET)是借用其他类型 entity ID 跑通的,不合 schema §2 规范。

**方案**:直接编辑 `1_extracted/entities/registry.yaml`,append 5 个 yaml block:

```yaml
- id: vpp_theme
  canonical_name: 虚拟电厂
  type: [theme]
  aliases:
    - 虚拟电厂
    - VPP
    - 需求侧响应聚合
    - 负荷聚合
    - 可调节负荷
    - 需求响应
  desc: VPP 政策主题(国家级 + 省级试点 + 市场化运营规则)
  added_at: 2026-04-28
  added_by: l2_themes_expansion_v1
  confidence: 0.95

- id: energy_storage_theme
  canonical_name: 新型储能
  type: [theme]
  aliases:
    - 新型储能
    - 电化学储能
    - 储能电站
    - 共享储能
    - 储能调用
    - 储能并网
    - 用户侧储能
    - 独立储能
  desc: 新型储能政策主题(配置规模 + 调用机制 + 并网规则 + 价格政策)
  added_at: 2026-04-28
  added_by: l2_themes_expansion_v1
  confidence: 0.95

- id: gas_station_transition_theme
  canonical_name: 加油站转型
  type: [theme]
  aliases:
    - 加油站
    - 油电融合
    - 光储充换
    - 油气电氢一体化
    - 综合能源补给站
    - 加油站升级
  desc: 加油站向综合能源服务站转型政策主题
  added_at: 2026-04-28
  added_by: l2_themes_expansion_v1
  confidence: 0.95

- id: equipment_renewal_theme
  canonical_name: 以旧换新
  type: [theme]
  aliases:
    - 以旧换新
    - 汽车换新
    - 消费品更新
    - 设备更新
    - 大规模设备更新
    - 报废更新
    - 汽车以旧换新
  desc: 以旧换新与设备更新政策主题(国务院专项 + 部委细则 + 各省落实)
  added_at: 2026-04-28
  added_by: l2_themes_expansion_v1
  confidence: 0.95

- id: green_power_trading_theme
  canonical_name: 绿电交易
  type: [theme]
  aliases:
    - 绿电交易
    - 绿电消费
    - 绿色电力证书
    - 绿证
    - 可再生能源消纳
    - 绿电直供
    - 可再生能源消费承诺
  desc: 绿电交易与绿证制度政策主题
  added_at: 2026-04-28
  added_by: l2_themes_expansion_v1
  confidence: 0.95
```

**命名决策**(用户认可):用 `xxx_theme` 后缀。理由:避免与已有 concept 实体(如 `vpp`)冲突,语义清晰。

**aliases 设计原则**:充分但不污染。每条 alias 必须满足"出现在标题/tag/body 时,该政策的确属于这个主题"。

**验证**:
- 对每个 theme 跑 `python3 _meta/scripts/crystallize_theme.py --theme <id> --aliases <list>`
- 看 `_meta/<theme>_theme_input.json` 政策数 ≥ 30(L1 audit 估算每主题 70-95 篇)
- 抽样验证 timeline.md 政策不混入无关主题

**工作量**:30min-1h

---

### Module 3 / P1 — 顺手清理

3 件小事一并做:

| 子任务 | 操作 | 工作量 |
|---|---|---|
| 2 篇政策 → commentaries 移位 | 1. 文件名:含"解读文章"/"报道"的 2 篇<br>2. `git mv` 到 `0_raw/commentaries/`<br>3. 修改 frontmatter `type: 政策评论`<br>4. 加 `related_policy: [[<原政策 id>]]` 字段 | 15min |
| 6 篇 region.level=未知 补全 | 1. 脚本扫出哪 6 篇<br>2. 人工读 frontmatter + body 推断正确 region<br>3. 直接改 frontmatter | 30min |
| 1 篇 chinaenergyportal.org 标二手源 | 改 frontmatter `provenance.source_type: B`(媒体二手源) | 5min |

**实施脚本**:`_meta/scripts/cleanup_l1_misc.py`(可选,半自动)

**验证**:
- `policies/` 下不再含"解读文章/报道"标题
- 0 篇 region.level=未知
- gov.cn 之外的来源都标 source_type=B

**工作量**:1h

---

### Module 4 / L2 主体 — 5 主题结晶

**复用现有脚本** `_meta/scripts/crystallize_theme.py`,无需修改(接口已支持任意 canonical_id + aliases list)。

**Pipeline**:

```
For each theme in [vpp_theme, energy_storage_theme,
                   gas_station_transition_theme, equipment_renewal_theme,
                   green_power_trading_theme]:

  Step A: python3 crystallize_theme.py --theme <theme> --aliases <list>
    ↓ 自动产出:
      2_crystallized/themes/<theme>/timeline.md
      2_crystallized/themes/<theme>/regional-coverage.md
      _meta/<theme>_theme_input.json

  Step B: 起 1 个 subagent 跑 LLM 部分:
    输入: _meta/<theme>_theme_input.json
    输出:
      2_crystallized/themes/<theme>/overview.md
      2_crystallized/themes/<theme>/opinions-summary.md
```

**Subagent 并发策略**(用户认可):5 个 subagent 并发(主代理一个 message 内 5 个 Agent tool call)。理由:
- 主代理上下文不被污染(每个主题 input.json 大,LLM 输出长)
- 并发 ~30min 完成(对比单线程 ~2h)
- 每 subagent 独立任务,无共享状态

**Subagent 提示词骨架**:
```
你是政策主题结晶分析专家。读 _meta/<theme>_theme_input.json,产出 2 份 markdown:

1. overview.md (按 schema_v3 §9):
   - 主题综述(3-5 段)
   - Top 10 关键政策(按 重要性 + 引用数排序)
   - 时间脉络要点(国家级演进 + 省级铺开 + 地市落地的 3-stage 总结)
   - 业务影响要点(对滴滴三大业务线的具体启示)

2. opinions-summary.md (strict 模式 + schema_v3 §8.3):
   - 开头必须标注:"本主题共 N 篇政策,有舆论矩阵的 X 篇 (X/N=Y%)"
   - 共识/分歧/中性观察按规则聚合
   - 末尾列"未覆盖政策清单"(链接到反链页)
   - **绝对禁止编造无 stance 数据政策的观点**

输出严格 markdown,frontmatter 用 yaml。
```

**opinions-summary 诚实化决策**(用户认可):strict 模式必带覆盖率。理由:防止 LLM 编造未抽到 stance 的政策观点(L3 月报"诚实标注"原则的延伸)。

**工作量**:5 × ~30-40min ≈ 2.5-3.5h(主要被 subagent 并发吃掉,主代理时间 ≤30min)

**5 主题清单**:
| theme id | 政策池估算 | aliases 关键词 |
|---|---|---|
| `vpp_theme` | 86 | 虚拟电厂 / VPP / 负荷聚合 |
| `energy_storage_theme` | 94 | 新型储能 / 电化学储能 |
| `gas_station_transition_theme` | 72 | 加油站 / 油电融合 |
| `equipment_renewal_theme` | 91 | 以旧换新 / 设备更新 |
| `green_power_trading_theme` | 69 | 绿电 / 绿证 |

---

### Module 5 — 验证 + commit 策略

3 个 commit(按模块分):

| Commit | 范围 | 文件 |
|---|---|---|
| **C7 chore(L1): 地基整改** | Module 1 + 3 | `_meta/scripts/standardize_issuer.py` (新)<br>`_meta/scripts/cleanup_l1_misc.py` (新, 可选)<br>`_meta/issuer_standardize_summary.md` (新)<br>`0_raw/policies/*.md` (frontmatter 加 `issuer_canonical`)<br>`0_raw/commentaries/<2 篇移位>.md` (新位置)<br>`0_raw/policies/<6 篇 region 补>.md` (修)<br>`0_raw/policies/<1 篇 source_type 补>.md` (修)<br>`0_raw/policies/<2 篇移位前>.md` (删) |
| **C8 feat(L2): registry 加 5 theme 实体** | Module 2 | `1_extracted/entities/registry.yaml` (修) |
| **C9 feat(L2): 5 主题结晶页** | Module 4 | `2_crystallized/themes/<5 个新目录>/` (新)<br>`_meta/<5 theme>_theme_input.json` (新) |

**每 commit 后验证**:
- C7:跑 P0-2 v2 抽取(`extract_evolution_v2.py --dump-candidates`)看 issuer 候选生成是否变干净
- C8:对每个新 theme 跑 `crystallize_theme.py --dry-run`(如果脚本支持)或看 _input.json 政策数
- C9:抽样读每个 theme 的 4 件套 .md,看是否完整、无幻觉

---

## 3. 总工作量

| 模块 | 时长 |
|---|---|
| Module 1 issuer 标准化 | 2-3h |
| Module 2 registry theme 实体 | 30min-1h |
| Module 3 顺手清理 | 1h |
| Module 4 5 主题结晶 | 2.5-3.5h |
| Module 5 commits + 验证 | 30min |
| **合计** | **6.5-9h** |

可一晚 / 半天搞定。

---

## 4. 验证清单(整体)

完工标准:

- [ ] 289 篇 policies 全部有 `issuer_canonical: [...]` 字段
- [ ] `_meta/issuer_review_queue.yaml` 命中率 ≥95% / 残留 ≤14 篇且有 review 记录
- [ ] `policies/` 下 0 篇标题含"解读文章/报道/答记者问"
- [ ] 0 篇 `region.level == "未知"`
- [ ] `registry.yaml` 含 5 个 type=[theme] 实体
- [ ] `2_crystallized/themes/` 下 5 个新目录(共 8 个)
- [ ] 每个新 theme 目录含 4 个 .md(overview / timeline / regional-coverage / opinions-summary)
- [ ] 每个 opinions-summary.md 开头有"覆盖率 X%"标注
- [ ] 3 个 commits 干净落地
- [ ] 开发日记 `开发日记/2026-04-28/日志.md` 追写本轮总结

---

## 5. 已知风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| issuer aliases 不充分,未命中率 >20% | 中 | Module 1 卡住 | 第一遍跑完批量补 aliases,重跑 |
| 某 theme aliases 污染(把无关政策抓进来) | 中 | timeline 失真 | 抽样人审 timeline,微调 aliases 再重跑 crystallize_theme.py |
| subagent LLM 编造 opinions(未 strict) | 低(已 strict) | opinions-summary 失真 | 提示词 strict + 主代理 spot-check 5/5 主题各 1 段 |
| crystallize_theme.py 对新 theme id 不兼容 | 低 | Module 4 卡住 | 第一个 theme 跑完先验证,再并发 |
| _meta/<theme>_theme_input.json 太大塞不进 subagent | 低 | subagent 截断 | 政策池预估 ≤94 篇,frontmatter+1 段摘要 ~5KB/篇,合 ~500KB 可控 |

---

## 6. 与下一轮的衔接

完工后立即解锁的下一轮 P0:

1. **conflicts_with 抽取**(用 LLM 扫高分政策对)
2. **opinions 扩到 ≥25%**(跑剩余 90 条 commentary stance,L1 commentary 池补全独立工程)
3. **references title_match 补漏 + supersedes regex 升级**

下一轮 P1:

4. **L1 政策原文 vs 解读分类**(本轮已部分修,但根因未解)
5. **cites_basis 二轮**(OPENING 800 → 1500)
6. **diffs 补跑 13 → 22**

---

## 7. 参考

- `_meta/schema_v3.md` §2 实体类型 / §4 policy frontmatter / §9 主题结晶页
- `_meta/scripts/crystallize_theme.py` 接口
- `1_extracted/entities/registry.yaml` 现有 89 实体
- `开发日记/2026-04-27/日志.md` P0-2 v2 重抽全过程
- 对话记录:Explore subagent L1 audit 报告(2026-04-28)
