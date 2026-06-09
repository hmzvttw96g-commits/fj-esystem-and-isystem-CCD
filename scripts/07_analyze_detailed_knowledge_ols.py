from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, Iterable, List

import numpy as np

from common import (
    CHARTS_DIR,
    LOGS_DIR,
    PROCESSED_DIR,
    REPORTS_DIR,
    create_docx_report,
    create_pdf_text,
    read_xlsx_rows,
    save_bar_chart,
    save_heatmap,
    setup_logger,
    write_xlsx,
)


logger = setup_logger("analyze_detailed_knowledge_ols", LOGS_DIR / "analyze_detailed_knowledge_ols.log")

QUESTION_TYPES = {"选择题", "填空题", "解答题"}
DIFF_SCORE = {"基础": 1.0, "中等": 2.0, "较难": 3.0}


def valid_math_rows(rows: List[Dict[str, object]], source_type: str) -> List[Dict[str, object]]:
    out = []
    for r in rows:
        if r.get("source_type") != source_type:
            continue
        if r.get("question_type") not in QUESTION_TYPES:
            continue
        if not r.get("is_math_question"):
            continue
        detail = str(r.get("detailed_knowledge_point") or "")
        if not detail or detail == "其他待人工复核":
            continue
        out.append(r)
    return out


def counter_share(rows: Iterable[Dict[str, object]]) -> Dict[str, float]:
    c = Counter(str(r.get("detailed_knowledge_point")) for r in rows if r.get("detailed_knowledge_point"))
    total = sum(c.values()) or 1
    return {k: v / total for k, v in c.items()}


def avg_difficulty(rows: Iterable[Dict[str, object]]) -> Dict[str, float]:
    vals: Dict[str, List[float]] = defaultdict(list)
    for r in rows:
        vals[str(r.get("detailed_knowledge_point"))].append(DIFF_SCORE.get(str(r.get("difficulty")), 2.0))
    return {k: sum(v) / (len(v) or 1) for k, v in vals.items()}


def run_ols(rows: List[Dict[str, object]]):
    y = np.array([float(r["real_share"]) for r in rows], dtype=float)
    x = np.array(
        [
            [
                1.0,
                float(r["xiamen_share"]),
                float(r["syllabus_present"]),
                float(r["xiamen_avg_difficulty_norm"]),
            ]
            for r in rows
        ],
        dtype=float,
    )
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    fitted = x @ beta
    residual = y - fitted
    sst = float(((y - y.mean()) ** 2).sum())
    sse = float((residual**2).sum())
    r2 = None if sst == 0 else 1 - sse / sst
    return beta, fitted, residual, r2


def main() -> None:
    logger.info("Start detailed knowledge OLS analysis")
    all_rows = read_xlsx_rows(PROCESSED_DIR / "all_public_basic_math_questions.xlsx", "questions")
    real = valid_math_rows(all_rows, "real_paper_math_part")
    xiamen = valid_math_rows(all_rows, "xiamen_public_basic_mock")
    syllabus = [r for r in all_rows if r.get("source_type") == "syllabus_math_part"]
    syllabus_details = {str(r.get("detailed_knowledge_point") or r.get("knowledge_point")) for r in syllabus}
    syllabus_broad = {str(r.get("knowledge_point") or "") for r in syllabus if r.get("knowledge_point")}
    detail_broad_lookup = {}
    for row in real + xiamen:
        detail = str(row.get("detailed_knowledge_point") or "")
        broad = str(row.get("knowledge_point") or "")
        if detail and broad:
            detail_broad_lookup.setdefault(detail, broad)

    def in_syllabus(detail: str) -> bool:
        return detail in syllabus_details or detail_broad_lookup.get(detail, "") in syllabus_broad

    real_years = {str(r.get("year")) for r in real if r.get("year")}
    xiamen_years = {str(r.get("year")) for r in xiamen if r.get("year")}
    common_years = sorted(real_years & xiamen_years)

    question_overlap_rows: List[Dict[str, object]] = []
    for year in common_years:
        real_y = [r for r in real if str(r.get("year")) == year]
        xm_y = [r for r in xiamen if str(r.get("year")) == year]
        xm_details = [str(r.get("detailed_knowledge_point")) for r in xm_y]
        xm_broad = [str(r.get("knowledge_point")) for r in xm_y]
        for rq in real_y:
            detail = str(rq.get("detailed_knowledge_point"))
            broad = str(rq.get("knowledge_point"))
            qtype = str(rq.get("question_type"))
            diff = DIFF_SCORE.get(str(rq.get("difficulty")), 2.0)
            exact_count = xm_details.count(detail)
            broad_count = xm_broad.count(broad)
            type_count = sum(1 for x in xm_y if str(x.get("question_type")) == qtype)
            diff_sim = []
            for x in xm_y:
                xd = DIFF_SCORE.get(str(x.get("difficulty")), 2.0)
                diff_sim.append(max(0.0, 1.0 - abs(diff - xd) / 2.0))
            question_overlap_rows.append(
                {
                    "year": year,
                    "real_file": rq.get("file_name"),
                    "real_question_id": rq.get("question_id"),
                    "real_question_type": qtype,
                    "real_difficulty": rq.get("difficulty"),
                    "real_knowledge_point": broad,
                    "real_detailed_knowledge_point": detail,
                    "xiamen_same_year_question_count": len(xm_y),
                    "exact_detail_match_count": exact_count,
                    "exact_detail_overlap_rate": round(exact_count / (len(xm_y) or 1), 4),
                    "broad_knowledge_match_count": broad_count,
                    "broad_knowledge_overlap_rate": round(broad_count / (len(xm_y) or 1), 4),
                    "question_type_match_rate": round(type_count / (len(xm_y) or 1), 4),
                    "avg_difficulty_similarity": round(sum(diff_sim) / (len(diff_sim) or 1), 4),
                }
            )

    same_year_rows: List[Dict[str, object]] = []
    correlation_rows: List[Dict[str, object]] = []
    for year in common_years:
        real_y = [r for r in real if str(r.get("year")) == year]
        xm_y = [r for r in xiamen if str(r.get("year")) == year]
        real_share = counter_share(real_y)
        xm_share = counter_share(xm_y)
        xm_diff = avg_difficulty(xm_y)
        details = sorted(set(real_share) | set(xm_share) | syllabus_details)
        corr_details = sorted(set(real_share) | set(xm_share))
        if len(corr_details) >= 2:
            real_vec = np.array([real_share.get(d, 0.0) for d in corr_details], dtype=float)
            xm_vec = np.array([xm_share.get(d, 0.0) for d in corr_details], dtype=float)
            corr = float(np.corrcoef(real_vec, xm_vec)[0, 1]) if real_vec.std() > 0 and xm_vec.std() > 0 else 0.0
        else:
            corr = 0.0
        real_detail_set = set(real_share)
        xm_detail_set = set(xm_share)
        jaccard = len(real_detail_set & xm_detail_set) / (len(real_detail_set | xm_detail_set) or 1)
        correlation_rows.append(
            {
                "year": year,
                "real_question_count": len(real_y),
                "xiamen_question_count": len(xm_y),
                "detail_pearson_correlation": round(corr, 6),
                "detail_jaccard_overlap": round(jaccard, 6),
                "exact_overlap_count": len(real_detail_set & xm_detail_set),
                "real_detail_count": len(real_detail_set),
                "xiamen_detail_count": len(xm_detail_set),
                "plain_meaning": "越接近1，说明当年厦门卷详细考点分布越接近当年福建真题。",
            }
        )
        for detail in details:
            same_year_rows.append(
                {
                    "year": year,
                    "detailed_knowledge_point": detail,
                    "real_share": round(real_share.get(detail, 0.0), 6),
                    "xiamen_share": round(xm_share.get(detail, 0.0), 6),
                    "exact_overlap": detail in real_share and detail in xm_share,
                    "syllabus_present": 1 if in_syllabus(detail) else 0,
                    "xiamen_avg_difficulty_norm": round((xm_diff.get(detail, 2.0) - 1.0) / 2.0, 6),
                }
            )

    regression_rows = [r for r in same_year_rows if str(r.get("detailed_knowledge_point")) != "其他待人工复核"]
    beta = np.zeros(4)
    fitted = np.zeros(len(regression_rows))
    residual = np.zeros(len(regression_rows))
    r2 = None
    if len(regression_rows) >= 4:
        beta, fitted, residual, r2 = run_ols(regression_rows)
        for i, r in enumerate(regression_rows):
            r["ols_fitted_real_share"] = round(float(fitted[i]), 6)
            r["ols_residual"] = round(float(residual[i]), 6)

    coef_rows = [
        {"term": "截距", "coefficient": round(float(beta[0]), 6), "plain_meaning": "没有厦门卷信号时的基础权重。"},
        {"term": "厦门同年详细知识点占比", "coefficient": round(float(beta[1]), 6), "plain_meaning": "厦门卷某知识点占比越高，真题中对应占比的变化方向。"},
        {"term": "考纲覆盖", "coefficient": round(float(beta[2]), 6), "plain_meaning": "该知识点被考纲覆盖时对真题占比的加权影响。"},
        {"term": "厦门卷平均难度", "coefficient": round(float(beta[3]), 6), "plain_meaning": "厦门卷中该知识点平均难度越高，对真题占比的加权影响。"},
        {"term": "R2", "coefficient": "" if r2 is None else round(float(r2), 6), "plain_meaning": "模型对同年真题详细知识点占比的解释程度。"},
    ]

    real_all_share = counter_share(real)
    xiamen_future = [r for r in xiamen if str(r.get("year")) == "2026"]
    xiamen_recent = xiamen_future or [r for r in xiamen if str(r.get("year")) in sorted(xiamen_years)[-2:]]
    xiamen_future_share = counter_share(xiamen_recent)
    xiamen_future_diff = avg_difficulty(xiamen_recent)
    all_details = sorted(set(real_all_share) | set(xiamen_future_share) | syllabus_details)
    weight_rows: List[Dict[str, object]] = []
    raw_scores = []
    for detail in all_details:
        features = np.array(
            [
                1.0,
                xiamen_future_share.get(detail, 0.0),
                1.0 if in_syllabus(detail) else 0.0,
                (xiamen_future_diff.get(detail, 2.0) - 1.0) / 2.0,
            ]
        )
        ols_pred = float(features @ beta) if len(regression_rows) >= 4 else 0.0
        raw = max(0.0, ols_pred) + 0.35 * real_all_share.get(detail, 0.0) + 0.25 * xiamen_future_share.get(detail, 0.0)
        raw_scores.append(raw)
        weight_rows.append(
            {
                "detailed_knowledge_point": detail,
                "historical_real_share": round(real_all_share.get(detail, 0.0), 6),
                "xiamen_reference_share": round(xiamen_future_share.get(detail, 0.0), 6),
                "syllabus_present": in_syllabus(detail),
                "ols_predicted_real_share": round(ols_pred, 6),
                "raw_weight_score": round(raw, 6),
            }
        )
    total_raw = sum(raw_scores) or 1.0
    for row, raw in zip(weight_rows, raw_scores):
        row["normalized_weight"] = round(raw / total_raw, 6)
        row["recommended_questions_in_24"] = round(raw / total_raw * 24, 2)
    weight_rows.sort(key=lambda r: r["normalized_weight"], reverse=True)

    write_xlsx(
        {
            "question_level_same_year_overlap": question_overlap_rows,
            "same_year_detail_correlation": correlation_rows,
            "same_year_detail_regression_data": same_year_rows,
            "ols_coefficients": coef_rows,
            "ols_weighted_blueprint": weight_rows,
        },
        PROCESSED_DIR / "detailed_knowledge_ols_analysis.xlsx",
    )

    top = weight_rows[:10]
    save_bar_chart(
        [str(r["detailed_knowledge_point"]) for r in top],
        [float(r["normalized_weight"]) * 100 for r in top],
        CHARTS_DIR / "ols_weighted_knowledge_weights.png",
        "OLS加权后的详细知识点权重",
        "%",
    )
    if common_years:
        details = sorted({str(r["detailed_knowledge_point"]) for r in same_year_rows})
        real_row = []
        xm_row = []
        for detail in details:
            real_row.append(sum(float(r["real_share"]) for r in same_year_rows if r["detailed_knowledge_point"] == detail))
            xm_row.append(sum(float(r["xiamen_share"]) for r in same_year_rows if r["detailed_knowledge_point"] == detail))
        save_heatmap(
            ["同年真题", "同年厦门卷"],
            details,
            [real_row, xm_row],
            CHARTS_DIR / "same_year_detail_overlap_heatmap.png",
            "同年详细知识点占比对照",
        )

    sections = [
        {
            "heading": "分析结论",
            "paragraphs": [
                f"同年可直接对照年份为：{', '.join(common_years) if common_years else '暂无'}。由于2024福建真题PDF文本层为空，2024厦门卷无法与同年福建真题做逐题同年回归，只进入后续权重参考。",
                "OLS以详细知识点为单位，用厦门同年占比、考纲覆盖和厦门卷平均难度解释同年真题占比，再结合历史真题和2026厦门模拟卷形成出卷权重。",
            ],
            "tables": [
                {
                    "title": "同年详细知识点相关性",
                    "columns": ["year", "real_question_count", "xiamen_question_count", "detail_pearson_correlation", "detail_jaccard_overlap", "exact_overlap_count"],
                    "rows": correlation_rows,
                },
                {
                    "title": "OLS回归系数",
                    "columns": ["term", "coefficient", "plain_meaning"],
                    "rows": coef_rows,
                }
            ],
            "images": [CHARTS_DIR / "same_year_detail_overlap_heatmap.png", CHARTS_DIR / "ols_weighted_knowledge_weights.png"],
        },
        {
            "heading": "出卷权重怎么用",
            "paragraphs": [
                "权重越高，模拟卷中越应该安排题目；但仍要满足你指定的题型结构：15道选择题、5道填空题、4道解答题。",
                "如果某些详细知识点由于公式抽取缺失进入人工复核，系统会降低其自动权重，避免误判。",
            ],
        },
    ]
    create_docx_report(REPORTS_DIR / "05_真题与厦门模拟题详细知识点OLS权重分析报告.docx", "真题与厦门模拟题详细知识点OLS权重分析报告", sections, "逐题重合度、相关性与出卷权重")
    create_pdf_text(REPORTS_DIR / "05_真题与厦门模拟题详细知识点OLS权重分析报告.pdf", "真题与厦门模拟题详细知识点OLS权重分析报告", sections, "逐题重合度、相关性与出卷权重")
    logger.info("Output detailed OLS analysis")


if __name__ == "__main__":
    main()
