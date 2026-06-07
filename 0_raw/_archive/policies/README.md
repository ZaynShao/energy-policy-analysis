# _archive/policies — 退役/历史快照存档（move 非 delete）

本目录是 `0_raw/policies/` 的归档区,**不物理删除**以备回收 + 审计留痕。含两类:
- **历史快照**(`__pre_issuer_fix_` / `__pre_classification_` / `__pre_pdfreextract_` / `__pre_date_fix_` 等后缀)
  = 早期在地修改前的备份版本,非本次收口产物。
- **退役非政策污染**(下方分日期记录)= 经判定不是政策原文(新闻/工作信息)而退出 policies/ 的文件。

## 2026-06-07 退役（L1 采集修复 Task12 收口）

L1 gate golden 校准（commit `c77d291`）时抽样核验,发现 2 篇原 vault 存量是**非政策污染**,
gate 正确判它们为 non_policy(误杀=0 的前提是把这 2 篇标对)。退役入档:

- **`P_2024_HE_8b8b5a46`** 〔全国首个电动重卡型虚拟电厂在唐山建成〕
  = **新闻报道**(正文"记者…获悉"句式),非政策文件。来源 fagaiwei.tangshan.gov.cn。
- **`P_2020_LN_e3ff353a`** 〔一批先进经验落地,苏企超千亿投资注入…辽苏合作"步步登高"〕
  = **工作信息/合作动态报道**,非政策文件。来源 辽宁省发展和改革委员会。

回收方式:若日后判定误退,把文件移回 `0_raw/policies/` 即可(pid/frontmatter 原样保留)。
