# DOCX 兜底抓取报告 — 2026-05-07T13:51:52+08:00

- 待抓 URL: **20**(去重 from fetch_top600.log + fetch_retry.log)
- 成功: **20**
- 失败: **0**
- 成功率: 100.0%

## 成功列表

| hash | body_len | url |
|---|---:|---|
| 58d9cbf8 | 1314 | http://fgw.hunan.gov.cn/fgw/xxgk_70899/tzgg/202006/12293420/files/5409190768154b038748311a9d8f6f5d.d |
| bd5f6b0b | 7441 | http://fgw.hunan.gov.cn/fgw/xxgk_70899/tzgg/202310/31806161/files/72f711c95ad44c4c90b19b424988cdff.d |
| fa33e97d | 17640 | http://fgw.hunan.gov.cn/fgw/xxgk_70899/tzgg/202310/31806161/files/8accde15376c4457898eadfe19012cf1.d |
| d6cedc7b | 30603 | http://fgw.hunan.gov.cn/fgw/xxgk_70899/tzgg/202310/31806161/files/a161c02cd91d4aa1a8453b02ff9bcf9d.d |
| eb1ce6e5 | 1098 | http://fgw.hunan.gov.cn/fgw/xxgk_70899/tzgg/202404/33267399/files/0294e96feabb4692a801034fecef9f04.d |
| c19c575f | 1373 | http://fgw.hunan.gov.cn/xxgk_70899/tzgg/202404/33275558/files/45d13595f83c47cc81ecd9f567663ccc.docx |
| c482d8cd | 4704 | http://fgw.qinghai.gov.cn/xwzx/tzgg/202509/P020250925549022357022.docx |
| 88e46ed2 | 4467 | http://fgw.qinghai.gov.cn/zfxxgk/sdzdgknr/fgwwj/202504/W020251104622234599794.docx |
| 62b7d86b | 4474 | http://fgw.qinghai.gov.cn/zfxxgk/sdzdgknr/fgwwj/202510/W020251009468518682940.docx |
| eb60c706 | 4484 | http://plan.hainan.gov.cn/sfgw/0400/202205/c0c54c35e9184c80b137258af8e28050/files/f1050a67ecb3473db5 |
| 9496f106 | 6638 | http://plan.hainan.gov.cn/sfgw/zjdc/202303/8243bdb308a546eb8210a1dfbf0d469d/files/ccf55865ffda4e94b7 |
| e30bc1a8 | 9438 | http://plan.hainan.gov.cn/sfgw/zjdc/202506/362bf10db972463b9d5004defde78267/files/ae17f882cbc34d59ae |
| 921af1ca | 1424 | https://fgw.hunan.gov.cn/fgw/xxgk_70899/tzgg/202412/33551104/files/bcf774f8caf54badb60eb3c0f6c2fe6c. |
| 26ac2af3 | 62206 | https://fgw.shanxi.gov.cn/ztzl/sxzcq/gzdt/202601/P020260106608025126836.docx |
| d99f3f55 | 4653 | https://fzgg.tj.gov.cn/xxfb/tzggx/202204/W020220414627847426485.docx |
| f28e9cd5 | 51558 | https://fzggw.nx.gov.cn/tzgg/202509/P020250926635970809300.docx |
| 33025ab3 | 2752 | https://hbdrc.hebei.gov.cn/cy_new/zcfg/jjyx/202312/W020231214318381593978.docx |
| 91f40b1e | 611 | https://plan.hainan.gov.cn/sfgw/zjdc/202503/4ce0bb02c15249ff88cd83525383f240/files/5f65770a7518476a9 |
| 810d55b2 | 32106 | https://sndrc.shaanxi.gov.cn/zfxxgk/zc/fgwj/sfzggwwj/2021/202304/P020241106545906245718.docx |
| 08bf4022 | 5569 | https://www.bjrd.gov.cn/zyfb/202603/P020260330620039834531.docx |

## 失败列表

| hash | error | url |
|---|---|---|

## 下一步

成功 staging 在 `_meta/audit_2026-05-06/docx_staging/<hash>.md`,
走 normalize_to_raw.py 入 vault → trigger A 全套(rel_judge + 5C)
需要 LLM 调用,作为后续作业。