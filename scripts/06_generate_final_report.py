from __future__ import annotations

from pathlib import Path

from common import CHARTS_DIR, GENERATED_DIR, LOGS_DIR, PROCESSED_DIR, REPORTS_DIR, create_docx_report, create_pdf_text, read_xlsx_rows, setup_logger


logger = setup_logger("generate_final_report", LOGS_DIR / "generate_final_report.log")


def safe_rows(path: Path, sheet: str):
    if path.exists():
        return read_xlsx_rows(path, sheet)
    return []


def val(metrics, name: str):
    for r in metrics:
        if r.get("metric") == name:
            return r.get("value") if r.get("value") is not None else r.get("status")
    return "未生成"


def coef_val(rows, term: str):
    for r in rows:
        if r.get("term") == term:
            return r.get("coefficient")
    return "未生成"


def main() -> None:
    logger.info("Start final report")
    questions = safe_rows(PROCESSED_DIR / "all_public_basic_math_questions.xlsx", "questions")
    file_status = safe_rows(PROCESSED_DIR / "all_public_basic_math_questions.xlsx", "file_status")
    sources = safe_rows(PROCESSED_DIR / "xiamen_public_basic_sources.xlsx", "sources")
    metrics = safe_rows(PROCESSED_DIR / "quantitative_comparison_results.xlsx", "quantitative_metrics")
    prediction = safe_rows(PROCESSED_DIR / "future_exam_trend_prediction.xlsx", "trend_prediction")
    directions = safe_rows(PROCESSED_DIR / "future_exam_trend_prediction.xlsx", "direction_summary")
    blueprint = safe_rows(GENERATED_DIR / "模拟卷命题依据表.xlsx", "blueprint")
    ols_path = PROCESSED_DIR / "detailed_knowledge_ols_analysis.xlsx"
    ols_corr = safe_rows(ols_path, "same_year_detail_correlation")
    ols_coef = safe_rows(ols_path, "ols_coefficients")
    ols_weighted = safe_rows(ols_path, "ols_weighted_blueprint")

    real_count = sum(1 for r in questions if r.get("source_type") == "real_paper_math_part" and r.get("question_type") in {"选择题", "填空题", "解答题"} and not r.get("needs_manual_review"))
    xiamen_count = sum(1 for r in questions if r.get("source_type") == "xiamen_public_basic_mock" and r.get("question_type") in {"选择题", "填空题", "解答题"} and not r.get("needs_manual_review"))
    review_count = sum(1 for r in safe_rows(PROCESSED_DIR / "math_questions_need_manual_review.xlsx", "manual_review"))
    top_points = "、".join([r.get("knowledge_point") for r in prediction[:7] if r.get("knowledge_point")]) or "暂无"
    high_direction = next((r.get("content") for r in directions if r.get("category") == "高频考点"), top_points)
    xiamen_corr = val(metrics, "厦门卷与真题正相关性")
    syllabus_overlap = val(metrics, "考纲 vs 真题知识点重合度")
    ols_r2 = coef_val(ols_coef, "R2")
    top_ols_points = "、".join([str(r.get("detailed_knowledge_point")) for r in ols_weighted[:8] if r.get("detailed_knowledge_point")]) or "暂无"

    sections = [
        {
            "heading": "一、先看结论",
            "paragraphs": [
                "本项目已按新的研究口径重建：2026年起公共基础数学按单张综合卷分析；模拟卷按用户最新指定题型结构生成。",
                f"本轮自动解析出可用真题数学题 {real_count} 道；可用厦门公共基础模拟卷数学题 {xiamen_count} 道；需人工复核记录 {review_count} 条。",
                f"从现有数据看，优先关注的知识点是：{high_direction}。",
                f"考纲与真题知识点重合度为：{syllabus_overlap}。厦门卷与真题正相关性为：{xiamen_corr}。",
                f"逐题详细知识点层面已新增OLS回归权重分析，模型R2为：{ols_r2}。高权重详细考点包括：{top_ols_points}。",
            ],
        },
        {
            "heading": "二、数据来源是否可靠",
            "paragraphs": [
                "真题与考纲来自用户提供的本地原始文件。厦门市公共基础模拟卷由爬虫尝试联网检索；若当前环境无法访问外网，来源表会保留检索种子和失败日志。",
                "这份报告不会把没有下载到、没有解析出的厦门卷当作已验证样本。缺数据的地方会明确写成缺失，便于后续补材料后重跑。",
            ],
            "tables": [
                {
                    "title": "来源索引",
                    "columns": ["year", "title", "source_url", "source_platform", "file_type", "file_path", "is_downloaded", "material_type", "region", "relevance_score", "evidence_level", "notes"],
                    "rows": sources[:12],
                },
                {
                    "title": "文件解析状态",
                    "columns": ["file_path", "source_type", "region", "year", "chars_extracted", "math_chars", "question_rows", "confidence", "ocr_failed", "status", "notes"],
                    "rows": file_status,
                },
            ],
        },
        {
            "heading": "三、真题、考纲、厦门卷怎么对照",
            "paragraphs": [
                "知识点热力图看的是“有没有覆盖”：同一列越多行亮起来，说明真题、考纲、厦门卷越一致。",
                "题型与难度关系图看的是“题量和难度是否一起变化”：点越靠右说明题量多，越靠上说明平均难度高。",
                "分值堆叠图看的是“分数花在哪里”：它能帮助判断模拟卷的分值结构是否接近真题。",
            ],
            "tables": [
                {
                    "title": "核心量化指标",
                    "columns": ["metric", "value", "status", "explanation"],
                    "rows": metrics,
                }
            ],
            "images": [
                CHARTS_DIR / "knowledge_overlap_heatmap.png",
                CHARTS_DIR / "question_type_difficulty_correlation.png",
                CHARTS_DIR / "score_distribution_stacked.png",
                CHARTS_DIR / "high_frequency_coverage.png",
            ],
        },
        {
            "heading": "四、逐题详细知识点与OLS权重",
            "paragraphs": [
                "这一部分直接回答“真题每道题的详细知识点，与当年厦门模拟题详细知识点是否接近”。系统先按年份把真题题目逐题拆成详细知识点，再与同年厦门卷做精确重合、宽知识点重合、题型相近和难度相近分析。",
                "随后用OLS回归把厦门同年详细知识点占比、考纲覆盖和厦门卷平均难度转化为命题权重。权重越高，模拟卷越应该安排对应考点；但最终仍受题型结构约束。",
            ],
            "tables": [
                {
                    "title": "同年详细知识点相关性",
                    "columns": ["year", "real_question_count", "xiamen_question_count", "detail_pearson_correlation", "detail_jaccard_overlap", "exact_overlap_count", "plain_meaning"],
                    "rows": ols_corr,
                },
                {
                    "title": "OLS回归系数",
                    "columns": ["term", "coefficient", "plain_meaning"],
                    "rows": ols_coef,
                },
                {
                    "title": "OLS加权后的前列详细考点",
                    "columns": ["detailed_knowledge_point", "historical_real_share", "xiamen_reference_share", "syllabus_present", "ols_predicted_real_share", "normalized_weight", "recommended_questions_in_24"],
                    "rows": ols_weighted[:12],
                },
            ],
            "images": [
                CHARTS_DIR / "same_year_detail_overlap_heatmap.png",
                CHARTS_DIR / "ols_weighted_knowledge_weights.png",
            ],
        },
        {
            "heading": "五、趋势图怎么读",
            "paragraphs": [
                "历年真题考点分布趋势图用来观察哪些知识点反复出现。考纲变更趋势图用来观察命题边界。综合趋势关联图把考纲、真题、厦门样本放在一起，方便看三者是否同向变化。",
            ],
            "images": [
                CHARTS_DIR / "real_exam_knowledge_trend.png",
                CHARTS_DIR / "syllabus_change_trend.png",
                CHARTS_DIR / "comprehensive_trend_relation.png",
                CHARTS_DIR / "future_prediction_scores.png",
            ],
        },
        {
            "heading": "六、2026模拟卷设计",
            "paragraphs": [
                "已重新生成一套原创公共基础数学模拟卷，严格采用用户最新指定结构：15道选择题，每题3分；5道填空题，每题3分；4道解答题，每题10分。该结构分值合计为100分。",
                "题目安排以OLS权重为主线，同时兼顾真题高频、考纲覆盖、厦门模拟卷信号和中职数学基础性。解答题重点放在集合运算、分段函数、直线与圆、应用建模。",
            ],
            "tables": [
                {
                    "title": "模拟卷命题依据",
                    "columns": ["question_id", "question_type", "score", "knowledge_point", "detailed_knowledge_point", "difficulty", "ols_normalized_weight", "ols_recommended_questions_in_24", "prediction_score", "recommended_coverage", "design_basis"],
                    "rows": blueprint,
                }
            ],
        },
        {
            "heading": "七、后续怎么补强",
            "paragraphs": [
                "如果拿到厦门市2022-2025公共基础综合卷或模拟卷，请放入 data/raw/crawled_xiamen_public_basic/年份/，再运行 run_all.py。",
                "如果材料是扫描版PDF或图片，需要安装OCR工具，或先转成可复制文字。系统会把OCR失败文件写入人工复核表。",
            ],
        },
    ]
    report = REPORTS_DIR / "福建省中职公共基础数学命题趋势分析与模拟卷生成报告.docx"
    create_docx_report(report, "福建省中职公共基础数学命题趋势分析与模拟卷生成报告", sections, "2026年起单张综合卷分析；模拟卷按15选+5填+4解生成")
    create_pdf_text(REPORTS_DIR / "福建省中职公共基础数学命题趋势分析与模拟卷生成报告.pdf", "福建省中职公共基础数学命题趋势分析与模拟卷生成报告", sections, "2026年起单张综合卷分析；模拟卷按15选+5填+4解生成")
    logger.info("Output final report %s", report)


if __name__ == "__main__":
    main()
