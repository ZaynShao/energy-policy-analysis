---
title: Step 5 实体抽取汇总
date: 2026-04-25
---

# Step 5 · 实体抽取汇总

- 输入政策: **979**
- registry 实体: **99**
- 命中实体的政策: **940**
- 零实体命中政策: **39**(召回缺口,LLM 补抽 candidate)
- 平均每政策命中实体: **7.0**
- 已被引用的 canonical: **73/99**
- 孤儿 canonical(0 政策引用): **26**

## type 分布(有政策引用的)
- stakeholder: 31
- org: 18
- theme: 11
- region: 9
- concept: 7

## Top 20 引用最多的实体

| # | canonical_id | 名称 | type | 引用政策数 |
|---|--------------|------|------|:-----:|
| 1 | `nea` | 国家能源局 | org | 350 |
| 2 | `power_market` | 电力市场 | concept | 325 |
| 3 | `state_council` | 国务院 | org | 309 |
| 4 | `grid_company` | 电网企业 | stakeholder / org | 289 |
| 5 | `distribution_grid_opening` | 配电网开放 | theme | 278 |
| 6 | `rural_revitalization_theme` | 乡村振兴 | theme | 259 |
| 7 | `nev` | 新能源汽车 | concept | 258 |
| 8 | `new_ess` | 新型储能 | concept | 257 |
| 9 | `vpp` | 虚拟电厂 | concept | 216 |
| 10 | `green_power_trading_theme` | 绿电交易 | theme | 209 |
| 11 | `region_beijing` | 北京 | region | 204 |
| 12 | `power_user` | 电力用户 | stakeholder | 163 |
| 13 | `region_shanghai` | 上海 | region | 163 |
| 14 | `equipment_renewal_theme` | 以旧换新 | theme | 149 |
| 15 | `energy_storage_theme` | 新型储能 | theme | 145 |
| 16 | `region_xinjiang` | 新疆 | region | 143 |
| 17 | `charging_infra` | 充电基础设施 | concept | 142 |
| 18 | `power_generator` | 发电企业 | stakeholder | 136 |
| 19 | `consumer` | 消费者 | stakeholder | 132 |
| 20 | `aggregator_access` | 聚合商准入 | theme | 128 |

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

- `P_2024_GO_cbce5378`
- `P_1900_SN_41cca677`
- `P_2023_GO_0e239de9`
- `P_2019_BJ_7953e5fb`
- `P_2025_GO_4f82af00`
- `P_2021_SC_028ec539`
- `P_2020_GO_5ad272e2`
- `P_1900_GO_6a44403f`
- `P_2022_SX_1012250c`
- `P_2025_SN_73f3b419`
- `P_2025_CQ_a813b653`
- `P_2022_CQ_353802ae`
- `P_2025_GD_b2876ecb`
- `P_2025_GD_399ed9f5`
- `P_2025_GD_1e47cd63`
- `P_2025_GD_badbf18f`
- `P_2026_GD_7da3dcc0`
- `P_2025_GD_b7cfd44d`
- `P_2024_GX_18226505`
- `P_2026_GO_e0ac73e6`
- ... 共 39 条