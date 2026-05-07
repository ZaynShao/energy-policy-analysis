---
title: P0 主题 × P0 省 重抓种子清单
generated_at: 2026-05-07T15:41:45+08:00
generated_by: _meta/scripts/oneshot_build_p0_refetch_seeds.py
r2_cells: 4
r2_urls: 7
r3_cells: 8
r3_urls: 56
---

# P0 主题 × P0 省 重抓种子清单

**生成**: 2026-05-07T15:41:45+08:00

配套 `_meta/audit/p0_gaps_diagnosis.md`(根因诊断)+ `missing_base_policies.md`
(53 个 commentary 引用主版本缺失)。

## 🚨 R2:fetch 失败 url(走 SKILL §A.6 fallback chain)

Phase 1 fetch_candidates.py 失败的 P0×P0 url。**多数是 SSL/TLS 不兼容**
(本机 LibreSSL 2.8.3 + 政府老 https 端点)。

**Fallback chain**(逐级试,首个成功为准):
1. `requests` + 新 OpenSSL Python(`brew install python@3.12` + 重跑 fetch)
2. **playwright/chromium**(浏览器内核宽容老 TLS)
3. **手动浏览器抓**:打开 url → 保存 HTML → 放 `_meta/audit_2026-05-06/manual_staging/<8hash>.md`
4. **换源**:同政策可能在 ndrc.gov.cn / nea.gov.cn / 央媒(人民日报)有镜像

### 充电基础设施 × 江苏

- 中国能源大事年鉴（2024）——电网篇：全国电力市场活跃度不断上升
  - http://jsdsm.fzggw.jiangsu.gov.cn/dsmsite/2jdxw/5407.jhtml

### 配电网开放 × 江苏

- [PDF] 关于印发江苏省售电公司监管实施办法 - 盐城市发展和改革委员会
  - http://jsdsm.fzggw.jiangsu.gov.cn/dsmsite/u/cms/www2/201904/16095053p98b.pdf
- [PDF] 关于印发江苏省售电公司监管实施办法 - 盐城市发展和改革委员会
  - http://jsdsm.fzggw.jiangsu.gov.cn/dsmsite/u/cms/www2/201904/16095053p98b.pdf
- 中国能源大事年鉴（2024）——电网篇：全国电力市场活跃度不断上升
  - http://jsdsm.fzggw.jiangsu.gov.cn/dsmsite/2jdxw/5407.jhtml

### 绿电交易 × 江苏

- 江苏电力市场2022-2025年度交易量价走势分析 - 江苏省电力需求侧 ...
  - http://jsdsm.fzggw.jiangsu.gov.cn/dsmsite/2jdxw/5393.jhtml

### 虚拟电厂 × 江苏

- 两部委：推动光储直柔、虚拟电厂等技术应用主动参与电力需求侧响应
  - http://jsdsm.fzggw.jiangsu.gov.cn/dsmsite/dlggjs/2776.jhtml
- 两部委：推动光储直柔、虚拟电厂等技术应用主动参与电力需求侧响应
  - http://jsdsm.fzggw.jiangsu.gov.cn/dsmsite/dlggjs/2776.jhtml

## 📥 R3:promote 漏 url(走 trigger A SKILL §2 prepare 重抓)

rest 中含 P0×P0 候选(layer_meta 标 P0 主题 + P0 省),Phase 1 因为
`candidates_top600` 600 cutoff 没纳入。本次直接挑出供 trigger A 重抓。

**操作**:
```bash
# 手动列 url → fetch_candidates 单跑(本机 SSL OK 的话)
# 或 normalize_to_raw 后走 trigger A:
python3 _meta/scripts/rebuild_l2.py prepare --trigger pid_change --pids ...
```

### 聚合商接入 × 江苏(8 url)

- 中共南京市委 南京市人民政府
  - https://www.nanjing.gov.cn/zdgk/202601/t20260121_5774264.html
- 对市政协十五届二次会议第0487号提案的答复 - 南京市人民政府
  - https://www.nanjing.gov.cn/xxgkn/jytabljggk/2024njytabl/shizxta/202411/t20241120_5013567.html
- 助力电网系统保持平衡江苏公示首批六大虚拟电厂
  - https://www.zgjssw.gov.cn/yaowen/202411/t20241120_8427783.shtml
- 江苏开展负荷快速响应能力建设工作：支持虚拟电厂 - 国际储能网
  - https://mchuneng.in-en.com/html/chunengy-53602.shtml
- 江苏明确电力市场新型主体可参与交易_中共江苏省委新闻网
  - https://www.zgjssw.gov.cn/yaowen/202501/t20250114_8447507.shtml
- 对市政协十五届三次会议第0485号提案的答复
  - https://www.nanjing.gov.cn/xxgkn/jytabljggk/2025njytabl/shizxta/202512/t20251203_5704597.html
- 全市唯一！全国典型！ - 苏州市吴中区人民政府
  - http://www.szwz.gov.cn/szwz/bmdt/202512/3dfc0be5d98d448494ddc7be4f910798.shtml
- [PDF] 苏州市能源发展“十四五”规划
  - https://www.suzhou.gov.cn/szsrmzf/zfbgswj/202205/c2fda710427a4ab8a5da2eb878a66953/files/9b996439d54547379db320f7f7e77a9b.pdf

### 充电基础设施 × 江苏(10 url)

- [PDF] 苏州市“十四五”电动汽车公共充换电设施规划
  - https://www.suzhou.gov.cn/szsrmzf/zfbgswj/202206/b9152963df214b2b8ba02ad07ab8a80d/files/d57c5f1330b04d2ca7eeb740ccc50282.pdf
- 关于不断完善苏州新能源汽车充电基础设施建设的建议
  - http://minjian.gov.cn/nd.jsp?id=1702&groupId=-1
- 《江苏苏州市新能源汽车充电基础设施建设运营管理办法（公开征求 ...
  - https://chd.in-en.com/html/chd-2439994.shtml
- 对市政协十五届二次会议第446号提案的答复 - 苏州市人民政府
  - http://www.suzhou.gov.cn/szsrmzf/bmwj/202308/fd652a2dcd604daea9cb62b13b900821.shtml
- 关于加强充电桩及配套设施的建设的几点建议
  - http://www.szwz.gov.cn/szwz/qzxtalm/202312/539fceae5ea5406488fc9bdc4352edd7.shtml
- 关于印发《南京市居民区电动汽车充电基础设施建设管理办法》的通知
  - https://jtj.nanjing.gov.cn/njsjtysj/202211/t20221130_3769450.html
- 关于印发《南京市居民区电动汽车充电基础设施建设管理办法》的通知
  - https://jtj.nanjing.gov.cn/zwgk/gzk/202310/t20231013_4030368.html
- 江苏南京CATL超级充换电站正式进入试运营阶段-充电站--国际充换电网
  - https://chd.in-en.com/html/chd-2458742.shtml
- 关于投入居民小区充电桩建设的提案 - 南京市人民政府
  - https://www.nanjing.gov.cn/xxgkn/jytabljggk/2025njytabl/shizxta/202512/t20251203_5704504.html
- [PDF] 苏工信办发〔2022〕113号 - 苏州市人民政府
  - http://www.suzhou.gov.cn/szsrmzf/bmwj/202208/fabd73dc3e0d46efb8bccb961eb510f2/files/004df4e8fa15445f82687d12bb47bafa.pdf

### 充电基础设施 × 广东(11 url)

- 9个城市和30个项目列入首批车网互动规模化应用试点---国家能源局
  - https://www.nea.gov.cn/20250425/6c21959a140744a6bb35916e634cc9b6/c.html
- 深圳市发展和改革委员会关于印发《深圳市支持虚拟电厂加快发展的 ...
  - https://fgw.sz.gov.cn/zwgk/zcjzcjd/gfxwjcx/content/post_11355182.html
- 广东深圳：发布通知征集新能源汽车充电应用场景创新项目
  - https://chd.in-en.com/html/chd-2445949.shtml
- 深圳市住房和建设局关于《电动汽车充电基础设施工程技术规程 ...
  - https://zjj.sz.gov.cn/hdjlpt/yjzj/answer/46570
- 深圳加快建设“超充之城2.0”-产业发展-深圳市发展和改革委员会网站
  - https://fgw.sz.gov.cn/ztzl/qtztzl/szscjmyjjfzzhfwpt/xwdt/cyfz/content/post_12329516.html
- 【关于印发《电动汽车充电设施服务能力“三年倍增”行动方案(2025—2027年)》的通知(发改能源〔2025〕1250号)】-国家发展和改革
  - https://www.ndrc.gov.cn/xxgk/zcfb/tz/202510/t20251015_1401011.html
- 广州市工业和信息化局关于印发进一步加强电动汽车充电基础设施建设运营管理的通知 - 广州市人民政府门户网站
  - https://www.gz.gov.cn/gfxwj/sbmgfxwj/gzsgyhxxhj/content/post_5485528.html
- 广州市工业和信息化委关于印发进一步加强电动汽车充电基础设施建设运营管理的通知 - 广州市人民政府门户网站
  - https://www.gz.gov.cn/gfxwj/sbmgfxwj/gzsgyhxxhj/content/post_5485448.html
- 充电基础设施补贴资金管理办法的通知 - 广州市人民政府
  - https://www.gz.gov.cn/gfxwj/sbmgfxwj/gzsgyhxxhj/content/post_5485523.html
- 广州市海珠区科技工业商务和信息化局关于开展2019-2021年度电动 ...
  - http://www.haizhu.gov.cn/gzhzkgsx/gkmlpt/content/8/8493/post_8493470.html
- 广州市白云区科技工业商务和信息化局关于公开遴选有关机构承担 ...
  - https://www.by.gov.cn/ywdt/tzgg/content/post_10113686.html

### 配电网开放 × 江苏(6 url)

- 织就坚强电网 赋能一流营商环境 ——苏州“十四五”电网发展成就综述 - 苏州市人民政府
  - https://www.suzhou.gov.cn/szsrmzf/szyw/202601/c6042acdb1e94921a1adfa32379e5a44.shtml
- 苏州电网售电量跃居全国城市电网首位 - 江苏省电力需求侧管理平台
  - http://jsdsm.fzggw.jiangsu.gov.cn/dsmsite/2gzdt/1465.jhtml
- [PDF] 增量配电业务改革试点名单
  - https://www.ndrc.gov.cn/xxgk/zcfb/tz/202008/P020200826564030685694.pdf
- 苏州实施10项供电服务提升行动
  - https://www.suzhou.gov.cn/szsrmzf/szyw/202503/7c76fbad5ec74275966b1f9e1635a975.shtml
- 全国首份配电网业务放开实施细则发布- 江苏电力需求侧门户新版
  - http://jsdsm.fzggw.jiangsu.gov.cn/dsmsite/dlggqt/2056.jhtml
- 江苏省投资项目审批监管平台
  - https://tzxm.fzggw.jiangsu.gov.cn/portalopenPublicInformation.do?method=queryExamineByProjectuuid&projectuuid=36357057c2ca45609943f6108957539e

### 新型储能 × 江苏(11 url)

- 省发展改革委关于印发江苏省“十四五”新型储能发展实施方案的通知
  - https://www.wxlx.gov.cn/doc/2023/01/06/3859868.shtml
- 常州发布支持企业创新发展政策，聚焦新能源与绿色转型- 储能 - 低碳网
  - http://www.ditan.com/industry/energy-storage/6797.html
- [PDF] 常州市发展和改革委员会文件
  - https://zx.changzhou.gov.cn/uploadfile/czzx/2024/0925/20240925031024379.pdf
- [DOC] 新型储能试点示范项目公示名单 - 国家能源局
  - http://www.nea.gov.cn/1310757632_17036659274831n.doc
- 常州，“四重身份”开启新型电力系统建设新征程
  - https://www.changzhou.gov.cn/ns_news/185177439890074
- 江苏省发展改革委关于印发江苏省“十四五”新型储能发展实施方案的 ...
  - https://www.wnd.gov.cn/doc/2022/08/11/3730532.shtml
- [PDF] 苏州市能源发展“十四五”规划
  - https://www.suzhou.gov.cn/szsrmzf/zfbgswj/202205/c2fda710427a4ab8a5da2eb878a66953/files/9b996439d54547379db320f7f7e77a9b.pdf
- 全文发布！国家能源局专场新闻发布会实录- 江苏电力需求侧门户新版
  - http://jsdsm.fzggw.jiangsu.gov.cn/dsmsite/2jdxw/4684.jhtml
- 江苏省投资项目审批监管平台
  - https://tzxm.fzggw.jiangsu.gov.cn/portalopenPublicInformation.do?method=querybeianExamineAll&pageSize=20&pageNo=8&apply_project_name=&id=026260a6da4e4110bd2d8c429548bf6b
- 标题
  - https://tzxm.fzggw.jiangsu.gov.cn/portalopenPublicInformation.do?method=goPromotionPage
- 办理结果公示 - 江苏省投资项目审批监管平台
  - https://tzxm.fzggw.jiangsu.gov.cn/tzxmweb/portalopenPublicInformation.do?method=queryExamineAll

### 绿电交易 × 江苏(2 url)

- 江苏：扩大绿电交易供应规模持续推动绿电绿证服务站建设- 江苏电力 ...
  - http://jsdsm.fzggw.jiangsu.gov.cn/dsmsite/2jdxw/5863.jhtml
- 电力长协降价低电价周期来了？ - 江苏省电力需求侧管理平台
  - http://jsdsm.fzggw.jiangsu.gov.cn/dsmsite/2jdxw/5396.jhtml

### V2G(车网互动) × 浙江(2 url)

- 9个城市和30个项目列入首批车网互动规模化应用试点---国家能源局
  - https://www.nea.gov.cn/20250425/6c21959a140744a6bb35916e634cc9b6/c.html
- 车网互动规模化应用渐行渐近 - 浙江省经济信息中心
  - https://zjic.zj.gov.cn/zkdtx/202410/t20241018_22942029.shtml

### 虚拟电厂 × 江苏(6 url)

- 对市政协十五届三次会议第0485号提案的答复
  - https://www.nanjing.gov.cn/xxgkn/jytabljggk/2025njytabl/shizxta/202512/t20251203_5704597.html
- 江苏南京市：打造源网荷储协同的城市级示范与新型能源场景试点
  - https://msolar.in-en.com/html/solar-2457765.shtml
- 中共南京市委 南京市人民政府
  - https://www.nanjing.gov.cn/zdgk/202601/t20260121_5774309.html
- 喜报！首批省级虚拟电厂项目，鼓楼+3！
  - http://www.njgl.gov.cn/ztzl47815/yhyshjzc/gzdt/202601/t20260106_5757823.html
- 2024年国家碳达峰试点（南京江宁经济技术开发区）建设经验
  - https://www.ndrc.gov.cn/fggz/hjyzy/tdftzh/202412/t20241231_1395392.html
- 全球首批“虚拟电厂”标准花落中国- 江苏电力需求侧门户新版
  - http://jsdsm.fzggw.jiangsu.gov.cn/dsmsite/2jdxw/2255.jhtml

## 📌 关联清单

- `_meta/audit/missing_base_policies.md` — 53 个 base pid commentary 引用断
  (含发改环资〔2025〕1745 / 发改能源〔2024〕1128 等 P0 政策)
- `_meta/audit/p0_gaps_diagnosis.md` — R0~R4 漏抓机制诊断
- `_meta/audit/fetch_failed_for_manual.jsonl` — fetch_candidates.py 自动追加
