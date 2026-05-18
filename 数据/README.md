# 数据采集说明

本文件夹用于保存论文指标体系的数据采集程序、原始材料、候选数值和最终面板数据。

## 文件结构

```text
数据/
  scripts/collect_ai_thesis_data.py   数据采集主程序
  config/indicator_catalog.csv        指标目录、口径、来源、检索式
  processed/panel_template.csv        省份-年份-指标面板模板
  processed/search_results.csv        自动检索结果
  processed/numeric_candidates.csv    网页候选数值与上下文
  processed/table_index.csv           自动抽取到的网页表格索引
  processed/manual_todo.csv           需人工/API补充的数据清单
  processed/manual_import_index.csv   手工导入文件索引
  raw/pages/                          下载的公开网页原文
  raw/tables/                         从网页抽取出的表格
  manual_import/                      放置CNKI、企查查、Wind等导出的文件
  logs/run_manifest.json              每次运行记录
```

## 快速运行

先生成指标目录、面板模板和人工补数清单：

```powershell
python "C:\金融专硕\论文\硕士毕业论文_Obsidian_MD统一整理_20260512\数据\scripts\collect_ai_thesis_data.py" --dry-run
```

小规模试爬福建 2024 年三个指标：

```powershell
python "C:\金融专硕\论文\硕士毕业论文_Obsidian_MD统一整理_20260512\数据\scripts\collect_ai_thesis_data.py" --provinces 福建 --start-year 2024 --end-year 2024 --indicators F_FIN_GDP E_AI_MAJOR_COUNT I_AI_COMPANY_COUNT --limit-per-query 2 --download-top-n 1 --max-pages 5
```

全量检索窄样本：

```powershell
python "C:\金融专硕\论文\硕士毕业论文_Obsidian_MD统一整理_20260512\数据\scripts\collect_ai_thesis_data.py" --sample narrow --start-year 2018 --end-year 2024 --limit-per-query 3 --download-top-n 1
```

全量检索核心样本会比较慢：

```powershell
python "C:\金融专硕\论文\硕士毕业论文_Obsidian_MD统一整理_20260512\数据\scripts\collect_ai_thesis_data.py" --sample core --start-year 2018 --end-year 2024 --limit-per-query 3 --download-top-n 1
```

## Tavily 支持

如果系统环境中设置了 `TAVILY_API_KEY`，程序会优先调用 Tavily Search API。没有设置时，会退回 DuckDuckGo HTML 检索。

```powershell
$env:TAVILY_API_KEY="你的 Tavily Key"
python "C:\金融专硕\论文\硕士毕业论文_Obsidian_MD统一整理_20260512\数据\scripts\collect_ai_thesis_data.py" --sample narrow
```

## 人工导入

以下数据通常不能稳定公开爬取，建议从数据库导出后放入 `manual_import/`：

- `CNKI`、`Web of Science`、`Scopus` 的 AI 论文数量
- `企查查`、`天眼查`、`IT桔子`、`清科` 的企业、融资、投资事件数据
- `Wind`、`CSMAR` 的上市公司和融资数据
- `国家知识产权局` 或商业专利库的批量专利检索结果
- 北京大学数字普惠金融指数公开数据包

导入后刷新索引：

```powershell
python "C:\金融专硕\论文\硕士毕业论文_Obsidian_MD统一整理_20260512\数据\scripts\collect_ai_thesis_data.py" --index-manual-imports
```

## 使用原则

自动爬取结果只能作为“候选证据”。写入论文前，应逐条核验 `source_url`、网页时间、统计口径、单位和年份，最终数值填入 `processed/panel_template.csv` 或另存为正式面板数据表。
