# 实验性口径检验与探索性回归报告

## 1. 本次运行信息

- run_id：`20260605_184549`
- 输入文件：`/Users/greenbarry/Documents/Codex/2026-06-04/imported-codex-24/data/panel/experimental_analysis/latest_experimental_analysis_base_panel_2019_2024.csv`
- 参考 summary report：`/Users/greenbarry/Documents/Codex/2026-06-04/imported-codex-24/data/audit/experimental_analysis/latest_experimental_analysis_summary_report.md`
- 样本范围：福州、厦门、泉州，2019-2024
- 输出目录：`/Users/greenbarry/Documents/Codex/2026-06-04/imported-codex-24/data/audit/experimental_caliber_tests/20260605_184549`；`/Users/greenbarry/Documents/Codex/2026-06-04/imported-codex-24/outputs/tables/experimental_caliber_tests/20260605_184549`；`/Users/greenbarry/Documents/Codex/2026-06-04/imported-codex-24/outputs/figures/experimental_caliber_tests/20260605_184549`

## 2. 数据使用说明

本轮只使用 latest experimental 面板，不使用 legacy 文件，不重新采集数据，不重新计算原始 E/I 指标，不把 missing 填 0。

## 3. 口径设计

- baseline_full_sample：使用 can_use_for_caliber_test=1 的全部样本。
- exclude_zero_index：剔除 data_status=calculated_zero_index 的样本。
- post_2021_sample：只保留 year>=2021 的可检验样本。
- balanced_years_only：只保留三个城市都有可计算结果的年份；厦门 2022 缺失导致 2022 不纳入。
- non_missing_nonzero：只保留 E_index、I_index、D 均非缺失且 E_index>0、I_index>0 的样本。
- industry_lag_focus：只保留 lag_type=industry_lag 的样本。

## 4. 口径检验结果

| caliber_name | sample_size | mean_D | industry_lag_count | education_lag_count | balanced_count |
| --- | --- | --- | --- | --- | --- |
| baseline_full_sample | 17 | 0.5267135294117646 | 12 | 2 | 3 |
| exclude_zero_index | 15 | 0.596942 | 10 | 2 | 3 |
| post_2021_sample | 11 | 0.6622816363636364 | 8 | 2 | 1 |
| balanced_years_only | 15 | 0.5167816 | 10 | 2 | 3 |
| non_missing_nonzero | 15 | 0.596942 | 10 | 2 | 3 |
| industry_lag_focus | 12 | 0.5549324166666666 | 12 | 0 | 0 |

城市路径分类变化如下：

| city | caliber_name | sample_size | mean_D | start_D | end_D | change_D | dominant_lag_type | dominant_CCD_level | path_type | expected_path_type | matches_expected | path_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 泉州 | exclude_zero_index | 4 | 0.46384825 | 0.469789 | 0.59039 | 0.12060099999999996 | education_lag | 勉强协调 | 波动调整型 | 低位波动型 | False | D均值=0.464, 首末变化=0.121 |
| 泉州 | post_2021_sample | 4 | 0.46384825 | 0.469789 | 0.59039 | 0.12060099999999996 | education_lag | 勉强协调 | 波动调整型 | 低位波动型 | False | D均值=0.464, 首末变化=0.121 |
| 泉州 | non_missing_nonzero | 4 | 0.46384825 | 0.469789 | 0.59039 | 0.12060099999999996 | education_lag | 勉强协调 | 波动调整型 | 低位波动型 | False | D均值=0.464, 首末变化=0.121 |

## 5. 探索性回归结果

所有回归仅用于 experimental validation，不得作为正式论文因果结论。

成功运行模型：

| caliber_name | model_name | n_obs | r_squared | adj_r_squared | warnings |
| --- | --- | --- | --- | --- | --- |
| baseline_full_sample | model_A_E_I_index | 17 | 0.8745049402378052 | 0.8565770745574917 |  |
| baseline_full_sample | model_B_mismatch_abs | 17 | 0.06466130208275045 | 0.002305388888267146 |  |
| baseline_full_sample | model_C_industry_lag_dummy | 17 | 0.02693454533146533 | -0.03793648497977031 |  |
| baseline_full_sample | model_D_E_I_city_FE | 17 | 0.9008140390470406 | 0.8677520520627209 |  |
| exclude_zero_index | model_A_E_I_index | 15 | 0.9835104638423802 | 0.9807622078161102 |  |
| exclude_zero_index | model_B_mismatch_abs | 15 | 0.073341263483651 | 0.0020598222131626986 |  |
| exclude_zero_index | model_C_industry_lag_dummy | 15 | 0.24720380006692777 | 0.18929640007207615 |  |
| exclude_zero_index | model_D_E_I_city_FE | 15 | 0.9878405989831877 | 0.9829768385764627 |  |
| post_2021_sample | model_A_E_I_index | 11 | 0.9812596726134484 | 0.9765745907668104 |  |
| post_2021_sample | model_B_mismatch_abs | 11 | 9.55297742631922e-05 | -0.11100496691748529 |  |
| post_2021_sample | model_C_industry_lag_dummy | 11 | 0.17668221172994525 | 0.08520245747771693 |  |
| post_2021_sample | model_D_E_I_city_FE | 11 | 0.994374917289282 | 0.9906248621488033 |  |
| balanced_years_only | model_A_E_I_index | 15 | 0.8788955696641373 | 0.8587114979414935 |  |
| balanced_years_only | model_B_mismatch_abs | 15 | 0.04514263827590559 | -0.028307928010563144 |  |
| balanced_years_only | model_C_industry_lag_dummy | 15 | 0.021694824824866288 | -0.0535594194193747 |  |
| balanced_years_only | model_D_E_I_city_FE | 15 | 0.918969524930641 | 0.8865573349028975 |  |
| non_missing_nonzero | model_A_E_I_index | 15 | 0.9835104638423802 | 0.9807622078161102 |  |
| non_missing_nonzero | model_B_mismatch_abs | 15 | 0.073341263483651 | 0.0020598222131626986 |  |
| non_missing_nonzero | model_C_industry_lag_dummy | 15 | 0.24720380006692777 | 0.18929640007207615 |  |
| non_missing_nonzero | model_D_E_I_city_FE | 15 | 0.9878405989831877 | 0.9829768385764627 |  |

仅显示前 20 行，共 23 行。

跳过模型：

| caliber_name | model_name | n_obs | skip_reason |
| --- | --- | --- | --- |
| industry_lag_focus | model_C_industry_lag_dummy | 12 | 解释变量无足够变异或完全常数 |

## 6. 稳健性判断

1. baseline_full_sample 的 mean_D=0.527，三市路径仍呈福州较稳步提升、厦门高位跃迁但有缺失、泉州低位波动的格局，支持当前论文方向的实验性描述。
2. 剔除泉州 2019、2020 的 0 值后，mean_D 从 0.527 变为 0.597；路径差异仍存在，但泉州低位特征会被弱化，因此 0 值样本是解释泉州早期低位的重要来源。
3. 只看 2021 年以后，mean_D=0.662，福州、厦门、泉州仍有差异；但样本更少，不能扩大解释。
4. 厦门 2022 缺失导致 balanced_years_only 会排除 2022，这会影响城市年度比较的连续性，但不改变已有年份的方向性判断。
5. industry_lag_focus 样本量为 12，baseline 中 industry_lag_count=12，产业承接滞后判断在多数可计算样本中存在，但仍需结合 I 端口径复核。

## 7. 数据风险

- 厦门 2022 E_index 缺失，影响连续年份比较和 balanced_years_only 口径。
- 泉州 2019、2020 I_index=0，虽然不是 missing 填 0，但对低位波动判断影响明显。
- 三市小样本不能支撑正式因果推断。
- 当前 I 端仍是实验性候选口径，需要复核企业/专利候选。
- 小样本 min-max 标准化可能放大极端值。

## 8. 下一步建议

- 可以继续写实验性结果章节，但需明确 experimental validation。
- 建议立即补厦门 2022 E 端。
- 建议立即复核泉州 2019、2020 I 端。
- 可以开始准备扩展福建 9 市，但不宜跳过缺失和 0 值复核。
- 可以启动正式 C/B/X 口径数据收集，但本轮口径检验不是正式 C/B/X 结果。

## 9. 可写入论文的实验性结论

基于当前福州、厦门、泉州三市 2019-2024 年实验性 CCD 面板，教育端与产业端耦合协调水平呈现明显城市分化。福州整体表现为稳步改善，厦门在部分年份达到较高协调水平但存在 2022 年 E 端缺失，泉州则表现出早期低位与后续波动改善并存的特征。上述结果说明，福建省不同城市在人工智能教育供给与产业承接之间可能存在差异化演进路径。

进一步的实验性口径检验显示，剔除泉州早期 I_index 为 0 的样本后，三市差异仍然存在，但泉州低位特征有所弱化，说明该结论对早期产业端低值具有一定敏感性。因此，当前结果可作为论文初稿中的探索性发现和后续口径设计依据，但仍需补齐厦门 2022 年 E 端数据，并复核泉州 2019、2020 年 I 端口径后，方可进入更正式的实证检验。

## Warnings

输入面板缺少 can_use_for_caliber_test，已按 E_index/I_index/D 非缺失临时派生，未写回 latest 面板。