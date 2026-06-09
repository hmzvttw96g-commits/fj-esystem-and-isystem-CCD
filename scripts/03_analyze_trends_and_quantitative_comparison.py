from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Dict, Iterable, List

from common import (
    CHARTS_DIR,
    LOGS_DIR,
    PROCESSED_DIR,
    REPORTS_DIR,
    create_docx_report,
    create_pdf_text,
    distribution,
    l1_similarity,
    overlap_rate,
    read_xlsx_rows,
    save_bar_chart,
    save_grouped_bar_chart,
    save_heatmap,
    save_line_chart,
    save_scatter_chart,
    save_stacked_bar_chart,
    setup_logger,
    write_xlsx,
)


logger = setup_logger("analyze_trends_and_quantitative_comparison", LOGS_DIR / "analyze_trends_and_quantitative_comparison.log")

QUESTION_TYPES = {"选择题", "填空题", "解答题"}
DIFFICULTY_SCORE = {"基础": 1, "中等": 2, "较难": 3}


def pearson_from_counters(a: Counter, b: Counter) -> float | None:
    keys = sorted(set(a) | set(b))
    if len(keys) < 2:
        return None
    xs = [float(a.get(k, 0)) for k in keys]
    ys = [float(b.get(k, 0)) for k in keys]
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mx) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - my) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return None
    return num / (den_x * den_y)


def score_counter(rows: Iterable[Dict[str, object]]) -> Counter:
    c = Counter()
    for r in rows:
        try:
            score = float(r.get("score") or 0)
        except Exception:
            score = 0.0
        c[str(r.get("question_type") or "未识别")] += score
    return c


def high_freq_coverage(candidate_rows: List[Dict[str, object]], real_rows: List[Dict[str, object]], n: int = 6) -> float | None:
    if not candidate_rows:
        return None
    high = {k for k, _ in distribution(real_rows, "knowledge_point").most_common(n)}
    cand = {str(r.get("knowledge_point")) for r in candidate_rows if r.get("knowledge_point")}
    return len(high & cand) / (len(high) or 1)


def main() -> None:
    logger.info("Start trends and quantitative comparison")
    all_rows = read_xlsx_rows(PROCESSED_DIR / "all_public_basic_math_questions.xlsx", "questions")
    sources = read_xlsx_rows(PROCESSED_DIR / "xiamen_public_basic_sources.xlsx", "sources") if (PROCESSED_DIR / "xiamen_public_basic_sources.xlsx").exists() else []
    real = [r for r in all_rows if r.get("source_type") == "real_paper_math_part" and r.get("question_type") in QUESTION_TYPES and not r.get("needs_manual_review")]
    xiamen = [r for r in all_rows if r.get("source_type") == "xiamen_public_basic_mock" and r.get("question_type") in QUESTION_TYPES and not r.get("needs_manual_review")]
    syllabus = [r for r in all_rows if r.get("source_type") == "syllabus_math_part"]

    real_kp = distribution(real, "knowledge_point")
    xiamen_kp = distribution(xiamen, "knowledge_point")
    syllabus_kps = {str(r.get("knowledge_point")) for r in syllabus if r.get("knowledge_point")}
    xiamen_corr = pearson_from_counters(real_kp, xiamen_kp)
    real_syllabus_overlap = overlap_rate(real_kp.keys(), syllabus_kps)
    xiamen_real_overlap = overlap_rate(xiamen_kp.keys(), real_kp.keys()) if xiamen else None
    xiamen_syllabus_overlap = overlap_rate(xiamen_kp.keys(), syllabus_kps) if xiamen else None
    metrics = [
        {"metric": "考纲 vs 真题知识点重合度", "value": round(real_syllabus_overlap, 4), "status": "可计算", "explanation": "真题已识别知识点与考纲知识点的Jaccard重合度。"},
        {"metric": "厦门卷 vs 真题知识点重合度", "value": None if xiamen_real_overlap is None else round(xiamen_real_overlap, 4), "status": "缺少厦门卷样本" if xiamen_real_overlap is None else "可计算", "explanation": "厦门模拟卷知识点与真题知识点重合度。"},
        {"metric": "厦门卷 vs 考纲知识点重合度", "value": None if xiamen_syllabus_overlap is None else round(xiamen_syllabus_overlap, 4), "status": "缺少厦门卷样本" if xiamen_syllabus_overlap is None else "可计算", "explanation": "厦门模拟卷知识点与考纲知识点重合度。"},
        {"metric": "题型匹配度", "value": None if not xiamen else round(l1_similarity(distribution(real, "question_type"), distribution(xiamen, "question_type")), 4), "status": "缺少厦门卷样本" if not xiamen else "可计算", "explanation": "基于题型占比的一致性。"},
        {"metric": "难度匹配度", "value": None if not xiamen else round(l1_similarity(distribution(real, "difficulty"), distribution(xiamen, "difficulty")), 4), "status": "缺少厦门卷样本" if not xiamen else "可计算", "explanation": "基于基础/中等/较难占比的一致性。"},
        {"metric": "分值占比匹配度", "value": None if not xiamen else round(l1_similarity(score_counter(real), score_counter(xiamen)), 4), "status": "缺少厦门卷样本" if not xiamen else "可计算", "explanation": "基于各题型总分占比的一致性。"},
        {"metric": "高频考点覆盖率", "value": None if not xiamen else round(high_freq_coverage(xiamen, real) or 0, 4), "status": "缺少厦门卷样本" if not xiamen else "可计算", "explanation": "厦门卷覆盖真题前6个高频知识点的比例。"},
        {"metric": "厦门卷与真题正相关性", "value": None if xiamen_corr is None else round(xiamen_corr, 4), "status": "缺少厦门卷样本或向量无方差" if xiamen_corr is None else "可计算", "explanation": "知识点频次向量的Pearson相关系数。"},
    ]

    years = sorted({str(r.get("year")) for r in real if r.get("year")})
    trend_rows = []
    for year in years:
        subset = [r for r in real if str(r.get("year")) == year]
        total = len(subset) or 1
        for kp, count in distribution(subset, "knowledge_point").items():
            trend_rows.append({"year": year, "source": "福建真题数学部分", "knowledge_point": kp, "count": count, "share": round(count / total, 4)})
    if xiamen:
        for year in sorted({str(r.get("year")) for r in xiamen if r.get("year")}):
            subset = [r for r in xiamen if str(r.get("year")) == year]
            total = len(subset) or 1
            for kp, count in distribution(subset, "knowledge_point").items():
                trend_rows.append({"year": year, "source": "厦门公共基础模拟卷", "knowledge_point": kp, "count": count, "share": round(count / total, 4)})

    syllabus_by_year = defaultdict(set)
    for r in syllabus:
        if r.get("year") and r.get("knowledge_point"):
            syllabus_by_year[str(r.get("year"))].add(str(r.get("knowledge_point")))
    syllabus_change_rows = []
    syl_years = sorted(syllabus_by_year)
    for i, year in enumerate(syl_years):
        prev = syllabus_by_year[syl_years[i - 1]] if i else set()
        cur = syllabus_by_year[year]
        added = sorted(cur - prev)
        removed = sorted(prev - cur)
        for kp in sorted(cur | prev):
            syllabus_change_rows.append(
                {
                    "year": year,
                    "knowledge_point": kp,
                    "in_syllabus": kp in cur,
                    "change_type": "新增" if kp in added else ("移除" if kp in removed else "延续"),
                    "real_frequency": real_kp.get(kp, 0),
                    "xiamen_frequency": xiamen_kp.get(kp, 0),
                }
            )

    score_rows = []
    for source, rows in [("福建真题数学部分", real), ("厦门公共基础模拟卷", xiamen)]:
        sc = score_counter(rows)
        for qtype, score in sc.items():
            score_rows.append({"source": source, "question_type": qtype, "score_total": score})

    type_difficulty_rows = []
    for source, rows in [("福建真题数学部分", real), ("厦门公共基础模拟卷", xiamen)]:
        by_type = defaultdict(list)
        for r in rows:
            by_type[str(r.get("question_type"))].append(DIFFICULTY_SCORE.get(str(r.get("difficulty")), 0))
        for qtype, vals in by_type.items():
            type_difficulty_rows.append(
                {
                    "source": source,
                    "question_type": qtype,
                    "question_count": len(vals),
                    "avg_difficulty_score": round(sum(vals) / (len(vals) or 1), 3),
                }
            )

    write_xlsx(
        {
            "quantitative_metrics": metrics,
            "knowledge_year_trend": trend_rows,
            "syllabus_changes": syllabus_change_rows,
            "score_distribution": score_rows,
            "type_difficulty_relation": type_difficulty_rows,
            "source_index": sources,
        },
        PROCESSED_DIR / "quantitative_comparison_results.xlsx",
    )

    # Charts
    all_kps = sorted(set(real_kp) | set(xiamen_kp) | syllabus_kps)
    save_heatmap(
        ["福建真题", "考纲", "厦门模拟卷"],
        all_kps,
        [[1 if kp in real_kp else 0 for kp in all_kps], [1 if kp in syllabus_kps else 0 for kp in all_kps], [1 if kp in xiamen_kp else 0 for kp in all_kps]],
        CHARTS_DIR / "knowledge_overlap_heatmap.png",
        "知识点重合度热力图",
    )
    if trend_rows:
        groups = defaultdict(dict)
        for row in trend_rows:
            if row["source"] == "福建真题数学部分":
                groups[row["year"]][row["knowledge_point"]] = row["count"]
        save_grouped_bar_chart(dict(groups), CHARTS_DIR / "real_exam_knowledge_trend.png", "历年真题考点分布趋势")
    else:
        save_bar_chart(["无数据"], [0], CHARTS_DIR / "real_exam_knowledge_trend.png", "历年真题考点分布趋势")

    syllabus_groups = defaultdict(dict)
    for row in syllabus_change_rows:
        if row["change_type"] != "移除":
            syllabus_groups[row["year"]][row["knowledge_point"]] = 1
    save_grouped_bar_chart(dict(syllabus_groups) or {"无数据": {"无": 0}}, CHARTS_DIR / "syllabus_change_trend.png", "历年考纲变更趋势")

    scatter_points = []
    color_map = {"福建真题数学部分": "#2563EB", "厦门公共基础模拟卷": "#059669"}
    for row in type_difficulty_rows:
        scatter_points.append(
            {
                "x": row["question_count"],
                "y": row["avg_difficulty_score"],
                "label": f"{row['source'].replace('数学部分','').replace('公共基础','')}-{row['question_type']}",
                "color": color_map.get(row["source"], "#7C3AED"),
            }
        )
    save_scatter_chart(scatter_points or [{"x": 0, "y": 0, "label": "无厦门样本"}], CHARTS_DIR / "question_type_difficulty_correlation.png", "题型与难度关系图", "题量", "平均难度")

    stacked = {}
    for source in ["福建真题数学部分", "厦门公共基础模拟卷"]:
        stacked[source] = {row["question_type"]: row["score_total"] for row in score_rows if row["source"] == source}
        if not stacked[source]:
            stacked[source] = {"无可解析样本": 0}
    save_stacked_bar_chart(stacked, CHARTS_DIR / "score_distribution_stacked.png", "分值分布堆叠柱状图")

    hf_labels = [k for k, _ in real_kp.most_common(8)]
    hf_values = [100 if k in xiamen_kp else 0 for k in hf_labels] if xiamen else [0 for _ in hf_labels]
    save_bar_chart(hf_labels or ["无数据"], hf_values or [0], CHARTS_DIR / "high_frequency_coverage.png", "高频考点覆盖率", "%")

    trend_series = {
        "真题题量": [sum(1 for r in real if str(r.get("year")) == y) for y in years],
        "考纲覆盖点数": [len(syllabus_by_year.get(y, set())) for y in years],
        "厦门样本题量": [sum(1 for r in xiamen if str(r.get("year")) == y) for y in years],
    }
    save_line_chart(trend_series, years or ["无年份"], CHARTS_DIR / "comprehensive_trend_relation.png", "综合趋势关联图")

    metric_text = "；".join([f"{m['metric']}：{m['value'] if m['value'] is not None else m['status']}" for m in metrics])
    xiamen_note = "本轮未获得可解析厦门市公共基础模拟卷样本，因此厦门卷相关指标保留为缺失状态。" if not xiamen else "已获得可解析厦门模拟卷样本，相关指标可计算。"
    sections = [
        {
            "heading": "结论摘要",
            "paragraphs": [
                "本报告按2026年起单张综合卷口径，只分析公共基础中的数学部分。",
                metric_text,
                xiamen_note,
            ],
        },
        {
            "heading": "考点趋势与考纲变化",
            "paragraphs": ["真题样本用于观察实际命题覆盖，考纲样本用于确定命题边界。图中重点看哪些知识点长期出现、哪些只在考纲中出现但真题样本较少。"],
            "images": [CHARTS_DIR / "real_exam_knowledge_trend.png", CHARTS_DIR / "syllabus_change_trend.png", CHARTS_DIR / "comprehensive_trend_relation.png"],
        },
        {
            "heading": "量化对照图表",
            "paragraphs": ["热力图显示真题、考纲、厦门模拟卷的知识点是否同时出现；题型与难度图把题量放在横轴、平均难度放在纵轴，越靠右上说明题量多且难度高。"],
            "images": [
                CHARTS_DIR / "knowledge_overlap_heatmap.png",
                CHARTS_DIR / "question_type_difficulty_correlation.png",
                CHARTS_DIR / "score_distribution_stacked.png",
                CHARTS_DIR / "high_frequency_coverage.png",
            ],
        },
        {
            "heading": "人工复核提示",
            "paragraphs": ["如果后续下载到厦门市公共基础综合卷或模拟卷，请放入 data/raw/crawled_xiamen_public_basic/年份/ 后重跑全流程，系统会自动更新正相关性和覆盖率。"],
        },
    ]
    create_docx_report(REPORTS_DIR / "03_厦门公共基础数学卷与福建真题考纲量化对照报告.docx", "厦门公共基础数学卷与福建真题考纲量化对照报告", sections, "面向普通读者的直观量化分析")
    create_pdf_text(REPORTS_DIR / "03_厦门公共基础数学卷与福建真题考纲量化对照报告.pdf", "厦门公共基础数学卷与福建真题考纲量化对照报告", sections, "面向普通读者的直观量化分析")
    logger.info("Output quantitative comparison workbook, charts and report")


if __name__ == "__main__":
    main()
