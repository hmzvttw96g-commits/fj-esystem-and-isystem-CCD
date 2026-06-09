# Experimental Rerun Comparison - 20260605_183928

本次重跑原因：从 GitHub 仓库 `hmzvttw96g-commits/fj-esystem-and-isystem-CCD` 找到并恢复了 `docs/codex/experimental_analysis_automation.md`，因此重新执行一次 experimental CCD 自动分析流程。

## 对比对象

- 原 latest 对应正式 run：`20260605_182254`
- 本次验证性 run：`20260605_183928`
- 本次 run 使用了 `--no-update-latest`，因此没有覆盖 latest 入口。

## 核心结果对比

| comparison_item | result |
|---|---|
| base_panel | same |
| regression_panel | same |
| regression_model_summary | same |
| regression_coefficients | same |
| required_checks | same |
| heterogeneity_city_path | same |

## 差异源头

核心分析结果没有变化。唯一实质差异来自前置文件状态：

- `20260605_182254` 运行时缺少 `docs/codex/experimental_analysis_automation.md`，manifest 和 summary report 中包含对应 warning。
- `20260605_183928` 运行前已从 GitHub 恢复该文档，因此不再出现该 warning。

输入 Excel、样本城市、样本年份、缺失样本、异常样本和回归可用样本均一致。

## 处理结论

由于核心结果一致，按用户要求不更新 latest。当前 latest 仍保持为 `20260605_182254` 对应结果。
