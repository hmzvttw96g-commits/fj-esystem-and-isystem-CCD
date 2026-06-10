# Organized CCD Outputs by Time and Topic

本目录是在不移动原始 `data/`、`outputs/` 文件的前提下，为之前运行过的 CCD 分析、口径检验、E/I 端复核和系统边界审计输出建立的按时间与指令主题整理层。

## 目录规则

- `by_time_and_topic/`：按 `YYYY-MM-DD_HH-MM-SS__topic_slug` 建目录。
- `latest_entrypoints/`：集中放最近一次使用的 `latest_*` 便捷入口。
- 每个复制文件命名为：`时间__主题__原文件名`。
- 原始输出仍保留在 `data/` 和 `outputs/` 下，本目录只做便捷归档副本。

## 运行主题

- `2026-06-05_18-22-07__experimental_ccd_initial_failed_run`：实验性 CCD 初跑/失败记录（11 个文件）
- `2026-06-05_18-22-54__experimental_ccd_analysis_run`：实验性 CCD 正式分析（14 个文件）
- `2026-06-05_18-39-28__experimental_ccd_analysis_rerun_with_docs_check`：experimental CCD 文档补齐后复跑/差异比较（15 个文件）
- `2026-06-05_18-45-49__experimental_caliber_tests_and_regression`：口径检验与探索性回归（7 个文件）
- `2026-06-05_22-12-47__i_system_upgrade_assets_dictionary_plan`：I端升级版资产回顾/词典/模板/复核计划（5 个文件）
- `2026-06-06_09-06-32__i_system_upgrade_collection_template_run`：I端岗位技能采集模板运行（3 个文件）
- `2026-06-06_09-25-58__quanzhou_2019_2020_official_job_skill_pilot`：泉州2019/2020官方岗位技能试点采集（5 个文件）
- `2026-06-06_10-05-16__ei_system_boundary_audit_initial`：E/I系统边界审计初版（4 个文件）
- `2026-06-06_17-18-49__quanzhou_private_digital_boundary_collect_v1`：泉州民企数字化岗位采集与边界维护 v1（8 个文件）
- `2026-06-06_17-19-40__quanzhou_private_digital_boundary_collect_v2`：泉州民企数字化岗位采集与边界维护 v2（8 个文件）
- `2026-06-06_17-20-26__quanzhou_private_digital_boundary_collect_latest`：泉州民企数字化岗位采集与边界维护最终版（8 个文件）
- `2026-06-06_17-34-41__xiamen_2022_EB_pdf_recheck_initial`：厦门2022 E端B口径招生计划补齐初版（3 个文件）
- `2026-06-06_17-35-29__xiamen_2022_EB_pdf_recheck`：厦门2022 E端B口径招生计划补齐复核（3 个文件）
- `2026-06-07_09-21-12__hqu_campus_verification_initial`：华侨大学校区归属核验初版（5 个文件）
- `2026-06-07_09-41-13__hqu_campus_verification_final_year_rule`：华侨大学校区归属核验-3+1按最后一年所在地（5 个文件）
- `2026-06-07_09-48-24__three_city_EB_completed_panel`：E端三市2019-2024 B基本口径补齐版面板（2 个文件）

## 索引文件

- `organized_outputs_inventory.xlsx`：总索引，含 run summary、file inventory、latest entrypoints。
- `organized_outputs_inventory.csv`：文件清单 CSV。
- `organized_runs_summary.csv`：运行主题汇总 CSV。

## 安全边界

本目录不包含 `data/raw/`、`data/external/`、`data/source/`、`archive/legacy_outputs/`、`outputs/ccd_outputs/`、PDF、zip、log、tmp、venv 或缓存文件。
