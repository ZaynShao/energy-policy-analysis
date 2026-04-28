# 策略-公众号补源-wewe-rss

> L1 评论桶补源 SOP。把"行业媒体 / 学术智库 / 学者个人 / 行业垂直号"的微信公众号文章稳定批量同步进 vault `0_raw/commentaries/`。
> 服务对象:补 L2 opinion 覆盖率(目标 20% → 40%+)、补 conflicts_with 转评论层抽取的数据前提
> 上游依赖:微信读书订阅(用户的微信账号)
> 下游消费:`audit_commentaries.py` → `extract_opinions.py` → L2 opinions/themes
> 替代关系:**取代**[[策略-八步采集法]]Step 7 的搜狗微信搜索路径(已实测不可用,详见"路径选型")

---

## 一句话总览

**OrbStack 起 wewe-rss(基于微信读书 API)→ 微信账号扫码 → web UI 订阅核心公众号 → wrapper 拉 fulltext JSON feed → 落 `0_raw/commentaries/`**

wewe-rss 后台预拉全文存 SQLite,wrapper 调用是**纯本地**操作(0 次外部 API 请求),不增加封控压力。

---

## 路径选型(为什么是 wewe-rss)

| 路径 | 数据源 | 拉取方式 | 实测结果 | 状态 |
|---|---|---|---|---|
| 搜狗 type=2(`weixin.sogou.com`) | 搜狗微信搜索网页 | 关键词搜文章 | "中能传媒" 9 条结果 → 3/9 是该号原创,其余是别人转发引用 | ❌ **2026 年实测废弃** |
| 搜狗 type=1 公众号搜索 | weixin.sogou.com 公众号主页 | 主页解析历史文章 | 主页半 sunset,token 过期快,反爬严 | ❌ 工程量大且不稳 |
| **wewe-rss(微信读书)** | 微信读书 App 公众号订阅 | 订阅 → API 拉历史 + 增量 | 393/500 dry-run 已可用,100% 该号原创 | ✅ **主路径** |
| 手动 URL 批量 | 用户在微信里复制单篇链接 → wechat_article_pipeline | 人工攒 URL 文件 | 质量最高,人工成本高 | 🔧 **兜底**(看到一篇好文章临时收) |

**核心机制差异:wewe-rss 是订阅模式,搜狗是关键词搜索模式。订阅模式 = 100% 该号原创,关键词搜索 = 严重杂讯**。

---

## 工具分工

| 工具 | 职责 | 备注 |
|---|---|---|
| **OrbStack** | Mac 本地 Docker(Mac 原生 + 个人免费,不要 Docker Hub 账号) | `brew install --cask orbstack`;比 Docker Desktop 轻 |
| **`cooderl/wewe-rss-sqlite`** | wewe-rss 服务端(SQLite 版,最轻) | 9.3k★,2026-04 仍维护 |
| **微信读书 App** | 提供订阅基础设施 + 反爬代理 | wewe-rss 走作者 `weread.111965.xyz` 转发 |
| **`wewe_rss_to_commentaries.py`** | 拉 fulltext JSON feed → 落 commentaries | vault `_meta/scripts/` |
| **`wechat_article_pipeline.py`** | 兜底:单 URL → Markdown(用户手动场景) | vault `_meta/scripts/`,从桌面 skill vendor 而来 |

---

## 部署 SOP

### 一次性步骤(首次配置)

#### Step 1 · 装 OrbStack
```bash
HOMEBREW_NO_AUTO_UPDATE=1 brew install --cask orbstack
open -a OrbStack
# 等 15 秒,docker shim 注入 PATH
docker ps   # 应看到空表头
```

#### Step 2 · 拉镜像(国内 mirror)

2026 年 Docker Hub 在国内 DNS 被劫持(`*.internet.org` 证书错误),必须走 mirror:

```bash
docker pull docker.1ms.run/cooderl/wewe-rss-sqlite:latest
docker tag docker.1ms.run/cooderl/wewe-rss-sqlite:latest cooderl/wewe-rss-sqlite:latest
```

**Mirror 优先级**(2026-04 实测):`docker.1ms.run` ✓ > `docker.1panel.live` > `dockerpull.com` > daocloud(403)

#### Step 3 · 启动服务

```bash
mkdir -p ~/wewe-rss-data && docker run -d --name wewe-rss \
  -p 4000:4000 \
  -e DATABASE_TYPE=sqlite \
  -e AUTH_CODE=zayn-policy-2026 \
  -e SERVER_ORIGIN_URL=http://localhost:4000 \
  -e FEED_MODE=fulltext \
  -e ENABLE_CLEAN_HTML=true \
  -v ~/wewe-rss-data:/app/data \
  --restart unless-stopped \
  cooderl/wewe-rss-sqlite:latest
```

关键 env:
- `FEED_MODE=fulltext` — 后台预拉全文存 SQLite,wrapper 拉 feed = 0 次微信 API
- `ENABLE_CLEAN_HTML=true` — 服务端清掉公众号噪音 HTML
- `AUTH_CODE` — 管理接口鉴权(`/feeds` 路径不需要,但 `/accounts` 等管理接口需要)

#### Step 4 · 扫码 + 订阅

1. 浏览器开 http://localhost:4000,输入 AUTH_CODE
2. **账号管理** → 添加账号 → 微信扫码(**不要勾"24小时自动退出"**)
3. **公众号源** → 添加 → 粘贴公众号分享链接(微信里随便打开一篇文章 → ··· → 复制链接)

**护账纪律**(降低封控概率):
- 一天只加 5-8 个号,17 个号分 2-3 天加完
- `UPDATE_DELAY_TIME` 调到 120-180s(默认 60s)
- `CRON_EXPRESSION` 改成一天 1 次(默认 2 次)
- 每月 OPML 导出备份(web UI → 导出)到 `_meta/wewe_rss_subscriptions_<date>.opml`

### 周期性步骤(同步 + 落库)

```bash
# 1. 检查服务在跑
docker ps | grep wewe-rss

# 2. 后台已按 cron 自动同步,可手动触发
#    (web UI → 公众号源 → 点"更新全部")

# 3. 拉 wewe-rss → 落 commentaries(增量)
cd "/Users/shaoziyuan/Documents/Zayn Main/政策分析"
python3 _meta/scripts/wewe_rss_to_commentaries.py
# 选项: --dry-run / --since 2026-04-01 / --limit 500 / --timeout 300
```

---

## wrapper 设计要点

### 接口

```bash
python3 _meta/scripts/wewe_rss_to_commentaries.py \
    [--base-url http://localhost:4000] \
    [--output-dir <vault>/0_raw/commentaries] \
    [--since YYYY-MM-DD] \
    [--limit 500] \
    [--timeout 300] \
    [--dry-run]
```

### 内部流程

1. `GET /feeds/all.json?limit=N` — JSON Feed 1.0 风格(注意:用单数 `author` 不是 `authors`,日期是 `date_modified` 不是 `date_published`)
2. URL 去重:扫现有 `0_raw/commentaries/*.md` 提取 frontmatter `source_url` 字段建 set
3. since 过滤:可选,只同步指定日期之后的
4. HTML → Markdown:复用 `wechat_article_pipeline.HTMLToMarkdownParser`,传 NoOpImageDownloader(图片保留 mmbiz URL,不下载)
5. 写文件:`<safe_title>.md` + frontmatter(`source_account` / `source_url` / `date_published` / `fetched_at` / `commentary_type: 待分类` / `business_tag` / `source: wewe-rss`)
6. 收尾按号统计

### 业务标签 mapping(脚本内置)

| 业务线 | 公众号 |
|---|---|
| **power**(电力 / 储能 / VPP) | 中能传媒研究院 / 中国电力企业联合会 / 储能与电力市场 / 电力市场与价格洞察 / 高工储能 / 国网能源研究院有限公司 |
| **charging**(充电 / V2G) | 电动汽车观察家 |
| **gas**(加油站转型) | 中国石油经济技术研究院 / 卓创资讯 / 隆众资讯 |
| **cross**(跨业务) | 落基山研究所 / 36碳 / 金杜律师事务所 / 中央财经大学 IIGF / 中国(深圳)综合开发研究院 / 人民网研究院 / 能源评论 |

新加号要更新 `ACCOUNT_BUSINESS_MAP` dict,匹配不到的默认 `cross`。

---

## 已知陷阱

### 陷阱 1 · 直觉合理 ≠ 实际正确

**错误思路**:"用 wewe-rss 拉标题 + wechat-article-to-markdown 抓正文,分散风控池减少封控"

**实际错向**:
- wewe-rss 后台同步是它**自己控制频率**(MAX_REQUEST_PER_MINUTE / UPDATE_DELAY_TIME / CRON_EXPRESSION 三层节流,本就是为防封设计)
- `FEED_MODE=fulltext` 时 wrapper 拉 feed = **本地 SQLite 读**,0 次微信 API
- 走 wechat-article-to-markdown 直连 mp.weixin.qq.com = 多一层抓取 + **公网 IP 反爬池**
- 双重抓取不是分担,是**叠加**

**正确护账**:调高 wewe-rss 节流参数 + 分天加号 + 备份 OPML。

### 陷阱 2 · 国内网络

| 现象 | 原因 | 解 |
|---|---|---|
| `brew` 卡在 "Auto-updating Homebrew..." | 国内 GitHub 慢 | `HOMEBREW_NO_AUTO_UPDATE=1` |
| `docker.io` 报 `*.internet.org` 证书错 | 运营商 DNS 劫持 | 走 `docker.1ms.run` mirror |
| 拉镜像 `403 Forbidden` | 部分 mirror 已关停(daocloud) | 换 mirror |

### 陷阱 3 · 终端 bracketed paste

多行命令带 `\` 粘贴时 zsh 把 `[200~` 当 pattern 报错。**改成单行命令**(用 `&&` 链)。

### 陷阱 4 · OrbStack 装好但 docker 命令找不到

需要 `open -a OrbStack` 启动 app,等 ~15 秒 docker shim 才注入 PATH。

### 陷阱 5 · wewe-rss 单作者依赖

`weread.111965.xyz` 是项目作者 cooderl 自己的转发代理。**风险**:
- 项目跑路 → 服务挂
- 备用 `weread.965111.xyz`
- 长期可 fork 改 `PLATFORM_URL` 自建

### 陷阱 6 · 微信读书账号封控

短时大量加号会被封 24h(README 明确警告)。
- 大号风险高,长期切小号最稳
- 每月 OPML 导出 → 万一被封,新号扫码 + 导入 OPML 重建,5 分钟

### 陷阱 7 · `content_html` 中的 mmbiz 图片

JSON feed 里图片是 `https://mmbiz.qpic.cn/...` URL,Obsidian 加载需要走代理,且图床有 referer 检查。短期接受图片不显示,长期可:
- 在 wrapper 里下载图到本地 `<safe_title>_img/`
- 或在 obsidian 配 referer rewrite

---

## 验证手段

### self-test(不访问网络)

```bash
python3 _meta/scripts/collect_wechat_account.py --self-test  # 老脚本,parser 验证
```

### dry-run

```bash
python3 _meta/scripts/wewe_rss_to_commentaries.py --dry-run --limit 50
```

应看到 account / business_tag 都填上,by_account 分布合理。

### 实抓后验证

```bash
# 1. 查 0_raw/commentaries/ 数量
ls "/Users/shaoziyuan/Documents/Zayn Main/政策分析/0_raw/commentaries/" | wc -l

# 2. 跑 daily_lint
python3 _meta/scripts/daily_lint.py

# 3. 查 _global_index 数字
head -10 "/Users/shaoziyuan/Documents/Zayn Main/政策分析/2_crystallized/_global_index.md"
```

### 抽 5 篇人肉 spot check

- frontmatter 完整(7 个字段)?
- 正文有内容(非空)?
- source_account 跟订阅清单一致?
- date_published 在合理时间窗?

---

## 与八步采集法的关系

| 八步采集法 | 旧路径 | 新路径(本 skill) |
|---|---|---|
| Step 7 公众号历史翻页 | 搜狗 type=1 + wechat-article-to-markdown | wewe-rss + `wewe_rss_to_commentaries.py` |
| Step 6 单文章抓取 | wechat-article-to-markdown | 仍用,但只在用户手动复制 URL 时 |

**[[策略-八步采集法]]需要 update**:Step 7 段落标注"搜狗路径已废弃,见 [[策略-公众号补源-wewe-rss]]"。

---

## 维护责任

- 每月一次 OPML 备份 → vault `_meta/`
- 每月一次跑 wrapper 增量同步
- mirror 列表每半年 review(国内可用 mirror 变化快)
- wewe-rss 项目 watch GitHub release(major 升级要测兼容)
