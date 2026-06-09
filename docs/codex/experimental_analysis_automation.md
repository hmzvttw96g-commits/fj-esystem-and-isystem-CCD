# Codex 自动化执行方案：实验性 CCD 数据核验、可视化、回归准备与异质性分析

> 来源：GitHub 仓库 `hmzvttw96g-commits/fj-esystem-and-isystem-CCD` 的 `docs/codex/experimental_analysis_automation.md`。  
> 适用阶段：当前小样本实验性 E-I CCD 验证阶段。  
> 当前目标：不是最终论文实证，而是用已收集数据自动完成数据核验、图表输出、回归面板准备、探索性回归和异质性分析。  
> 核心原则：不重新采集数据、不覆盖原始文件、不把 missing 填 0、所有输出标记 experimental。

---

## 1. 当前研究状态判断

当前小样本实验性 CCD 可用于方向验证：

- E 端已有福建省普通高校招生计划册整理出的城市-年份教育端变量；
- I 端已有福州、厦门、泉州三市的企业存量与专利申请实验性候选变量；
- CCD 已形成三市 2019-2024 年实验性结果；
- 当前结果能显示福州、厦门、泉州的路径差异；
- 当前数据仍不能作为最终论文结论。

下一步应先完成：

1. 数据底表锁定；
2. 缺失与异常核验；
3. CCD 可视化；
4. 回归面板准备；
5. 探索性回归；
6. 城市异质性与阶段性判断；
7. 输出自动化报告。

---

## 2. 输入文件要求

Codex 应优先查找：

```text
当前数据与CCD实验性分析整理_20260604.xlsx
```

如果文件不在根目录，应在以下目录自动搜索：

```text
data/
data/raw/
data/interim/
data/panel/
data/audit/
.
```

Excel 应包含或尽量包含以下工作表：

```text
00_总览
01_数据资产清单
02_E端城市年份输入
03_E端学校年份汇总
04_E端缺失核查
05_来源文件筛选
06_口径字典
07_CCD结果总表
08_CCD城市均值
09_CCD年份均值
10_滞后类型
11_异常检查
12_论文实验性结论
13_CCD趋势数据
14_下一步验证清单
```

如果部分工作表不存在，不要中止，应写入报告说明缺失。

---

## 3. 输出目录

新输出文件应放入：

```text
data/audit/experimental_analysis/
outputs/figures/experimental_analysis/
outputs/tables/experimental_analysis/
```

结合版本规则，正式归档结果必须进入带 `run_id` 的子目录，latest 只作便捷入口。

---

## 4. 数据资产核验

读取 Excel 全部 sheet，并生成数据资产核验文件。建议包含：

1. `sheet_inventory`：每个 sheet 的行数、列数、字段名；
2. `missing_sheets`：缺失的预期 sheet；
3. `raw_column_map`：自动识别的关键字段映射；
4. `notes`：读取异常说明。

字段识别需要兼容中文和英文：

```text
城市: 城市, city
年份: 年份, year
CCD值: D, CCD, coordination_degree, coupling_coordination_degree
等级: 等级, CCD_level, level
E指数: E_index, education_index, E综合指数
I指数: I_index, industry_index, I综合指数
滞后类型: lag_type, 滞后类型
```

---

## 5. 实验分析底表

输出：

```text
data/panel/experimental_analysis_base_panel_2019_2024.csv
```

建议字段：

```text
city
year
E_raw
I_firm_raw
I_patent_raw
I_job_raw
E_index
I_index
E_minus_I
D
CCD_level
lag_type
data_status
can_use_for_regression
can_use_for_caliber_test
notes
```

样本范围：

```text
福州
厦门
泉州
2019-2024
```

缺失处理：

1. E_index 缺失：`data_status = missing_E`，`can_use_for_regression = 0`，`can_use_for_caliber_test = 0`，`lag_type = missing`。
2. I_index 缺失：`data_status = missing_I`，`can_use_for_regression = 0`，`can_use_for_caliber_test = 0`，`lag_type = missing`。
3. E_index 和 I_index 都存在但其中一个为 0：`data_status = calculated_zero_index`，可用于回归和口径检验；notes 说明 0 值来自标准化或真实计算结果，不是 missing 自动填 0。
4. E_index、I_index、D 均存在：`data_status = calculated`，可用于回归和口径检验。

滞后类型判断：

```text
if missing: lag_type = missing
elif abs(E_index - I_index) <= 0.05: lag_type = balanced
elif E_index > I_index: lag_type = industry_lag
elif E_index < I_index: lag_type = education_lag
```

---

## 6. 缺失与异常核验

输出：

```text
data/audit/experimental_analysis/experimental_missing_and_outlier_check.xlsx
```

建议工作表：

1. `sample_coverage`：3 市 x 6 年完整样本矩阵；
2. `missing_records`：缺失样本；
3. `zero_index_records`：E_index=0 或 I_index=0 样本；
4. `D_zero_records`：D=0 样本；
5. `outlier_records`：D、E_index、I_index 极端样本；
6. `xiamen_2022_check`；
7. `quanzhou_2019_2020_check`；
8. `manual_review_required`。

重点检查：

```text
厦门 2022 是否 missing_E
泉州 2019 是否 I_index=0
泉州 2020 是否 I_index=0
D=0 是否来自 missing 填 0
是否存在 2025 年混入主样本
是否存在非福州/厦门/泉州城市混入当前小样本
```

---

## 7. CCD 可视化

输出目录：

```text
outputs/figures/experimental_analysis/
```

应生成：

```text
experimental_CCD_D_trend_by_city.png
experimental_CCD_heatmap_city_year.png
experimental_E_I_index_trend_by_city.png
experimental_E_vs_I_scatter.png
```

图表标题必须注明 experimental。E-I 散点图建议加 45 度参考线，用于展示 E/I 谁领先。

---

## 8. 描述性统计与相关性

输出：

```text
outputs/tables/experimental_analysis/experimental_descriptive_statistics.xlsx
```

建议工作表：

1. `overall_descriptive`;
2. `by_city_descriptive`;
3. `by_year_descriptive`;
4. `correlation_matrix`;
5. `lag_type_counts`;
6. `CCD_level_counts`。

如变量不存在，跳过并在 notes 中说明。

---

## 9. 探索性回归准备

输出：

```text
outputs/tables/experimental_analysis/experimental_regression_panel.xlsx
```

只保留可用于回归的样本，不得包含 missing_E、missing_I、missing_D。报告中必须写明：

```text
当前样本为三市小样本，回归仅用于方向验证，不得作为正式论文因果结论。
```

---

## 10. 探索性回归

输出：

```text
outputs/tables/experimental_analysis/experimental_regression_results.xlsx
data/audit/experimental_analysis/experimental_regression_report.md
```

可运行模型：

```text
D_it = α + β1 E_index_it + β2 I_index_it + ε_it
D_it = α + β1 abs(E_index_it - I_index_it) + ε_it
D_it = α + β1 E_raw_it + β2 I_firm_raw_it + β3 I_patent_raw_it + ε_it
```

样本量小或变量缺失时跳过不适合的模型。不要声称因果关系；样本量小于 15 时只做描述性回归，不强调显著性。

---

## 11. 异质性分析

输出：

```text
outputs/tables/experimental_analysis/experimental_heterogeneity_analysis.xlsx
```

建议工作表：

1. `city_path_type`;
2. `city_mean_D`;
3. `city_lag_type_distribution`;
4. `year_mean_D`;
5. `level_distribution_by_city`;
6. `stage_interpretation_placeholder`。

当前预期分类：

```text
福州：稳定提升型
厦门：跃迁协调型，但 2022 缺失需要说明
泉州：低位波动型
```

自动分类若不同，不要强行改，应在报告中说明原因。

---

## 12. Markdown 总报告

输出：

```text
data/audit/experimental_analysis/experimental_analysis_summary_report.md
```

报告必须明确：

```text
当前结果仅用于 experimental validation，不能作为 final empirical conclusion。
```

建议结构：

1. 数据来源与样本范围；
2. 数据资产核验；
3. 缺失值与异常值；
4. CCD 趋势与城市差异；
5. E/I 滞后类型判断；
6. 描述性统计；
7. 探索性回归结果；
8. 异质性分析；
9. 当前结论是否支持论文方向；
10. 不能用于正式论文结论的风险；
11. 下一步数据补充建议。

---

## 13. 人工复核点

自动完成后重点复核：

1. 厦门 2022 是否仍然缺失；
2. 泉州 2019、2020 的 0 是否为 calculated_zero_index；
3. 是否有 missing 被填成 0；
4. 图表趋势是否符合前期判断；
5. 回归样本数是否足够；
6. 报告是否明确 experimental；
7. 下一步是否建议补数据或进入口径检验。

---

## 14. 当前结论边界

当前小样本实验仅用于方向验证。建议顺序：

1. 完成当前三市实验性自动分析；
2. 补齐厦门 2022 E 端；
3. 复核 I 端企业和专利候选；
4. 再扩展福建 9 市；
5. 最后做 C/B/X 口径检验和探索性回归。
