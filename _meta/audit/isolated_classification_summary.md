# Isolated 132 政策分类 — 2026-05-07T13:48:38+08:00

- 总数:**132**
- 平均 confidence:0.847
- 数据源:`_l2_rebuild_state/isolated_classification/results/batch_*.jsonl`
- audit 数据:`_meta/audit/isolated_classification.jsonl`(下次跑覆盖)

## Label 分布

| label | n | % |
|---|---:|---:|
| `index_page` | 30 | 22.7% |
| `news_or_press` | 54 | 40.9% |
| `duplicate_or_alt_version` | 4 | 3.0% |
| `no_vault_basis` | 21 | 15.9% |
| `true_orphan` | 23 | 17.4% |

## Suggested Action 分布

| action | n | % | 处理建议 |
|---|---:|---:|---|
| `exclude_from_main_graph` | 79 | 59.8% | 前端 graph 过滤,不展示主图谱 |
| `cleanup_candidate` | 4 | 3.0% | review 后可下架到 _archive(同政策有更好版本) |
| `keep_with_tag` | 21 | 15.9% | 保留,标 'no_vault_basis',P2.7 候选回填时优先抓上位 |
| `future_refetch` | 8 | 6.1% | 正经政策但 body 不全,需重抓 |
| `accept_orphan` | 20 | 15.2% | 真孤儿(早期/边缘),接受现状 |

## 各 action 政策清单

### `exclude_from_main_graph` (79)

```
P_1900_AH_365ee7cf
P_1900_GO_035b055e
P_1900_GO_3872f513
P_1900_GO_78454068
P_1900_TJ_2473efef
P_2021_GO_b961a331
P_2022_GX_f1d94d34
P_2023_CQ_e490adb4
P_2023_TJ_23242c1b
P_2024_BJ_bb14b4c6
P_2025_BJ_54c00899
P_2025_GO_2060dd14
P_2025_HI_4b282d7d
P_2026_AH_10dda71e
P_2026_GO_4d158ed8
P_2026_SD_d05e6fa9
P_1900_BJ_f1388b92
P_1900_GO_4b5155f5
P_1900_GO_d1101dae
P_1900_GZ_8c89d2d9
P_1900_NX_ffe6eeec
P_1900_SN_41cca677
P_2017_QH_07058af7
P_2021_LN_1ce1fce9
P_2022_HA_3232e2ef
P_2023_GO_0e239de9
P_2024_LN_1979cc90
P_2024_SN_0e8bc123
P_2025_CQ_0515554e
P_2025_GO_fc24f456
P_2025_HN_97f39c45
P_2026_AH_1f64a250
P_2026_OTHER2D4E_0327e7ba
P_2026_SH_583bbba6
P_2026_YN_b2d38b2c
P_1900_CQ_82e7213b
P_1900_GO_565c42a6
P_1900_GO_d589270a
P_1900_HE_e745fde4
P_1900_QH_123e5b27
P_1900_SN_43aa16d7
P_2022_SD_385097d9
P_2024_BJ_04b2f71c
P_2025_GO_3560eda4
P_2025_LN_1b193457
P_2025_SH_01150bf2
P_2026_CQ_02025d8d
P_2026_GO_d859d6d9
P_2026_OTHERD5E7_03169880
P_2026_SH_6e089c0e
P_1900_CQ_965d30b5
P_1900_GO_195b16ea
P_1900_GO_5dff3182
P_1900_GO_e7ac5f2c
P_1900_HN_13866b04
P_1900_QH_1b811389
P_1900_SX_0c8e739a
P_1900_TJ_f6097cc8
P_2024_GO_5dc81faa
P_2025_AH_16e70d4c
P_2025_CQ_a813b653
P_2025_HA_25fbc7b4
P_2025_LN_4f5b9e7c
P_2025_SH_d8527ff1
P_2026_CQ_0275a8b2
P_2026_GO_e0ac73e6
P_2026_SC_01062e80
P_1900_GO_6a44403f
P_1900_GX_42d84277
P_1900_JX_2449ab7d
P_2023_CQ_0406f829
P_2024_GO_8fc095f9
P_2025_AH_48dd3a22
P_2025_GO_1009d2cd
P_2025_HA_2a26e652
P_2025_SN_ee83cfd7
P_2026_GO_47cfdc36
P_2026_SD_2a71e689
P_2026_SX_1e4b199e
```

### `cleanup_candidate` (4)

```
P_2018_GO_ce8700fb
P_2023_NDRC_178
P_2019_BJ_7953e5fb
P_2021_BJ_52a28aed
```

### `keep_with_tag` (21)

```
P_1900_GZ_2dad70b3
P_1900_SN_21047ac7
P_2019_GX_03dd61d7
P_2024_GO_c5b25865
P_2025_OTHERE27E_24
P_2026_SX_bfc68419
P_1900_TJ_95daac5a
P_2020_LN_193563de
P_2025_GO_22391573
P_2025_SD_4bcf1389
P_2026_GO_5c0cf20a
P_1900_GO_0cae0427
P_1900_TJ_9dbe2db1
P_2020_TJ_8b3b418c
P_2025_GZ_154a4cf4
P_2018_TJ_3f5fc84a
P_2020_ZJ_da16f2fb
P_2023_NEA_27
P_1900_QH_d24ac57d
P_1900_SX_8bdfd02b
P_2026_HA_526c08ca
```

### `future_refetch` (8)

```
P_1900_LN_54de50fa
P_2024_SH_242
P_2024_BJ_01265eb0
P_2024_OTHER55FD_08015615
P_2023_BJ_11237d18
P_2024_OTHER7F45_060777c1
P_2026_SX_04010841
P_2025_OTHER9626_9
```

### `accept_orphan` (20)

```
P_2017_NDRC_09206e37
P_2025_GO_bf090cf3
P_2026_NEA_0324cd2a
P_1900_GO_0c246ae8
P_2024_CQ_2
P_2022_CQ_11
P_2024_GO_1c6be4ad
P_2024_YN_f3824736
P_2025_CQ_1a0d5778
P_2022_GO_0729ac2b
P_2024_BJ_05274abd
P_2025_GO_381b8d69
P_1900_GO_02e64a1c
P_1900_GO_26f7dd68
P_1990_NEA_1162
P_2022_GO_6a4cc949
P_2023_SH_146aea94
P_2024_BJ_4327ac6f
P_2024_SH_09f07265
P_2025_GO_7bad0548
```
