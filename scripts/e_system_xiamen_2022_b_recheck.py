#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""厦门 2022 年 E 端 B 基本口径缺失补齐核验。

本脚本基于 2022 年福建省普通高校招生计划（普通类物理科目组）PDF
中已核验的相关页，整理厦门市本科高校 AI 基础专业群候选数据。
不重算 CCD，不覆盖 latest experimental base panel。
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from pypdf import PdfReader


PDF_CANDIDATES = [
    Path("/Users/greenbarry/Desktop/finacial system and educational system CCD/e-基本口径data/2022年福建省普通高校招生计划（普通类物理科目组）(1).pdf"),
    Path("/Users/greenbarry/Desktop/finacial system and educational system CCD/e-基本口径data/2022年福建省普通高校招生计划（普通类物理科目组）.pdf"),
]
LATEST_BASE_PANEL = Path("data/panel/experimental_analysis/latest_experimental_analysis_base_panel_2019_2024.csv")

TARGET_YEAR = 2022
TARGET_CITY = "厦门"

CANDIDATE_COLUMNS = [
    "year",
    "city",
    "school_name",
    "school_location",
    "school_type",
    "batch",
    "admission_scope",
    "program_group",
    "major_code",
    "major_original",
    "major_standard",
    "major_group",
    "caliber",
    "plan_count",
    "tuition",
    "remarks",
    "evidence_page",
    "evidence_text",
    "include_in_B_main",
    "include_in_C_conservative",
    "include_in_X_expanded",
    "include_status",
    "reviewer_decision",
    "reviewer_notes",
]


def pick_pdf() -> tuple[Path, list[str]]:
    warnings: list[str] = []
    for path in PDF_CANDIDATES:
        if path.exists():
            if "(1)" not in path.name:
                warnings.append("优先文件名带 (1) 的 PDF 未找到，已使用同目录下无 (1) 版本。")
            return path, warnings
    raise FileNotFoundError("未找到 2022 年福建省普通高校招生计划（普通类物理科目组）PDF。")


def page_text(reader: PdfReader, page: int, max_chars: int = 520) -> str:
    text = (reader.pages[page - 1].extract_text() or "").replace("\n", " | ")
    text = " ".join(text.split())
    return text[:max_chars]


def record(
    school_name: str,
    school_location: str,
    school_type: str,
    admission_scope: str,
    program_group: str,
    major_code: str,
    major_original: str,
    major_standard: str,
    major_group: str,
    caliber: str,
    plan_count: int,
    tuition: str,
    remarks: str,
    evidence_page: int,
    evidence_text: str,
    include_in_b: int,
    include_in_c: int,
    include_in_x: int,
    include_status: str,
    reviewer_notes: str,
) -> dict[str, Any]:
    return {
        "year": TARGET_YEAR,
        "city": TARGET_CITY,
        "school_name": school_name,
        "school_location": school_location,
        "school_type": school_type,
        "batch": "普通类·物理科目组—本科批",
        "admission_scope": admission_scope,
        "program_group": program_group,
        "major_code": major_code,
        "major_original": major_original,
        "major_standard": major_standard,
        "major_group": major_group,
        "caliber": caliber,
        "plan_count": plan_count,
        "tuition": tuition,
        "remarks": remarks,
        "evidence_page": evidence_page,
        "evidence_text": evidence_text,
        "include_in_B_main": include_in_b,
        "include_in_C_conservative": include_in_c,
        "include_in_X_expanded": include_in_x,
        "include_status": include_status,
        "reviewer_decision": "pending_review",
        "reviewer_notes": reviewer_notes,
    }


def add_records(rows: list[dict[str, Any]], evidence: dict[int, str]) -> None:
    def add_public_b(school: str, page: int, group: str, code: str, major: str, plan: int, tuition: str, scope: str = "普通类", notes: str = "") -> None:
        status = "include_B_main" if scope == "普通类" else "manual_review_required"
        rows.append(
            record(
                school,
                "厦门市",
                "公办",
                scope,
                group,
                code,
                major,
                major,
                "AI基础专业群",
                "B_basic",
                plan,
                tuition,
                "",
                page,
                evidence[page],
                1 if status == "include_B_main" else 0,
                1 if major in {"人工智能", "计算机科学与技术", "软件工程", "信息安全", "网络空间安全"} or major == "计算机类" else 0,
                1,
                status,
                notes or ("公办普通本科批，先作为厦门 2022 E_B 主口径补齐候选。" if status == "include_B_main" else "分区域招生范围需人工决定是否并入厦门主口径。"),
            )
        )

    def add_x_only(school: str, page: int, group: str, code: str, major: str, plan: int, tuition: str, scope: str, school_type: str = "公办", location: str = "厦门市", status: str = "include_X_only", notes: str = "") -> None:
        rows.append(
            record(
                school,
                location,
                school_type,
                scope,
                group,
                code,
                major,
                major,
                "智能制造/自动化候选",
                "X_expanded_candidate",
                plan,
                tuition,
                "",
                page,
                evidence[page],
                0,
                0,
                1,
                status,
                notes or "自动化、智能制造或机器人工程仅列 X 扩大口径候选，不进入 B 主口径。",
            )
        )

    def add_special(school: str, page: int, group: str, code: str, major: str, plan: int, tuition: str, scope: str, school_type: str, location: str, status: str, notes: str, x_only: bool = False) -> None:
        rows.append(
            record(
                school,
                location,
                school_type,
                scope,
                group,
                code,
                major,
                major,
                "AI基础专业群" if not x_only else "智能制造/自动化候选",
                "B_basic" if not x_only else "X_expanded_candidate",
                plan,
                tuition,
                "",
                page,
                evidence[page],
                0,
                1 if (not x_only and major in {"人工智能", "计算机科学与技术", "软件工程", "信息安全", "网络空间安全", "计算机类"}) else 0,
                1,
                status,
                notes,
            )
        )

    # 华侨大学，PDF 标注所在地为厦门市，未在用户重点列表中但符合抽取范围。
    for code, major, plan in [
        ("018", "人工智能", 8),
        ("019", "计算机科学与技术", 35),
        ("020", "软件工程", 15),
        ("021", "信息安全", 12),
        ("022", "物联网工程", 17),
        ("023", "数据科学与大数据技术", 25),
    ]:
        add_public_b("华侨大学", 97, "1108 专业组:999", code, major, plan, "5460", notes="PDF 标注华侨大学所在地为厦门市，需确认当前 E 端规则是否将华侨大学计入厦门。")
    add_x_only("华侨大学", 97, "1108 专业组:999", "014", "智能制造工程", 29, "5460", "普通类")

    # 厦门大学
    add_public_b("厦门大学", 118, "1220 专业组:999", "018", "计算机类", 72, "5460", notes="备注含计算机科学与技术、网络空间安全、人工智能、软件工程、数字媒体技术。")
    add_public_b("厦门大学", 118, "1220 专业组:999", "019", "数据科学与大数据技术", 12, "5460")
    add_special("厦门大学", 119, "1222 专业组:999", "005", "人工智能", 11, "2.8万林吉特/学年", "马来西亚分校", "公办", "厦门市/马来西亚雪兰莪州", "exclude_malaysia_campus", "马来西亚分校招生专业，不纳入厦门 E_B 主模型。")
    for code, major, plan, tuition in [
        ("006", "计算机科学与技术", 16, "2.7万林吉特/学年"),
        ("007", "软件工程", 14, "2.7万林吉特/学年"),
        ("009", "数据科学与大数据技术", 4, "2.8万林吉特/学年"),
        ("010", "网络空间安全", 5, "2.8万林吉特/学年"),
    ]:
        add_special("厦门大学", 119, "1222 专业组:999", code, major, plan, tuition, "马来西亚分校", "公办", "厦门市/马来西亚雪兰莪州", "exclude_malaysia_campus", "马来西亚分校招生专业，不纳入厦门 E_B 主模型。")
    add_public_b("厦门大学", 120, "1223 专业组:999", "004", "计算机类", 7, "5460", scope="面向厦门", notes="面向厦门招生计划单独记录，是否合并进主口径需人工决定。")
    add_public_b("厦门大学", 120, "1224 专业组:999", "004", "计算机类", 7, "5460", scope="面向漳州", notes="面向漳州招生计划单独记录，是否作为厦门 E 端供给需人工决定。")

    # 集美大学
    for code, major, plan, tuition in [
        ("076", "人工智能", 63, "5460"),
        ("077", "计算机科学与技术", 69, "5460"),
        ("078", "软件工程", 49, "9230"),
        ("079", "智能科学与技术", 63, "5460"),
        ("080", "数据科学与大数据技术", 89, "5460"),
        ("081", "网络空间安全", 52, "5460"),
    ]:
        add_public_b("集美大学", 100, "1112 专业组:999", code, major, plan, tuition)
    add_x_only("集美大学", 100, "1112 专业组:999", "069", "智能制造工程", 36, "5460", "普通类")
    for code, major, plan, tuition in [
        ("025", "人工智能", 5, "5460"),
        ("026", "计算机科学与技术", 5, "5460"),
        ("027", "软件工程", 5, "9230"),
        ("028", "智能科学与技术", 5, "5460"),
        ("029", "数据科学与大数据技术", 5, "5460"),
        ("030", "网络空间安全", 5, "5460"),
    ]:
        add_public_b("集美大学", 101, "1123 专业组:999", code, major, plan, tuition, scope="面向厦门", notes="面向厦门招生计划单独记录，是否合并进主口径需人工决定。")
    add_x_only("集美大学", 101, "1123 专业组:999", "018", "智能制造工程", 4, "5460", "面向厦门", status="manual_review_required", notes="面向厦门 X 候选，需人工决定是否用于扩展口径。")

    # 厦门理工学院
    for code, major, plan in [
        ("045", "人工智能", 18),
        ("047", "计算机科学与技术", 37),
        ("048", "软件工程", 65),
        ("049", "网络工程", 12),
        ("050", "物联网工程", 13),
        ("052", "数据科学与大数据技术", 20),
    ]:
        add_public_b("厦门理工学院", 123 if code in {"045", "047"} else 124, "1229 专业组:999", code, major, plan, "5460")
    add_special("厦门理工学院", 124, "1229 专业组:999", "051", "空间信息与数字技术", 18, "5460", "普通类", "公办", "厦门市", "manual_review_required", "该专业名称未列入本轮 B 基本口径清单，先作人工复核候选。")
    add_x_only("厦门理工学院", 123, "1229 专业组:999", "034", "智能制造工程", 43, "5460", "普通类")
    add_x_only("厦门理工学院", 123, "1229 专业组:999", "046", "自动化", 35, "5460", "普通类")
    for code, major, plan in [
        ("024", "人工智能", 10),
        ("026", "计算机科学与技术", 10),
        ("027", "软件工程", 22),
        ("028", "网络工程", 8),
        ("029", "物联网工程", 8),
        ("031", "数据科学与大数据技术", 8),
    ]:
        add_public_b("厦门理工学院", 125, "1231 专业组:999", code, major, plan, "5460", scope="面向厦门", notes="面向厦门招生计划单独记录，是否合并进主口径需人工决定。")
    add_special("厦门理工学院", 125, "1231 专业组:999", "030", "空间信息与数字技术", 5, "5460", "面向厦门", "公办", "厦门市", "manual_review_required", "该专业名称未列入本轮 B 基本口径清单，且为面向厦门范围。")
    add_x_only("厦门理工学院", 125, "1231 专业组:999", "013", "智能制造工程", 15, "5460", "面向厦门", status="manual_review_required", notes="面向厦门 X 候选，需人工决定是否用于扩展口径。")
    add_x_only("厦门理工学院", 125, "1231 专业组:999", "025", "自动化", 15, "5460", "面向厦门", status="manual_review_required", notes="面向厦门 X 候选，需人工决定是否用于扩展口径。")

    # 厦门医学院未发现 B 候选，不造记录，在报告中说明。

    # 独立学院/民办本科候选：不直接纳入主模型。
    for code, major, plan, tuition in [
        ("020", "计算机科学与技术", 46, "20500"),
        ("021", "软件工程", 46, "20500"),
        ("022", "物联网工程", 24, "20500"),
        ("023", "智能科学与技术", 26, "20500"),
        ("024", "数据科学与大数据技术", 41, "22000"),
    ]:
        add_special("厦门大学嘉庚学院", 121, "1226 专业组:999", code, major, plan, tuition, "普通类", "独立学院", "漳州市", "exclude_independent_college", "独立学院且 PDF 标注所在地为漳州市，不纳入厦门 E_B 主模型。")
    add_special("厦门大学嘉庚学院", 121, "1226 专业组:999", "018", "自动化", 27, "20500", "普通类", "独立学院", "漳州市", "exclude_independent_college", "独立学院 X 候选，不纳入厦门主模型。", x_only=True)
    add_special("厦门大学嘉庚学院", 121, "1226 专业组:999", "019", "机器人工程", 29, "20500", "普通类", "独立学院", "漳州市", "exclude_independent_college", "独立学院 X 候选，不纳入厦门主模型。", x_only=True)

    for code, major, plan, tuition in [
        ("015", "计算机科学与技术", 72, "18500"),
        ("016", "软件工程", 104, "20000"),
        ("017", "网络工程", 77, "20000"),
        ("018", "物联网工程", 70, "20000"),
        ("020", "数据科学与大数据技术", 55, "18500"),
    ]:
        add_special("集美大学诚毅学院", 102, "1124 专业组:999", code, major, plan, tuition, "普通类", "独立学院", "厦门市", "exclude_independent_college", "独立学院不纳入当前厦门 E_B 主模型，仅作追溯候选。")
    add_special("集美大学诚毅学院", 102, "1124 专业组:999", "011", "智能制造工程", 88, "20000", "普通类", "独立学院", "厦门市", "exclude_independent_college", "独立学院 X 候选，不纳入当前主模型。", x_only=True)
    add_special("集美大学诚毅学院", 102, "1124 专业组:999", "014", "自动化", 60, "18500", "普通类", "独立学院", "厦门市", "exclude_independent_college", "独立学院 X 候选，不纳入当前主模型。", x_only=True)

    for code, major, plan, tuition in [
        ("019", "软件工程", 180, "33000"),
        ("020", "物联网工程", 63, "28000"),
        ("021", "智能科学与技术", 147, "28000"),
        ("022", "数据科学与大数据技术", 115, "28000"),
    ]:
        add_special("厦门工学院", 122, "1227 专业组:999", code, major, plan, tuition, "普通类", "民办", "厦门市", "manual_review_required", "民办本科是否纳入 E_B 主模型缺少本地明确规则，先作人工复核候选。")
    add_special("厦门工学院", 122, "1227 专业组:999", "012", "智能制造工程", 82, "28000", "普通类", "民办", "厦门市", "manual_review_required", "民办 X 候选，是否纳入扩展口径需人工复核。", x_only=True)
    add_special("厦门工学院", 122, "1227 专业组:999", "018", "自动化", 63, "28000", "普通类", "民办", "厦门市", "manual_review_required", "民办 X 候选，是否纳入扩展口径需人工复核。", x_only=True)

    for code, major, plan, tuition in [
        ("010", "物联网工程", 66, "22000"),
        ("011", "数据科学与大数据技术", 30, "25000"),
    ]:
        add_special("厦门华厦学院", 123, "1228 专业组:999", code, major, plan, tuition, "普通类", "民办", "厦门市", "manual_review_required", "民办本科是否纳入 E_B 主模型缺少本地明确规则，先作人工复核候选。")
    add_special("厦门华厦学院", 123, "1228 专业组:999", "009", "机器人工程", 37, "25000", "普通类", "民办", "厦门市", "manual_review_required", "民办 X 候选，是否纳入扩展口径需人工复核。", x_only=True)


def make_summary(candidates: pd.DataFrame, input_pdf: Path, warnings: list[str]) -> dict[str, pd.DataFrame]:
    b = candidates[candidates["caliber"].eq("B_basic")].copy()
    x = candidates[candidates["caliber"].eq("X_expanded_candidate")].copy()
    main_b = b[b["include_status"].eq("include_B_main")]
    scope_review = b[(b["include_status"].eq("manual_review_required")) & (b["admission_scope"].str.contains("面向", na=False))]
    private_review = b[(b["include_status"].eq("manual_review_required")) & (b["school_type"].eq("民办"))]
    independent = b[b["include_status"].eq("exclude_independent_college")]
    malaysia = b[b["include_status"].eq("exclude_malaysia_campus")]
    city_summary = pd.DataFrame(
        [
            {
                "year": TARGET_YEAR,
                "city": TARGET_CITY,
                "input_pdf": str(input_pdf),
                "current_latest_panel_missing_E_confirmed": True,
                "B_main_candidate_plan_count": int(main_b["plan_count"].sum()),
                "B_main_candidate_school_count": int(main_b["school_name"].nunique()),
                "B_main_candidate_row_count": len(main_b),
                "B_scope_specific_manual_review_plan_count": int(scope_review["plan_count"].sum()),
                "B_private_manual_review_plan_count": int(private_review["plan_count"].sum()),
                "B_independent_excluded_plan_count": int(independent["plan_count"].sum()),
                "B_malaysia_excluded_plan_count": int(malaysia["plan_count"].sum()),
                "X_expanded_candidate_plan_count": int(x["plan_count"].sum()),
                "candidate_schools_found": "、".join(sorted(candidates["school_name"].unique())),
                "B_main_schools": "、".join(sorted(main_b["school_name"].unique())),
                "can_fill_xiamen_2022_E_B_gap": True,
                "recommended_use": "先用 B_main_candidate_plan_count 作为厦门2022 E端B基本口径补齐候选；面向厦门/漳州、民办、独立学院、马来西亚分校需人工确认后再决定是否合并。",
                "warnings": "；".join(warnings),
            }
        ]
    )
    school_summary = (
        candidates.groupby(["school_name", "school_location", "school_type", "admission_scope", "caliber", "include_status"], dropna=False)
        .agg(row_count=("major_original", "size"), plan_count=("plan_count", "sum"), majors=("major_standard", lambda s: "、".join(s.astype(str))))
        .reset_index()
    )
    status_summary = (
        candidates.groupby(["caliber", "include_status"], dropna=False)
        .agg(row_count=("major_original", "size"), plan_count=("plan_count", "sum"), school_count=("school_name", "nunique"))
        .reset_index()
    )
    scope_summary = (
        candidates.groupby(["admission_scope", "caliber", "include_status"], dropna=False)
        .agg(row_count=("major_original", "size"), plan_count=("plan_count", "sum"), schools=("school_name", lambda s: "、".join(sorted(set(s.astype(str))))))
        .reset_index()
    )
    return {
        "01_city_year_summary": city_summary,
        "02_school_summary": school_summary,
        "03_status_summary": status_summary,
        "04_scope_summary": scope_summary,
    }


def write_xlsx(path: Path, sheets: dict[str, pd.DataFrame]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)


def make_report(run_id: str, input_pdf: Path, candidates: pd.DataFrame, summary: pd.DataFrame, warnings: list[str]) -> str:
    main_total = int(summary.loc[0, "B_main_candidate_plan_count"])
    scope_total = int(summary.loc[0, "B_scope_specific_manual_review_plan_count"])
    private_total = int(summary.loc[0, "B_private_manual_review_plan_count"])
    independent_total = int(summary.loc[0, "B_independent_excluded_plan_count"])
    malaysia_total = int(summary.loc[0, "B_malaysia_excluded_plan_count"])
    main_school_lines = []
    b_main = candidates[candidates["include_status"].eq("include_B_main")]
    for school, df in b_main.groupby("school_name"):
        main_school_lines.append(f"- {school}：{int(df['plan_count'].sum())}，{ '、'.join(df['major_standard'].astype(str)) }")
    scope_lines = []
    for (school, scope), df in candidates[candidates["include_status"].eq("manual_review_required") & candidates["admission_scope"].str.contains("面向", na=False)].groupby(["school_name", "admission_scope"]):
        scope_lines.append(f"- {school}（{scope}）：{int(df['plan_count'].sum())}，需人工决定是否合并")
    return f"""# 厦门 2022 年 E 端 B 基本口径缺失补齐核验报告

## 1. 本次运行信息

- run_id：{run_id}
- 输入 PDF：{input_pdf}
- 核验对象：city=厦门，year=2022，普通类·物理科目组本科批为主
- 本轮不重算 CCD，不覆盖 `data/panel/experimental_analysis/latest_experimental_analysis_base_panel_2019_2024.csv`。

## 2. 当前缺失确认

latest experimental base panel 中，厦门 2022 当前为 `data_status=missing_E`，`E_index` 与 `D` 均缺失。本轮仅生成补齐候选表，不直接写回 latest panel。

## 3. 是否能补齐厦门 2022 E 端缺口

可以。该 PDF 在本科批普通类物理科目组中提供了厦门市公办本科高校的 AI 基础专业群招生计划。按保守处理，公办普通本科批 B main 候选计划数为 **{main_total}**。

需要注意：该数值仍是“可人工复核的补齐候选”，不是已写回 CCD 的最终 E_index。分区域招生、马来西亚分校、独立学院、民办本科均未直接混入主模型。

## 4. 找到的厦门高校

本轮候选或核验覆盖：{summary.loc[0, 'candidate_schools_found']}。其中厦门医学院未发现 B 基本口径 AI 基础专业群候选专业。

## 5. B main 候选专业

{chr(10).join(main_school_lines)}

## 6. 普通类、面向厦门、面向漳州、合作/特殊类别处理

- 普通类公办本科批：进入 `include_B_main` 候选。
- 面向厦门、面向漳州：单独记录为 `manual_review_required`，本轮未擅自合并，B 候选计划数合计 {scope_total}。
- 马来西亚分校：标记 `exclude_malaysia_campus`，B 候选计划数 {malaysia_total}，不进入厦门主模型。
- 独立学院：标记 `exclude_independent_college`，B 候选计划数 {independent_total}，不进入主模型。
- 民办本科：由于未发现明确本地 E 端纳入规则，标记 `manual_review_required`，B 候选计划数 {private_total}。
- 自动化、智能制造、机器人工程：仅列 `X_expanded_candidate`，不进入 B 主口径。

## 7. 重点学校核验

- 厦门大学：普通类含 `计算机类`、`数据科学与大数据技术`；另有面向厦门、面向漳州计算机类，以及马来西亚分校相关专业，均已分开标记。
- 集美大学：普通类含人工智能、计算机科学与技术、软件工程、智能科学与技术、数据科学与大数据技术、网络空间安全；面向厦门同类专业单独记录。
- 厦门理工学院：普通类含人工智能、计算机科学与技术、软件工程、网络工程、物联网工程、数据科学与大数据技术；面向厦门同类专业单独记录。
- 厦门医学院：未发现 B 基本口径候选。
- 厦门大学嘉庚学院、集美大学诚毅学院、厦门工学院、厦门华厦学院：已记录候选，但未进入主模型。
- 华侨大学：PDF 标注所在地为厦门市，且有 B 候选专业；虽不在重点学校清单中，仍按抽取范围进入候选，后续需确认当前 E 端城市归属规则。

## 8. 风险与人工复核点

1. PDF 文本抽取来自招生计划册，需人工抽查 evidence_page 与原 PDF 表格是否一致。
2. 华侨大学城市归属需按 E 端既有规则确认。
3. 面向厦门/面向漳州计划是否并入城市 E 端，需要统一口径。
4. 民办本科和独立学院是否纳入主模型，需要先补规则，不建议直接混入。
5. 本轮只补 E 端候选，不生成新的 E_index、D 或 CCD。

## 9. 输出位置

- 候选表：`data/interim/e_system_recheck/{run_id}/xiamen_2022_E_B_candidates_{run_id}.xlsx`
- 城市年份汇总：`data/panel/e_system_recheck/{run_id}/xiamen_2022_E_B_city_year_summary_{run_id}.xlsx`
- latest 报告：`data/audit/e_system_recheck/latest_xiamen_2022_E_B_recheck_report.md`

## 10. warnings

{chr(10).join('- ' + w for w in warnings) if warnings else '- 无'}
"""


def main() -> None:
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    input_pdf, warnings = pick_pdf()
    if not LATEST_BASE_PANEL.exists():
        warnings.append(f"latest experimental base panel 不存在：{LATEST_BASE_PANEL}")

    reader = PdfReader(str(input_pdf))
    evidence_pages = [97, 100, 101, 102, 118, 119, 120, 121, 122, 123, 124, 125]
    evidence = {page: page_text(reader, page) for page in evidence_pages}

    rows: list[dict[str, Any]] = []
    add_records(rows, evidence)
    candidates = pd.DataFrame(rows, columns=CANDIDATE_COLUMNS)

    summary_sheets = make_summary(candidates, input_pdf, warnings)
    summary_df = summary_sheets["01_city_year_summary"]

    audit_dir = Path("data/audit/e_system_recheck") / run_id
    interim_dir = Path("data/interim/e_system_recheck") / run_id
    panel_dir = Path("data/panel/e_system_recheck") / run_id
    for directory in [audit_dir, interim_dir, panel_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    report_path = audit_dir / f"xiamen_2022_E_B_recheck_report_{run_id}.md"
    candidates_path = interim_dir / f"xiamen_2022_E_B_candidates_{run_id}.xlsx"
    summary_path = panel_dir / f"xiamen_2022_E_B_city_year_summary_{run_id}.xlsx"

    write_xlsx(
        candidates_path,
        {
            "01_candidates": candidates,
            "02_B_main": candidates[candidates["include_status"].eq("include_B_main")],
            "03_manual_review": candidates[candidates["include_status"].eq("manual_review_required")],
            "04_excluded": candidates[candidates["include_status"].str.startswith("exclude", na=False)],
            "05_X_only": candidates[candidates["caliber"].eq("X_expanded_candidate")],
        },
    )
    write_xlsx(summary_path, summary_sheets)
    report_path.write_text(make_report(run_id, input_pdf, candidates, summary_df, warnings), encoding="utf-8")

    latest_report = Path("data/audit/e_system_recheck/latest_xiamen_2022_E_B_recheck_report.md")
    latest_candidates = Path("data/interim/e_system_recheck/latest_xiamen_2022_E_B_candidates.xlsx")
    latest_summary = Path("data/panel/e_system_recheck/latest_xiamen_2022_E_B_city_year_summary.xlsx")
    latest_report.parent.mkdir(parents=True, exist_ok=True)
    latest_candidates.parent.mkdir(parents=True, exist_ok=True)
    latest_summary.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(report_path, latest_report)
    shutil.copy2(candidates_path, latest_candidates)
    shutil.copy2(summary_path, latest_summary)

    print(
        {
            "run_id": run_id,
            "candidate_rows": len(candidates),
            "B_main_candidate_plan_count": int(summary_df.loc[0, "B_main_candidate_plan_count"]),
            "report": str(report_path),
            "candidates": str(candidates_path),
            "summary": str(summary_path),
        }
    )


if __name__ == "__main__":
    main()
