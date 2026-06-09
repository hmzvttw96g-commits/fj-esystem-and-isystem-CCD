# 2026 年起福建省中职学业水平测试公共基础数学命题趋势分析与模拟卷生成系统

本项目按“2026 年起公共基础考试数学部分合并为单张综合卷”的口径，分析 2022—2025 年真题数学部分、近两年考纲/考试说明，以及厦门市中职公共基础模拟卷线索，生成量化对照、可视化图表、逐题详细知识点 OLS 权重分析、趋势预测、原创模拟卷和答案解析。

说明：当前模拟卷按用户最新指定题型结构生成：15 道选择题（每题 3 分）、5 道填空题（每题 3 分）、4 道解答题（每题 10 分），合计 100 分。

## 目录结构

```text
fj_zhongzhi_public_math_project/
├── data/
│   ├── raw/
│   │   ├── real_papers/2022/
│   │   ├── real_papers/2023/
│   │   ├── real_papers/2024/
│   │   ├── real_papers/2025/
│   │   ├── syllabus/2024/
│   │   ├── syllabus/2025/
│   │   └── crawled_xiamen_public_basic/2022-2025/
│   ├── processed/
│   └── output/
├── scripts/
├── reports/
│   └── charts/
├── generated_papers/
├── logs/
├── temp/
├── requirements.txt
├── README.md
└── run_all.py
```

## 输入文件放置方法

- 真题及公共基础综合卷：`data/raw/real_papers/年份/`
- 考纲和考试说明：`data/raw/syllabus/年份/`
- 厦门市公共基础模拟卷：`data/raw/crawled_xiamen_public_basic/年份/`
- 支持 `.pdf`、`.docx`、`.txt`、`.md`、`.html`、`.xlsx`、常见图片格式。扫描版 PDF 和图片若无 OCR，会进入人工复核表。

## 运行方法

全流程：

```bash
python run_all.py
```

单脚本：

```bash
python scripts/01_crawl_xiamen_public_basic_papers.py
python scripts/02_extract_public_basic_math.py
python scripts/03_analyze_trends_and_quantitative_comparison.py
python scripts/07_analyze_detailed_knowledge_ols.py
python scripts/04_predict_exam_trends.py
python scripts/05_generate_mock_paper.py
python scripts/06_generate_final_report.py
```

## 输出文件

结构化表：

- `data/processed/xiamen_public_basic_sources.xlsx`
- `data/processed/all_public_basic_math_questions.xlsx`
- `data/processed/math_questions_need_manual_review.xlsx`
- `data/processed/quantitative_comparison_results.xlsx`
- `data/processed/detailed_knowledge_ols_analysis.xlsx`
- `data/processed/future_exam_trend_prediction.xlsx`

图表：

- `reports/charts/real_exam_knowledge_trend.png`
- `reports/charts/syllabus_change_trend.png`
- `reports/charts/knowledge_overlap_heatmap.png`
- `reports/charts/question_type_difficulty_correlation.png`
- `reports/charts/score_distribution_stacked.png`
- `reports/charts/high_frequency_coverage.png`
- `reports/charts/comprehensive_trend_relation.png`
- `reports/charts/future_prediction_scores.png`
- `reports/charts/same_year_detail_overlap_heatmap.png`
- `reports/charts/ols_weighted_knowledge_weights.png`

报告：

- `reports/03_厦门公共基础数学卷与福建真题考纲量化对照报告.docx/pdf`
- `reports/04_福建省中职公共基础数学未来命题趋势预测报告.docx/pdf`
- `reports/05_真题与厦门模拟题详细知识点OLS权重分析报告.docx/pdf`
- `reports/福建省中职公共基础数学命题趋势分析与模拟卷生成报告.docx/pdf`

模拟卷：

- `generated_papers/福建省中职学业水平测试公共基础数学模拟卷.docx/pdf`
- `generated_papers/福建省中职学业水平测试公共基础数学模拟卷_答案解析.docx/pdf`
- `generated_papers/模拟卷命题依据表.xlsx`

日志：

- `logs/*.log`

## OCR 失败与人工复核

脚本会记录：

- `chars_extracted`
- `math_chars`
- `question_rows`
- `confidence`
- `ocr_failed`
- `status`
- `notes`

若 PDF 文本层为空、图片无法识别、数学部分定位信心不足，相关记录会写入：

- `data/processed/math_questions_need_manual_review.xlsx`

如需自动识别扫描版 PDF/图片，请安装 Tesseract OCR，并扩展 `scripts/common.py` 中的图片/PDF OCR 逻辑。

## 厦门模拟卷缺失处理

如果没有下载到可解析的厦门市公共基础模拟卷，系统不会假装有样本。相关指标会显示“缺少厦门卷样本”，图表仍会生成，方便看清数据缺口。后续把材料放入 `data/raw/crawled_xiamen_public_basic/年份/` 后，重新运行 `python run_all.py` 即可更新量化指标和报告。

## 量化指标说明

- 知识点重合度：两个资料集合共同覆盖的知识点比例。
- 题型匹配度：选择题、填空题、解答题占比是否接近。
- 难度匹配度：基础、中等、较难占比是否接近。
- 分值占比匹配度：各题型分值分布是否接近。
- 高频考点覆盖率：模拟卷是否覆盖真题前列高频知识点。
- 正相关性：厦门卷与真题知识点频次向量的 Pearson 相关系数。
- 考纲变更关联性：考纲新增/延续知识点与真题、模拟卷出现频次之间的关系。
- 逐题详细知识点重合度：每道真题的详细知识点与同年厦门卷详细知识点的精确重合、宽知识点重合、题型相近和难度相近指标。
- OLS 出卷权重：用同年厦门卷详细知识点占比、考纲覆盖和厦门卷平均难度解释同年真题详细知识点占比，再结合历史真题和 2026 厦门模拟卷形成命题权重。

## 设计原则

1. 单张综合卷分析；模拟卷按最新指定题型结构生成，满分 100 分。
2. 只分析公共基础中的数学部分。
3. 所有图表面向普通读者，尽量直观。
4. 结论必须来自表格、图表或解析日志。
5. 模拟卷题目原创，符合中职数学基础性、情境性和可计算性。
