---
title: 政策采集首轮 run-report
date: 2026-04-25
type: collection-meta
runs: [first-pass, increment-r2, district-d]
---

# 政策采集首轮总报告 · 2026-04-25

## TL;DR

- **入库政策**: **313 篇**(≥3 分主流 236 + <3 分存档 77)
- **入库评论**: **264 篇**(首轮 94 + 增量 170)
- **新发现渠道**: **197 个根域名**(自动追加到 `渠道目录.md` 自动发现段)
- **API 调用**: Tavily 51 次(8+27+16) / Firecrawl ≈ 920 次抓取(政策 273 + 评论 ≈ 600+)
- **耗时**: 总跑约 4 小时(夜跑首轮 2h + 增量 r2 2h)
- **框架修订**: 3 处(1-2 分入库 / Step 2.5 渠道发现回写 / 直辖市下辖区)

---

## 三轮跑账本

| 轮次 | Step 2 查询 | 候选 | 过滤后 | 抓取 OK | 入库 ≥3 | 入库 <3 | 评论 OK |
|------|------------|------|-------|--------|---------|---------|---------|
| 首轮(简版) | 8 | 147 | 85 | 72 | 51 | 18 | 94 |
| 增量 r2(遍历) | 27 | 476 | 198 | 183 | 见合计 | 见合计 | 见合计 |
| 区级 d(直辖市) | 16 | 210 | 75 | 70 | 见合计 | 见合计 | 见合计 |
| **r2+d 合计** | **43** | **686** | **273** | **253** | **185** | **61** | **170** |
| **总计** | **51** | **833** | **358** | **325** | **236** | **79** | **264** |

---

## 框架修订(本轮发现 + 已写入 SOP/SKILL.md)

### 修订 1:1-2 分政策也要入库(只是不抓评论)

**原框架**:`综合分 <3 → 只记日志不入库`(SOP Step 5)
**新框架**:全部入库;<3 加 frontmatter 标 `archive: low_score`,不进 `ingested.jsonl`,Step 6 跳过
**已修改**:
- `00 背景资料/策略-八步采集法.md` Step 5 阈值表
- `00 背景资料/策略-八步采集法.md` Step 6 配额表
- `~/.openclaw/skills/policy-watch/SKILL.md` daily-scan 描述 + Step 6 配额表
- `step5_ingest.py` 全入库 + 双日志(`ingested.jsonl` / `ingested-low-score.jsonl`)

### 修订 2:Step 2.5 渠道发现回写(每日同步)

**原框架**:渠道目录只在 Step 8 缺口分析时被动反哺(周/月级)
**新框架**:每次 Step 2 跑完立即扫 candidates 的 `source_domain`,新根域名追加到 `渠道目录.md` 的"自动发现段"
**已修改**:
- `00 背景资料/策略-八步采集法.md` 新增 Step 2.5 章节
- `~/.openclaw/skills/policy-watch/SKILL.md` daily-scan 加 Step 2.5
- 实施脚本:`/tmp/step25_discovery.py`(本轮已运行,追加 197 条到自动发现段)

### 修订 3:直辖市下辖区(京沪津渝)纳入扫描范围

**原框架**:区/县级"本轮不做"
**新框架**:直辖市下辖区(京沪津渝 ~80 区)作"市级子区"专项扫描;一般地级市下辖区/县仍不做
**已修改**:
- `00 背景资料/策略-八步采集法.md` 渠道范围表 + 扩展四策
- `~/.openclaw/skills/policy-watch/SKILL.md` daily-scan 描述
- 实施脚本:`/tmp/step2d_districts.py`

---

## Step 4.5 结构化抽取效果

**正则层命中率**(253 篇):

| 字段 | 命中数 | 命中率 |
|------|------|------|
| 文号 | 141 | 56% |
| 发布日期 | 223 | 88% |
| URL→机构映射 | 117 | 46% |
| 业务标签粗筛 | 224 | 88% |

**LLM 兜底覆盖**:248 篇(≥1 字段需 LLM)→ 5 个 Agent 并行打分,平均每 Agent 50 条,总耗时 ~13 分钟

**JSON 解析失败**:r2 阶段 246 ok / 2 dropped(ASCII 引号嵌套);首轮 69 ok / 1 dropped。失败率 ~1%,可接受。

---

## 综合分分布

| 综合分 | 首轮 | r2 | d(归入 r2) | 总计 |
|:-----:|:----:|:--:|:----------:|:----:|
| 5 | 6 | 38 | — | 44 |
| 4 | 24 | 87 | — | 111 |
| 3 | 21 | 62 | — | 83 |
| 2 | 13 | 39 | — | 52 |
| 1 | 6 | 22 | — | 28 |
| 入库总 | 70 | 248 | 75(d) | 313 |

注:r2 + d 在 Step 4.5 后合并为统一批次,所以 r2 列含 d 部分。

---

## 渠道发现:197 个新根域名

**Top 命中数 ≥5 的新发现**(选样本):

| 命中数 | 根域名 | 含义 |
|:----:|---------|------|
| 7 | www.pudong.gov.cn | 上海浦东新区 |
| 7 | sww.sh.gov.cn | 上海市商务委员会 |
| 7 | www.cqspb.gov.cn | 重庆沙坪坝区 |
| 7 | zfxxgk.ndrc.gov.cn | 国家发改委政府信息公开 |
| 6 | www.fl.gov.cn | 重庆涪陵区 |
| 6 | fgw.sz.gov.cn | 深圳市发改委 |
| 6 | fgk.chinatax.gov.cn | 国家税务总局法规库 |
| 5 | sw.beijing.gov.cn | 北京市商务局 |
| 5 | gxt.fujian.gov.cn | 福建省工信厅 |
| 5 | www.nanjing.gov.cn | 南京市政府 |

完整列表:`collection-meta/2026-04-25/discovered-channels.jsonl` 197 条。
渠道目录已自动追加到 "## 自动发现段(待人工提升)"。

**待 Step 8 人工 review 后**:命中 ≥3 且 ≥7 天 → 提升到正式段;<3 留观察。

---

## 已知问题与下轮优化

### 数据质量

1. **JSON 引号嵌套**:Agent 打分时偶尔在中文标题里直接用 ASCII 双引号(如 `"两新"`),破坏 JSON。本轮丢 3 篇(可接受)。下轮在 prompt 里加更强约束 + Python 后处理时尝试修复内嵌引号。
2. **正则文号命中率仅 56%**:大量 r2 文件正文不含完整文号(摘要/转载/汇编类)。下轮提升:LLM 抽取时强制要求"如正文有任何形如 X〔YYYY〕Z 号的字符串都要捕"。
3. **r2 评论 fail 率 55%**(239 fail / 433 attempts):r2 多为地方/区级政策,圈内讨论少,Tavily 搜不到优质评论。下轮调整:r2 评论改为只搜近 6 月,且接受 0-1 篇评论。

### 工具可靠性

1. **Firecrawl 408 timeout**:首轮 13/85 失败 / r2 15/198 失败 / d 5/75 失败。地方政府站超时居多。下轮加重试机制(失败重试 1 次,间隔 30s)。
2. **wechat-article-to-markdown**:本轮没主动用(候选里没多少 mp.weixin.qq.com URL,Tavily 搜不到公众号正文)。Step 7 反扫公众号本轮跳过(无优质号种子)。

### 规模与成本

- Tavily:51 次调用(免费 1000/月),还远没用完
- Firecrawl:~920 次,免费 500/月可能耗尽,需观察额度;两个 key 备份正常

### 框架未实施

1. ~~Step 7 优质公众号反扫~~ → **本轮已补做**(详见下方 Step 7 章节)
2. ~~Step 8 缺口分析~~ → **本轮已补做**(详见下方 Step 8 章节)
3. **OpenClaw cron 部署**:`policy-watch` skill 仍是 0.2 草稿,未注册 `policy-analyst` agent,未配 `obsidian.vault_path`,cron 未启。

---

## Step 7 · 搜狗微信反扫(本轮补做)

**背景**:Tavily 对 mp.weixin.qq.com 几乎零覆盖(264 评论里 0 篇公众号);Firecrawl 额度耗尽。改 Python 直连搜狗微信(`weixin.sogou.com`)。

**执行**:
- 输入:130 个 ≥4 分政策的核心标题
- 方法:`requests.get` 抓搜狗微信搜索结果页,正则解析 `<li id="sogou_vr_">` 块,提取 `<a uigs="article_title">` + `<span class="all-time-y2">公众号</span>`
- 节流:每条间隔 2s
- 反爬:全程未触发(130/130 完整跑完)

**产出**:
- **1285 篇文章** 引用记录
- **846 个公众号** 出现统计
- **209 个种子号**(出现 ≥2)/ **82 个核心种子**(出现 ≥3)

**Top 25 优质号种子**(出现 ≥5):

| 名次 | 次数 | 公众号 | 备注 |
|:-:|:-:|---------|------|
| 1 | 23 | 中国政府网 | 官方 |
| 2 | 16 | 中国充电联盟 | ⭐ 充电核心号 |
| 3 | 14 | 北极星售电网 | ⭐ 电力交易 |
| 4 | 12 | 充电桩资源 | ⭐ 充电 |
| 5 | 11 | 国家能源局 | 官方 |
| 8 | 8 | 南方能源观察 | ⭐ 头部能源观察 |
| 9 | 8 | 中国电力报 | 官方系 |
| 10-15 | 7 | 北极星储能网 / 电车资源 / IESPlaza / 风能专委会 / 碳中和博览会 / 中国能源报 | 行业核心 |
| 22 | 5 | 氢智会 | 氢能 |
| 23 | 5 | 储能头条 | 储能 |

**完整清单**:`collection-meta/2026-04-25/step7-seed-accounts.jsonl`(82 条 ≥3)

---

## Step 8 · 缺口分析(本轮补做)

**输入**:1285 公众号文章 + 313 vault 政策 + 渠道目录自动发现段(197)
**方法**:从 step7-articles 标题里正则抽 `《...》` 政策名 + `XX〔YYYY〕Z号` 文号 → 比对 vault 287 unique 标题哈希 + 247 文号

### 产出

- **Type A 政策遗漏: 44 条**(被 ≥2 公众号引用但 vault 未收)
- **Type B 渠道待提升: 32 个域名**(命中 ≥3,从 Step 2.5 自动发现段晋升候选)

### Type A · Top 10 政策遗漏(下轮优先补抓)

| # | 引用次数 | 政策 | Top 引用号 |
|:-:|:-:|------|---------|
| 1 | 10 | "十四五"新型储能发展实施方案 | 节能中国 / 风能专委会 / 电力低碳 |
| 2 | 6 | 四川省 2026 设备更新和以旧换新政策 | 四川发展改革 / 四川省节能协会 |
| 3 | 6 | 关于完善全国统一电力市场体系的实施意见 | 湖南省电力行业协会 / 贵州微能源 |
| 4 | 6 | 关于促进新型储能并网和调度运用的通知 | CESA储能 / 储能与电力市场 |
| 5 | 5 | 吕梁市氢能产业中长期发展规划(2022-2035) | 氢能联盟CHA / 氢能储运 |
| 6 | 5 | 北京市设备更新和以旧换新行动方案 | 中国充电联盟 / 中宏国研 |
| 7 | 4 | 重庆市新能源汽车便捷超充行动计划 | 中国充电联盟 ×3 |
| 8 | 4 | 电力市场运行基本规则 | 中国能源观察 / 中国电力报 |
| 9 | 4 | 关于做好 2026 年全国碳排放权交易市场工作通知 | 超腾能源 / 气候法律观察 |
| 10 | 4 | 关于加强电网调峰储能和智能化调度能力建设的指导意见 | 湖南可再生能源学会 |

完整 44 条:`collection-meta/2026-04-25/gaps-policies.jsonl`

### Type B · Top 10 渠道待提升

| # | 命中数 | 域名 |
|:-:|:-:|------|
| 1 | 7 | www.pudong.gov.cn(上海浦东) |
| 2 | 7 | sww.sh.gov.cn(上海商务) |
| 3 | 7 | www.cqspb.gov.cn(重庆沙坪坝) |
| 4 | 7 | zfxxgk.ndrc.gov.cn(发改委政府信息公开) |
| 5 | 6 | www.fl.gov.cn(重庆涪陵) |
| 6 | 6 | fgw.sz.gov.cn(深圳发改委) |
| 7 | 6 | fgk.chinatax.gov.cn(税务总局法规库) |
| 8 | 5 | sw.beijing.gov.cn(北京商务局) |
| 9 | 5 | gxt.fujian.gov.cn(福建工信厅) |
| 10 | 5 | www.nanjing.gov.cn(南京政府) |

完整 32 条:`collection-meta/2026-04-25/gaps-channels.jsonl`

### 反哺动作

**已自动写入**:
- `step7-seed-accounts.jsonl` 82 条种子号(下轮 Step 7 反扫优先输入)
- `step8-report.md` 完整缺口分析

**已闭环执行(本轮收尾)**:
- ✅ Type B Top 32 域名 → 已写入 `渠道目录.md` 的"第一轮 Step 8 提升的渠道(2026-04-25)"段
- ✅ Type A 44 政策 → 见下方"Type A 补抓"章节(全部抓回)

---

## Type A 补抓(本轮闭环)

**背景**:Firecrawl 付费 plan 额度本月跑爆(Hobby 3000 credits 用完,实际跑了 ~3528),5 月 25 日刷新。改用 **Tavily search + Python `requests` + `trafilatura`** 替代抓取链路。

### 流程

```
44 个 Type A 缺口政策
  ↓ Tavily search(include_domains=gov.cn,advanced)
找原文 URL(每个政策 top 3 备选)
  ↓ Python requests 直连(伪装 UA,verify=False)
trafilatura 提取主内容 → markdown
  ↓ 失败兜底:BeautifulSoup 全文清洗
落 staging-typeA/<hash>/content.md
```

### 结果

| 阶段 | 数量 |
|------|:---:|
| 输入 | 44 政策(Step 8 Type A 全量) |
| Tavily 搜索 + Python 抓取 | **44 OK / 0 FAIL**(成功率 100%) |
| Step 4.5 抽取 | 44 |
| Step 5 打分 | 44 (≥3 共 38 / <3 共 6;均分 3.5) |
| Step 5 入库 | **38 主流 + 6 archive**(总 44) |
| Step 6 评论(Tavily+trafilatura 路径) | **88 OK / 5 FAIL**(成功率 95%) |

### Tavily+trafilatura 替代方案验证

实测**比 Firecrawl 还稳**:

| 抓取阶段 | 工具 | OK | FAIL | 成功率 |
|---------|------|:--:|:---:|:----:|
| Step 4(首轮 + r2 + d) | Firecrawl | 325 | 33 | 91% |
| Step 4 typeA | **Tavily+trafilatura** | **44** | **0** | **100%** |
| Step 6(首轮 + r2) | Firecrawl + Tavily | 299 | 245 | 55% |
| Step 6 typeA | **Tavily+trafilatura** | **88** | **5** | **95%** |

**结论**:Tavily+trafilatura 已写入 SOP 工具分工章节作为**法定 plan B**(Firecrawl 不可用时自动降级)。该路径在维护期 cron 跑时,如果 Firecrawl 返回 `Insufficient credits` 或连续超时,应自动切换。

---

## 第一阶段最终账本

| 维度 | 首轮 | 增量 r2+d | Type A 补抓 | **总计** |
|------|:---:|:--------:|:----------:|:------:|
| Tavily 搜索 | 8 | 43 | 44 | **95** |
| Firecrawl 抓取 | 85 | 273 | 0 | **358** |
| Tavily+trafilatura 抓取 | 0 | 0 | 44 + 93(评论) | **137** |
| 政策入库 ≥3 | 51 | 185 | 38 | **274** |
| 政策入库 <3(archive) | 18 | 61 | 6 | **85** |
| 评论入库 | 94 | 170 | 88 | **352**(去重后实 338) |
| 渠道发现(自动) | — | — | — | **197**(其中 32 已提升正式段) |

**vault 现状**:
- `01 核心政策/`: **357 政策**(274 主流 + 83 archive,扣去名重)
- `02 政策评论/`: **338 评论**

---

## 第一阶段框架修订汇总(SOP + SKILL.md 已落实)

1. ✅ **1-2 分政策入库存档**(Step 5 阈值改全入,加 `archive: low_score` frontmatter)
2. ✅ **Step 2.5 渠道发现回写**(每次 Step 2 后扫 source_domain → 自动发现段)
3. ✅ **直辖市下辖区扫描**(京沪津渝,扩展四策中的第 4 策)
4. ✅ **Step 4.5 结构化抽取**(正则 + LLM 级联)
5. ✅ **Tavily+trafilatura 替代抓取链路**(本轮新增,作 Firecrawl 法定 plan B)
6. ✅ **遍历策略默认行为**(Step 2 翻页至边际收敛 + 多查询变体 + Jaccard 去重)

---

## 关键文件清单

### Vault 内(可查阅)

```
政策分析/
├── 00 背景资料/
│   ├── 滴滴能源-政策分析背景.md       ← 业务背景(零改动继承)
│   ├── 渠道目录.md                    ← +197 条自动发现段
│   ├── 政策重要性打分体系.md            ← 六维打分(零改动继承)
│   ├── 策略-八步采集法.md               ← 含 Step 2.5 + 直辖市区 + 1-2 分入库
│   ├── schema/政策分析-领域schema.md    ← Karpathy v2 schema(零改动继承)
│   └── collection-meta/
│       ├── 2026-04-25/                 ← 本轮所有日志
│       │   ├── baseline.jsonl
│       │   ├── candidates.jsonl
│       │   ├── candidates-r2.jsonl
│       │   ├── candidates-d.jsonl
│       │   ├── filtered.jsonl
│       │   ├── filtered-r2.jsonl
│       │   ├── filtered-d.jsonl
│       │   ├── scraped.jsonl
│       │   ├── scraped-r2.jsonl
│       │   ├── extraction.jsonl
│       │   ├── extraction-r2.jsonl
│       │   ├── scored.jsonl            (首轮 69 条)
│       │   ├── scored-r2.jsonl         (r2 246 条)
│       │   ├── ingested.jsonl          (51 条 ≥3)
│       │   ├── ingested-low-score.jsonl (18 条 <3)
│       │   ├── ingested-r2.jsonl       (185 条 ≥3)
│       │   ├── ingested-r2-low-score.jsonl (61 条 <3)
│       │   ├── comments.jsonl          (94 条 OK)
│       │   ├── comments-r2.jsonl       (170 条 OK)
│       │   ├── discovered-channels.jsonl (197 条新渠道)
│       │   ├── review-batch-r2.md      (1.28 MB,Agent 打分输入)
│       │   └── run-report.md           ← 本文
│       └── staging/2026-04-25-r2/      (273 staging dir + content/meta/extracted)
├── 01 核心政策/                        ← 313 篇政策 .md
└── 02 政策评论/                        ← 264 篇评论 .md
```

### 脚本(在 /tmp/,下轮可固化为 skill 内置)

| 脚本 | 用途 | 步骤 |
|------|------|:---:|
| `step1prime_baseline.py` | 扫 vault 建去重基线 | 1 |
| `step2_tavily_search.py` | 简版 Tavily 8 查询 | 2 (deprecated) |
| `step2prime_tavily.py` | 遍历版 Tavily 27 查询 + advanced + 边际收敛 | 2 ✓ |
| `step2d_districts.py` | 直辖市下辖区专项 16 查询 | 2 ✓ |
| `step25_discovery.py` | 渠道发现回写到 渠道目录.md | 2.5 ✓ |
| `step3_filter.py`, `step3prime_filter.py`, `step3d_filter.py` | 标题过滤 + 查重 | 3 |
| `step4_fetch.py`, `step4prime_fetch.py`, `step4d_fetch.py` | 分层抓取 | 4 |
| `step45_regex_extract.py`, `step45_r2.py` | 正则结构化抽取 | 4.5 |
| `prep_review_batch.py`, `prep_review_r2.py` | 给 Agent 的打分批次 | 4.5→5 |
| `step5_ingest.py`, `step5_r2_ingest.py` | 入库 → 01 核心政策/ | 5 |
| `step6_comments.py`, `step6_r2_comments.py` | 找评论入库 → 02 政策评论/ | 6 |

下轮统一参数化、放进 `~/.openclaw/skills/policy-watch/scripts/`。

---

## 给决策层的简要看点(Top 5 政策,综合分 5)

(从 first pass + r2 选,均为 ⭐⭐⭐⭐⭐)

1. **关于完善居民电动汽车充电桩用电价格政策的通知** — 国家发改委
   分时电价直接影响充电站利润,峰谷套利空间。建议立即调整运营策略。
2. **关于推动车网互动规模化应用试点工作的通知(发改办能源〔2024〕718号)** — 国家发改委
   V2G 直接是核心业务,试点窗口有限。建议立即申报试点城市。
3. **国家电力中长期市场基本规则(发改能源规〔2025〕1656号)** — 国家发改委 + 国家能源局
   市场规则定调,影响购电策略。建议组建电力交易研究团队。
4. **福建省充电基础设施体系实施方案(闽发改规〔2024〕5号)** — 福建省发改委
   省级支持力度,补贴 + 电价优惠。建议在福建优先布局。
5. **2024-2025 年节能降碳行动方案(国发〔2024〕12号)** — 国务院
   双碳战略顶层文件,虚拟电厂/V2G/需求响应都有量化目标。战略级跟进。

---

_本报告由 policy-watch skill 首轮(建设期手工)产出,2026-04-25_
