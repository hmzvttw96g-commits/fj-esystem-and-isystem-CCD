# E 端三市 2019—2024 B 基本口径补齐版面板报告

## 1. 本次运行信息
- run_id：20260607_094824
- source_run_id：20260607_094113
- 输出面板：data/panel/e_system_recheck/20260607_094824/E_B_three_city_2019_2024_completed_panel_20260607_094824.xlsx
- latest 面板：data/panel/e_system_recheck/latest_E_B_three_city_2019_2024_completed_panel.xlsx
- 原 experimental base panel 未覆盖：data/panel/experimental_analysis/latest_experimental_analysis_base_panel_2019_2024.csv

## 2. 数据使用说明
本轮只基于 latest experimental base panel、华侨大学校区核验 latest、厦门/泉州 HQU 重分类 latest 生成 E 端补齐版面板。不重算 CCD，不覆盖原 latest experimental base panel。

## 3. 补齐与重分类规则
- 厦门 2022 `corrected_E_B` 设为 704，即非华侨大学公办主口径 634 + 华侨大学厦门校区确认 B 口径 70。
- 泉州 2022 `corrected_E_B` 设为 1366，即原泉州 1324 + 华侨大学泉州校区确认 B 候选 42。
- 校区不明、source_gap、无计划数记录不进入主值。
- 华侨大学 3+1/跨校区培养按最后一年所在地划分；但无年度计划数时不新增计划数量。

## 4. 三市 E_B 完整性
- 厦门：6/6 年有 corrected_E_B，缺失 0 年。
- 泉州：6/6 年有 corrected_E_B，缺失 0 年。
- 福州：6/6 年有 corrected_E_B，缺失 0 年。

结论：E 端三市小样本 2019—2024 B 基本口径在补齐版面板中已经完整。

## 5. 厦门 2022 状态
厦门 2022 已由原 experimental base panel 中的 `missing_E` / `E_B` 缺失，修正为 `corrected_data_status=calculated`，`corrected_E_B=704`。这只是 E 端补齐版面板状态，不代表已重算 E_index 或 CCD。

## 6. 华侨大学校区重分类影响
- 厦门 2022：original_E_B=，corrected_E_B=704，原因：fill_missing_xiamen_2022_E_B_with_hqu_campus_reclassified_value: strict_public_without_uncertain_hqu=634 + confirmed_hqu_xiamen=70
- 泉州 2022：original_E_B=1324，corrected_E_B=1366，原因：hqu_campus_reclassification_add_confirmed_quanzhou_B_candidate: original_quanzhou_E_B=1324 + confirmed_hqu_quanzhou=42

华侨大学原先在厦门 2022 补齐候选中合计 112 人，本轮按确认校区拆分：厦门校区 B 口径 70 人进入厦门主值；泉州校区 B 候选 42 人进入泉州修正值。校区不明记录不进入主值。

## 7. 是否还存在 E_B 缺失
补齐后 corrected_E_B 缺失数量为 0。不存在 E_B 缺失。

## 8. 下一步建议
建议下一步重新跑 `experimental_analysis_pipeline`，用本轮 `corrected_E_B` 更新 E 端主输入后重新计算 E_index、D 和 CCD，并随后重跑 caliber test。当前文件只是 E 端 B 基本口径补齐面板，不应直接替代 CCD 结果表。
