# Experimental CCD Analysis Summary - 20260605_183928

本次分析基于当前已有实验性 CCD Excel 数据运行，未重新采集数据，未使用 legacy 文件作为输入。

## Warning

输入文件不在项目目录内，已使用外部原始数据路径：/Users/greenbarry/Desktop/finacial system and educational system CCD/当前数据与CCD实验性分析整理_20260604.xlsx

## Input

- 输入文件：`/Users/greenbarry/Desktop/finacial system and educational system CCD/当前数据与CCD实验性分析整理_20260604.xlsx`
- 输入来源不是 `archive/legacy_outputs/`。

## Scope

- 城市：福州、厦门、泉州
- 年份：2019-2024
- 样本数量：18
- 可用于回归样本数量：17

## Missing Samples

| city | year | E_index | I_index | D |
| --- | --- | --- | --- | --- |
| 厦门 | 2022 |  | 0.428571 |  |

## Required Checks

| check_item | result | details |
| --- | --- | --- |
| 厦门 2022 是否 missing_E | True | E_index 缺失 |
| 泉州 2019 是否 I_index=0 | True | I_index=0.0 |
| 泉州 2020 是否 I_index=0 | True | I_index=0.0 |
| D=0 是否由 missing 填 0 导致 | False | 泉州-2019: E=0.230395, I=0.0, D=0.0, has_missing=False；泉州-2020: E=0.151973, I=0.0, D=0.0, has_missing=False |
| 是否有 2025 混入主样本 | False | 主样本已限定 2019-2024 |
| 是否有非福州/厦门/泉州城市混入当前小样本 | False | 无 |
| 是否有 legacy 文件被误用 | False | /Users/greenbarry/Desktop/finacial system and educational system CCD/当前数据与CCD实验性分析整理_20260604.xlsx |
| 是否生成 latest 入口 | True | 脚本将在写出结果后更新 latest 面板和 latest 报告 |
| 是否生成 manifest | True | 脚本将在 run_id audit 目录生成 manifest |

## Outlier Candidates

| city | year | E_index | I_index | D | outlier_notes |
| --- | --- | --- | --- | --- | --- |
| 厦门 | 2020 | 0.131515 | 0.142857 | 0.370228 | E_minus_I=outside_0_1 |
| 厦门 | 2022 |  | 0.428571 |  | E_index=missing；E_minus_I=missing；D=missing |
| 泉州 | 2019 | 0.230395 | 0.0 | 0.0 | I_index=0；D=0 |
| 泉州 | 2020 | 0.151973 | 0.0 | 0.0 | I_index=0；D=0 |
| 泉州 | 2021 | 0.102289 | 0.47619 | 0.469789 | E_minus_I=outside_0_1 |
| 泉州 | 2023 | 0.086702 | 0.142857 | 0.333606 | E_minus_I=outside_0_1 |

## City Path Classification

| city | auto_path_classification | expected_path_classification | match_expected | reason |
| --- | --- | --- | --- | --- |
| 厦门 | 跃迁协调型 | 跃迁协调型 | True | 存在缺失年份，且最高D=0.852 |
| 泉州 | 低位波动型 | 低位波动型 | True | D均值=0.309, 最大值=0.590 |
| 福州 | 稳定提升型 | 稳定提升型 | True | 首年D=0.378, 末年D=0.887, 均值=0.656 |

## Regression Interpretation Notice

当前样本为三市小样本，所有回归结果仅用于 experimental validation，不得作为正式论文因果结论。

## Generated Files

- `/Users/greenbarry/Documents/Codex/2026-06-04/imported-codex-24/data/audit/experimental_analysis/20260605_183928/experimental_data_assets_check_20260605_183928.xlsx`
- `/Users/greenbarry/Documents/Codex/2026-06-04/imported-codex-24/data/panel/experimental_analysis/20260605_183928/experimental_analysis_base_panel_2019_2024_20260605_183928.csv`
- `/Users/greenbarry/Documents/Codex/2026-06-04/imported-codex-24/data/audit/experimental_analysis/20260605_183928/experimental_missing_and_outlier_check_20260605_183928.xlsx`
- `/Users/greenbarry/Documents/Codex/2026-06-04/imported-codex-24/outputs/figures/experimental_analysis/20260605_183928/experimental_CCD_D_trend_by_city_20260605_183928.png`
- `/Users/greenbarry/Documents/Codex/2026-06-04/imported-codex-24/outputs/figures/experimental_analysis/20260605_183928/experimental_CCD_heatmap_city_year_20260605_183928.png`
- `/Users/greenbarry/Documents/Codex/2026-06-04/imported-codex-24/outputs/figures/experimental_analysis/20260605_183928/experimental_E_I_index_trend_by_city_20260605_183928.png`
- `/Users/greenbarry/Documents/Codex/2026-06-04/imported-codex-24/outputs/figures/experimental_analysis/20260605_183928/experimental_E_vs_I_scatter_20260605_183928.png`
- `/Users/greenbarry/Documents/Codex/2026-06-04/imported-codex-24/outputs/tables/experimental_analysis/20260605_183928/experimental_descriptive_statistics_20260605_183928.xlsx`
- `/Users/greenbarry/Documents/Codex/2026-06-04/imported-codex-24/outputs/tables/experimental_analysis/20260605_183928/experimental_regression_panel_20260605_183928.xlsx`
- `/Users/greenbarry/Documents/Codex/2026-06-04/imported-codex-24/outputs/tables/experimental_analysis/20260605_183928/experimental_regression_results_20260605_183928.xlsx`
- `/Users/greenbarry/Documents/Codex/2026-06-04/imported-codex-24/data/audit/experimental_analysis/20260605_183928/experimental_regression_report_20260605_183928.md`
- `/Users/greenbarry/Documents/Codex/2026-06-04/imported-codex-24/outputs/tables/experimental_analysis/20260605_183928/experimental_heterogeneity_analysis_20260605_183928.xlsx`