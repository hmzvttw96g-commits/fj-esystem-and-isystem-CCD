from __future__ import annotations

from collections import Counter
from typing import Dict, List

from common import (
    CHARTS_DIR,
    LOGS_DIR,
    PROCESSED_DIR,
    REPORTS_DIR,
    create_docx_report,
    create_pdf_text,
    distribution,
    read_xlsx_rows,
    save_bar_chart,
    setup_logger,
    write_xlsx,
)


logger = setup_logger("predict_exam_trends", LOGS_DIR / "predict_exam_trends.log")
QUESTION_TYPES = {"选择题", "填空题", "解答题"}


def main() -> None:
    logger.info("Start future exam trend prediction")
    rows = read_xlsx_rows(PROCESSED_DIR / "all_public_basic_math_questions.xlsx", "questions")
    metrics = read_xlsx_rows(PROCESSED_DIR / "quantitative_comparison_results.xlsx", "quantitative_metrics") if (PROCESSED_DIR / "quantitative_comparison_results.xlsx").exists() else []
    real = [r for r in rows if r.get("source_type") == "real_paper_math_part" and r.get("question_type") in QUESTION_TYPES and not r.get("needs_manual_review")]
    xiamen = [r for r in rows if r.get("source_type") == "xiamen_public_basic_mock" and r.get("question_type") in QUESTION_TYPES and not r.get("needs_manual_review")]
    syllabus = [r for r in rows if r.get("source_type") == "syllabus_math_part"]
    real_freq = distribution(real, "knowledge_point")
    xiamen_freq = distribution(xiamen, "knowledge_point")
    syllabus_set = {str(r.get("knowledge_point")) for r in syllabus if r.get("knowledge_point")}
    years = sorted({str(r.get("year")) for r in real if r.get("year")})
    recent = [r for r in real if str(r.get("year")) in years[-2:]]
    recent_freq = distribution(recent, "knowledge_point")

    all_kps = sorted(set(real_freq) | set(xiamen_freq) | syllabus_set)
    max_real = max(real_freq.values() or [1])
    max_recent = max(recent_freq.values() or [1])
    max_xm = max(xiamen_freq.values() or [1])
    prediction_rows: List[Dict[str, object]] = []
    for kp in all_kps:
        real_score = real_freq.get(kp, 0) / max_real
        recent_score = recent_freq.get(kp, 0) / max_recent
        syllabus_score = 1 if kp in syllabus_set else 0
        xiamen_score = xiamen_freq.get(kp, 0) / max_xm if xiamen else 0
        final_score = 0.42 * real_score + 0.28 * recent_score + 0.20 * syllabus_score + 0.10 * xiamen_score
        if real_freq.get(kp, 0) >= 3 and recent_freq.get(kp, 0) >= 1:
            trend = "稳定高频"
        elif recent_freq.get(kp, 0) > 0 and real_freq.get(kp, 0) <= 2:
            trend = "可能上升"
        elif kp in syllabus_set and real_freq.get(kp, 0) == 0:
            trend = "考纲保留但真题样本较少"
        else:
            trend = "基础轮换"
        prediction_rows.append(
            {
                "knowledge_point": kp,
                "historical_frequency": real_freq.get(kp, 0),
                "recent_frequency": recent_freq.get(kp, 0),
                "xiamen_frequency": xiamen_freq.get(kp, 0),
                "in_syllabus": kp in syllabus_set,
                "trend_label": trend,
                "prediction_score": round(final_score, 4),
                "recommended_coverage": "重点覆盖" if final_score >= 0.58 else ("适度覆盖" if final_score >= 0.32 else "基础覆盖"),
            }
        )
    prediction_rows.sort(key=lambda r: r["prediction_score"], reverse=True)
    direction_rows = [
        {"category": "高频考点", "content": "、".join([r["knowledge_point"] for r in prediction_rows[:7]]), "plain_explanation": "这些知识点在真题中出现多，且多数仍在考纲中，是单张综合卷数学部分的主干。"},
        {"category": "上升知识点", "content": "、".join([r["knowledge_point"] for r in prediction_rows if r["trend_label"] == "可能上升"][:5]) or "暂无明显上升项", "plain_explanation": "近期出现但历史频次还不算高，适合在模拟卷中适度安排。"},
        {"category": "下降或低优先级知识点", "content": "、".join([r["knowledge_point"] for r in prediction_rows[-4:]]) or "暂无", "plain_explanation": "不代表不会考，只是不宜作为押题重点。"},
        {"category": "应用题方向", "content": "函数模型、简单统计抽样、区间/不等式、生活生产情境下的费用或数量关系", "plain_explanation": "公共基础综合卷更强调基础能力和情境理解，应用题应短、清楚、可计算。"},
        {"category": "综合题方向", "content": "直线与圆、向量坐标、分段函数、三角函数基础性质的两到三问综合", "plain_explanation": "综合题建议分层设问，第一问送分，后两问考运算与表达。"},
        {"category": "不建议过度押题内容", "content": "未验证的厦门模拟卷题面、超纲竞赛题、复杂计算技巧、只靠记忆的冷门公式", "plain_explanation": "没有数据支持的材料不能直接作为强预测依据。"},
    ]
    write_xlsx({"trend_prediction": prediction_rows, "direction_summary": direction_rows, "quantitative_metrics_reference": metrics}, PROCESSED_DIR / "future_exam_trend_prediction.xlsx")
    save_bar_chart([r["knowledge_point"] for r in prediction_rows[:8]], [float(r["prediction_score"]) * 100 for r in prediction_rows[:8]], CHARTS_DIR / "future_prediction_scores.png", "未来命题趋势预测分", "%")

    xiamen_missing = not xiamen
    sections = [
        {
            "heading": "一句话结论",
            "paragraphs": [
                f"2026年起按单张综合卷备考时，建议把 {direction_rows[0]['content']} 作为数学部分重点覆盖板块。",
                "预测分越高，表示该知识点同时满足真题频次、近期出现、考纲覆盖和厦门样本参考四类条件。",
                "本轮厦门模拟卷样本缺失，因此厦门权重暂不发挥作用；后续补充样本后会自动更新。",
            ] if xiamen_missing else [
                f"2026年起按单张综合卷备考时，建议把 {direction_rows[0]['content']} 作为数学部分重点覆盖板块。",
                "预测分综合真题、考纲和厦门模拟卷，不是押题，而是命题权重建议。",
            ],
            "images": [CHARTS_DIR / "future_prediction_scores.png"],
        },
        {
            "heading": "怎么用这份预测",
            "paragraphs": [
                "重点覆盖：模拟卷中必须出现，通常用选择题、填空题和解答题多形式覆盖。",
                "适度覆盖：安排1题左右，防止知识面过窄。",
                "基础覆盖：用简单题点到即可，不宜投入过多分值。",
            ],
        },
        {
            "heading": "题型建议",
            "paragraphs": [
                "模拟卷建议保持基础题占多数，选择题覆盖面广，填空题看计算准确度，解答题看表达过程。",
                f"应用题方向：{direction_rows[3]['content']}。综合题方向：{direction_rows[4]['content']}。",
            ],
        },
    ]
    create_docx_report(REPORTS_DIR / "04_福建省中职公共基础数学未来命题趋势预测报告.docx", "福建省中职公共基础数学未来命题趋势预测报告", sections, "2026年起单张综合卷口径")
    create_pdf_text(REPORTS_DIR / "04_福建省中职公共基础数学未来命题趋势预测报告.pdf", "福建省中职公共基础数学未来命题趋势预测报告", sections, "2026年起单张综合卷口径")
    logger.info("Output future prediction workbook and report")


if __name__ == "__main__":
    main()
