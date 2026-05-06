---
title: Step 5 实体抽取汇总
date: 2026-04-25
---

# Step 5 · 实体抽取汇总

- 输入政策: **273**
- registry 实体: **95**
- 命中实体的政策: **271**
- 零实体命中政策: **2**(召回缺口,LLM 补抽 candidate)
- 平均每政策命中实体: **10.1**
- 已被引用的 canonical: **68/95**
- 孤儿 canonical(0 政策引用): **27**

## type 分布(有政策引用的)
- stakeholder: 30
- org: 18
- region: 9
- theme: 7
- concept: 7

## Top 20 引用最多的实体

| # | canonical_id | 名称 | type | 引用政策数 |
|---|--------------|------|------|:-----:|
| 1 | `state_council` | 国务院 | org | 141 |
| 2 | `nev` | 新能源汽车 | concept | 133 |
| 3 | `rural_revitalization_theme` | 乡村振兴 | theme | 112 |
| 4 | `nea` | 国家能源局 | org | 103 |
| 5 | `region_shanghai` | 上海 | region | 97 |
| 6 | `region_beijing` | 北京 | region | 92 |
| 7 | `region_xinjiang` | 新疆 | region | 88 |
| 8 | `equipment_renewal_theme` | 以旧换新 | theme | 87 |
| 9 | `mof` | 财政部 | org | 82 |
| 10 | `new_ess` | 新型储能 | concept | 77 |
| 11 | `consumer` | 消费者 | stakeholder | 75 |
| 12 | `power_market` | 电力市场 | concept | 75 |
| 13 | `grid_company` | 电网企业 | stakeholder / org | 74 |
| 14 | `green_power_trading_theme` | 绿电交易 | theme | 72 |
| 15 | `carbon_market_theme` | 碳市场 | theme | 71 |
| 16 | `mofcom` | 商务部 | org | 70 |
| 17 | `vpp` | 虚拟电厂 | concept | 69 |
| 18 | `mee` | 生态环境部 | org | 64 |
| 19 | `equipment_renewal` | 设备更新 | concept | 56 |
| 20 | `local_gov` | 地方政府 | org | 56 |

## 孤儿 canonical(0 政策引用,可能是 backup 残余)

- `joint_issuer_8ministries_nev` (工信部等八部门联合发文主体)
- `spic` (国家电力投资集团有限公司)
- `fujian_provincial_gov` (福建省及各市级政府)
- `pilot_county_gov` (试点县政府)
- `us_gov` (美国政府)
- `govt_procurer` (各级预算单位采购人)
- `national_gov_service_platform` (全国一体化政务服务平台)
- `charging_equipment_manufacturer` (充换电设备制造商)
- `ess_industry_company` (新型储能产业企业)
- `load_aggregator` (负荷聚合商)
- `green_power_user` (绿电消费用户)
- `ice_oem` (燃油车企业)
- `commercial_property` (商业地产及商贸流通企业)
- `home_appliance_company` (家电及数码产品企业)
- `heavy_truck_oem` (重卡制造商)
- `public_transit_company` (城市公交及运输企业)
- `transport_industry` (交通运输行业)
- `soe` (国有企业)
- `supply_chain_leader` (供应链领军企业)
- `utility_company` (供水供电供气供热企业)
- `energy_company` (能源企业)
- `export_enterprise` (外向型出口企业)
- `foreign_invested_enterprise_china` (在华外资企业)
- `pilot_project_unit` (试点项目单位与试点城市)
- `professional_service` (专业服务机构)
- `digital_tech_provider` (数智技术服务商)
- `misc_other_concept` (其他)

## 零实体命中政策(召回缺口)

这些政策正文里没有任何 alias 命中,LLM 补抽时优先处理。

- `P_2022_SX_1012250c`
- `P_2023_NDRC_0704ee90`