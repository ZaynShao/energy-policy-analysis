---
title: Step 5 实体抽取汇总
date: 2026-04-25
---

# Step 5 · 实体抽取汇总

- 输入政策: **289**
- registry 实体: **88**
- 命中实体的政策: **282**
- 零实体命中政策: **7**(召回缺口,LLM 补抽 candidate)
- 平均每政策命中实体: **8.1**
- 已被引用的 canonical: **60/88**
- 孤儿 canonical(0 政策引用): **28**

## type 分布(有政策引用的)
- stakeholder: 29
- org: 18
- region: 9
- concept: 7

## Top 20 引用最多的实体

| # | canonical_id | 名称 | type | 引用政策数 |
|---|--------------|------|------|:-----:|
| 1 | `nev` | 新能源汽车 | concept | 141 |
| 2 | `state_council` | 国务院 | org | 138 |
| 3 | `nea` | 国家能源局 | org | 107 |
| 4 | `region_shanghai` | 上海 | region | 97 |
| 5 | `equipment_renewal` | 设备更新 | concept | 95 |
| 6 | `region_beijing` | 北京 | region | 94 |
| 7 | `mof` | 财政部 | org | 86 |
| 8 | `vpp` | 虚拟电厂 | concept | 83 |
| 9 | `region_xinjiang` | 新疆 | region | 82 |
| 10 | `consumer` | 消费者 | stakeholder | 82 |
| 11 | `new_ess` | 新型储能 | concept | 80 |
| 12 | `power_market` | 电力市场 | concept | 75 |
| 13 | `mofcom` | 商务部 | org | 74 |
| 14 | `v2g` | 车网互动 | concept | 71 |
| 15 | `grid_company` | 电网企业 | stakeholder / org | 65 |
| 16 | `mee` | 生态环境部 | org | 63 |
| 17 | `charging_infra` | 充电基础设施 | concept | 59 |
| 18 | `region_tianjin` | 天津 | region | 54 |
| 19 | `region_liaoning` | 辽宁 | region | 54 |
| 20 | `local_gov` | 地方政府 | org | 53 |

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
- `high_energy_user` (重点用能企业)
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

- `P_2025_OTHERE27E_24`
- `P_2022_SX_1012250c`
- `P_0000_OTHERDA8B_0000bc05`
- `P_2024_NM_0101e295`
- `P_2024_CQ_162`
- `P_2026_CQ_0130f748`
- `P_2022_CQ_08252433`