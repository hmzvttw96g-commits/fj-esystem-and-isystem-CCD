# Codex Output Versioning Rules

本文件规定实验性 CCD 分析及后续相关任务的输出版本管理规则。

## 基本原则

1. 原始数据永不覆盖。
2. 所有 `experimental` 输出必须进入 `run_id` 子目录。
3. 所有正式归档文件名必须包含 `experimental` 和 `run_id`。
4. `latest` 文件可以覆盖，但只作为便捷入口，不作为唯一归档。
5. 不允许再生成 `outputs/ccd_outputs/CCD回归面板数据.xlsx` 这类无 `run_id`、无 `experimental`、无样本范围说明的旧式输出文件。
6. 旧式散落文件统一放入 `archive/legacy_outputs/`。
7. 每次运行必须生成 `experimental_run_manifest_{run_id}.json`。

## 推荐目录结构

正式实验性分析输出应写入以下目录：

```text
data/audit/experimental_analysis/{run_id}/
data/panel/experimental_analysis/{run_id}/
outputs/figures/experimental_analysis/{run_id}/
outputs/tables/experimental_analysis/{run_id}/
```

便捷入口文件可以写在对应目录根部：

```text
data/panel/experimental_analysis/latest_experimental_analysis_base_panel_2019_2024.csv
data/audit/experimental_analysis/latest_experimental_analysis_summary_report.md
```

## 文件命名规则

正式归档文件名至少包含：

```text
experimental
run_id
样本范围或年份范围
文件用途
```

示例：

```text
experimental_base_panel_2019_2024_{run_id}.csv
experimental_ccd_results_2019_2024_{run_id}.xlsx
experimental_summary_report_2019_2024_{run_id}.md
experimental_run_manifest_{run_id}.json
```

## latest 文件规则

`latest` 文件只用于降低人工查找成本：

1. 可以覆盖。
2. 必须来自某个带 `run_id` 的正式结果。
3. 不得作为唯一保存版本。
4. 不得由 legacy 文件直接生成。
5. 更新 latest 时必须同步更新对应 run manifest 或审计说明。

## legacy 文件规则

旧式散落输出统一复制到：

```text
archive/legacy_outputs/
```

legacy 文件只用于追溯，不作为最新分析入口。凡是位于旧目录、没有 `experimental`、没有 `run_id` 或无法确认生成口径的输出，均应在清单中标记为 `legacy_reference_only`、`possible_previous_panel`、`possible_previous_report`、`do_not_use_for_latest_analysis` 或 `needs_manual_review`。

## Manifest 要求

每次正式运行必须生成：

```text
experimental_run_manifest_{run_id}.json
```

manifest 至少记录：

```text
run_id
created_at
input_files
output_files
sample_range
script_version_or_commit
parameters
notes
```
