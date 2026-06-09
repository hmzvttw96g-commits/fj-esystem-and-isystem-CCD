#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Refine system-boundary audit for researcher/public-institution roles.

This script reads the latest system-boundary job-record review workbook and
writes a v2 workbook/report with employer-sector, job-function, evidence-level,
and refined system-mapping fields. It does not recalculate CCD or modify the
latest experimental base panel.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


INPUT_REVIEW = Path("data/interim/system_boundary_audit/latest_system_boundary_audit_job_record_review.xlsx")
OUTPUT_REVIEW_V2 = Path("data/interim/system_boundary_audit/latest_system_boundary_audit_job_record_review_v2.xlsx")
OUTPUT_REPORT_V2 = Path("data/audit/system_boundary_audit/latest_system_boundary_audit_report_v2.md")

HIGH_REVIEW_TERMS = [
    "研究员",
    "科研",
    "研究院",
    "技术研究院",
    "产业技术",
    "工程技术中心",
    "新型研发机构",
    "智能制造研究院",
    "工业互联网研究院",
    "技术转化",
    "成果转化",
    "企业服务",
    "产业化",
    "工程化",
]

UNIVERSITY_TERMS = ["高校", "大学", "学院", "师范学院", "职业技术大学", "教师", "教授", "讲师", "实验员"]
FINANCIAL_TERMS = ["金控", "银行", "基金", "担保", "融资", "金融"]
PUBLIC_TERMS = ["政府", "人社局", "教育局", "科技局", "工信局", "事业单位", "公共机构", "机关"]
TECH_TRANSFER_INSTITUTION_TERMS = ["产业技术研究院", "新型研发机构", "工程技术研究中心", "工业互联网研究院", "智能制造研究院", "技术研究院"]
TECH_TRANSFER_FUNCTION_TERMS = ["技术转化", "成果转化", "企业服务", "产业化", "工程化", "工程应用", "服务企业", "企业研发"]
PROJECT_TERMS = ["项目公告", "项目证据", "科技计划", "政府项目", "project_evidence", "government_project", "工业互联网", "智能制造"]


def clean(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def has_any(text: str, terms: list[str]) -> bool:
    return any(term.lower() in text.lower() or term in text for term in terms)


def build_text(row: pd.Series) -> str:
    fields = [
        "employer_name",
        "company_name",
        "job_title",
        "job_description",
        "source_type",
        "official_level",
        "source_file",
        "original_job_classification",
        "detected_boundary_type",
        "corrected_system_mapping",
        "correction_reason",
    ]
    return " ".join(clean(row.get(field)) for field in fields)


def infer_employer_sector(row: pd.Series) -> str:
    text = build_text(row)
    source_type = clean(row.get("source_type"))
    if has_any(text, FINANCIAL_TERMS):
        return "financial_institution"
    if has_any(text, TECH_TRANSFER_INSTITUTION_TERMS):
        return "industry_research_institute"
    if "university_employment_event" in source_type:
        return "university_employment_platform"
    if has_any(text, UNIVERSITY_TERMS):
        return "university"
    if has_any(text, ["事业单位", "public_institution"]):
        return "public_institution"
    if has_any(text, PUBLIC_TERMS):
        return "government_agency"
    if clean(row.get("company_name")):
        return "enterprise_or_organization"
    return "unknown"


def infer_job_function(row: pd.Series, employer_sector: str) -> str:
    text = build_text(row)
    job_title = clean(row.get("job_title"))
    if has_any(text, PROJECT_TERMS) and not job_title:
        return "project_evidence"
    if has_any(text, TECH_TRANSFER_FUNCTION_TERMS) or (
        employer_sector == "industry_research_institute" and has_any(text, ["研发", "工程", "产业", "技术"])
    ):
        return "tech_transfer"
    if has_any(text, ["教师", "教学", "教授", "讲师"]):
        return "teaching"
    if has_any(text, ["科研", "研究员", "博士后", "学术研究"]):
        return "academic_research"
    if employer_sector in {"government_agency", "public_institution"} and has_any(text, ["信息", "数字", "系统", "网络", "软件", "计算机"]):
        return "public_sector_it"
    if employer_sector == "financial_institution":
        return "financial_it"
    if clean(row.get("original_job_classification")) in {"ai_job_strong", "ai_job_tool_based", "digital_tech_job", "industrial_digital_job"}:
        return "candidate_job_function"
    return "unknown"


def infer_evidence_level(row: pd.Series, job_function: str) -> str:
    text = build_text(row)
    if job_function == "project_evidence":
        return "project_or_policy_evidence"
    if has_any(text, ["附件", "RAR", "attachment", "manual_required"]):
        return "attachment_pending"
    if clean(row.get("job_title")) and clean(row.get("source_url")):
        return "explicit_job_record"
    if clean(row.get("original_job_classification")) == "weak_only_review":
        return "weak_text_only"
    return "insufficient_evidence"


def infer_v2_mapping(row: pd.Series, employer_sector: str, job_function: str, evidence_level: str) -> tuple[str, bool, str]:
    original_mapping = clean(row.get("corrected_system_mapping"))
    text = build_text(row)
    if job_function == "project_evidence":
        return "I_project_evidence_only", False, "项目公告或政策材料仍只能作为项目证据，不能计入岗位数量。"
    if employer_sector == "financial_institution":
        return "F_financial_candidate", False, "金融机构、金控、银行、基金、担保等岗位留作 F 端扩展，不进入当前 E-I 主模型。"
    if employer_sector == "university" and job_function == "teaching":
        return "E_education_extension", False, "高校教师岗属于教育系统延伸，不进入 I_job。"
    if employer_sector == "university" and job_function == "academic_research":
        return "E_research_extension", False, "高校学术科研岗位属于教育/科研延伸，不进入 I_job。"
    if employer_sector in {"government_agency", "public_institution"} and job_function == "public_sector_it":
        return "G_public_sector_digital_demand", False, "普通公共部门或事业单位内部信息化需求不进入 I_job。"
    if employer_sector == "industry_research_institute" and job_function == "tech_transfer":
        return "I_tech_transfer_candidate", False, "产业技术研究院或新型研发机构岗位可能服务企业研发/技术转化，需高优先级人工复核后再决定是否进入 I 端。"
    if job_function == "tech_transfer" and has_any(text, TECH_TRANSFER_FUNCTION_TERMS):
        return "I_tech_transfer_candidate", False, "记录含技术转化、成果转化、企业服务、工程化或产业化证据，需人工复核。"
    if employer_sector == "university_employment_platform":
        return "manual_review_required", False, "高校就业平台来源需区分企业招聘与高校自身岗位。"
    if has_any(text, HIGH_REVIEW_TERMS):
        return "manual_review_required", False, "含研究员/科研/研究院/技术转化相关词，不能一刀切纳入或排除。"
    if original_mapping == "I_industry":
        return "I_industry", True, "已识别为企业产业端候选，仍需保留人工复核。"
    if original_mapping:
        return original_mapping, False, "沿用上一轮边界映射，但按 v2 字段保留复核。"
    return "manual_review_required", False, "信息不足，进入人工复核。"


def priority_for(row: pd.Series, mapping_v2: str, job_function: str) -> str:
    text = build_text(row)
    if has_any(text, HIGH_REVIEW_TERMS) or mapping_v2 in {"I_tech_transfer_candidate", "E_research_extension"}:
        return "high"
    if mapping_v2 in {"manual_review_required", "G_public_sector_digital_demand"}:
        return "medium"
    return "low"


def enhance(df: pd.DataFrame) -> pd.DataFrame:
    enhanced = df.copy()
    employer_sectors = []
    job_functions = []
    evidence_levels = []
    mappings = []
    include_i = []
    priorities = []
    reasons = []
    for _, row in enhanced.iterrows():
        employer_sector = infer_employer_sector(row)
        job_function = infer_job_function(row, employer_sector)
        evidence_level = infer_evidence_level(row, job_function)
        mapping, include, reason = infer_v2_mapping(row, employer_sector, job_function, evidence_level)
        priority = priority_for(row, mapping, job_function)
        employer_sectors.append(employer_sector)
        job_functions.append(job_function)
        evidence_levels.append(evidence_level)
        mappings.append(mapping)
        include_i.append(include)
        priorities.append(priority)
        reasons.append(reason)
    enhanced["employer_sector"] = employer_sectors
    enhanced["job_function"] = job_functions
    enhanced["evidence_level"] = evidence_levels
    enhanced["corrected_system_mapping_v2"] = mappings
    enhanced["corrected_include_in_I_job_v2"] = include_i
    enhanced["manual_review_priority"] = priorities
    enhanced["v2_correction_reason"] = reasons
    return enhanced


def write_excel(path: Path, sheets: dict[str, pd.DataFrame]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            safe = sheet_name[:31]
            df.to_excel(writer, index=False, sheet_name=safe)
            ws = writer.book[safe]
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for col_cells in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col_cells[:100])
                ws.column_dimensions[col_cells[0].column_letter].width = min(max(max_len + 2, 12), 58)


def write_report(path: Path, enhanced: pd.DataFrame) -> None:
    high_count = int((enhanced["manual_review_priority"] == "high").sum())
    tech_transfer_count = int((enhanced["corrected_system_mapping_v2"] == "I_tech_transfer_candidate").sum())
    e_research_count = int((enhanced["corrected_system_mapping_v2"] == "E_research_extension").sum())
    still_excluded = [
        "高校教师岗、高校内部学术科研岗、高校实验员岗",
        "普通政府机关、普通事业单位、公共部门内部信息化岗",
        "金控、银行、基金、担保、融资平台等金融机构信息技术岗",
        "项目公告、产业政策、科技计划等非岗位证据",
    ]
    lines = [
        "# E/I 系统边界审计 v2 修正说明",
        "",
        "## 1. 为什么修正",
        "上一轮把政府/事业单位岗位多数统一转为 G_public_sector_digital_demand，适合排除普通公共部门信息化岗位，但对“研究员”“产业技术研究院”“新型研发机构”“工程技术研究中心”等岗位过于粗糙。研究员岗位不能只按单位性质判断，需要看岗位功能和机构功能。",
        "",
        "## 2. 修正后的三步判定法",
        "1. `employer_sector`：先判断用人单位是高校、政府机关、普通事业单位、产业技术研究院、新型研发机构、企业还是金融机构。",
        "2. `job_function`：再判断岗位功能是教学、学术科研、公共部门信息化、企业研发、技术转化、工程化、产业化应用还是项目证据。",
        "3. `system_mapping`：最后确定系统归属，不能只看岗位关键词或单位性质。",
        "",
        "## 3. 仍然不能进入 I_job 的岗位",
    ]
    lines.extend([f"- {item}" for item in still_excluded])
    lines.extend(
        [
            "",
            "## 4. 可作为 I_tech_transfer_candidate 的岗位类型",
            "- 产业技术研究院、新型研发机构、工程技术研究中心、工业互联网研究院、智能制造研究院中的研究员/工程师岗位；",
            "- 证据明确显示服务企业研发、技术转化、成果转化、工程化、产业化应用或企业服务的岗位；",
            "- 这些记录仍是 candidate，不能自动进入 I_job，必须人工复核。",
            "",
            "## 5. 需要人工复核的记录",
            f"- 研究员/科研/研究院/技术转化相关高优先级复核记录数：{high_count}",
            f"- 当前识别为 I_tech_transfer_candidate 的记录数：{tech_transfer_count}",
            f"- 当前识别为 E_research_extension 的记录数：{e_research_count}",
            "",
            "## 6. 是否需要重跑 CCD",
            "不需要。本轮只修正规则和复核映射，尚未把岗位/技能数据正式纳入 I_index。",
            "",
            "## 7. 是否需要重新分类泉州 2019/2020 岗位候选",
            "需要。泉州师范学院教师岗仍应转入 E_education_extension；泉州金控信息技术岗仍应转入 F_financial_candidate；事业单位岗位附件需要在 v2 字段下重新确认是否只是普通公共部门岗位，或是否存在产业技术转化型研究机构岗位。",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if not INPUT_REVIEW.exists():
        raise FileNotFoundError(f"Missing input review workbook: {INPUT_REVIEW}")
    xl = pd.ExcelFile(INPUT_REVIEW)
    all_records = pd.read_excel(INPUT_REVIEW, sheet_name="01_all_suspect_records")
    enhanced = enhance(all_records)
    sheets = {
        "01_all_suspect_records_v2": enhanced,
        "02_high_priority_research": enhanced[enhanced["manual_review_priority"] == "high"],
        "03_I_tech_transfer_candidates": enhanced[enhanced["corrected_system_mapping_v2"] == "I_tech_transfer_candidate"],
        "04_E_research_or_education": enhanced[
            enhanced["corrected_system_mapping_v2"].isin(["E_research_extension", "E_education_extension"])
        ],
        "05_G_public_sector": enhanced[enhanced["corrected_system_mapping_v2"] == "G_public_sector_digital_demand"],
        "06_F_financial_candidate": enhanced[enhanced["corrected_system_mapping_v2"] == "F_financial_candidate"],
        "07_manual_review_required": enhanced[
            enhanced["corrected_system_mapping_v2"].isin(["manual_review_required", "exclude_or_review"])
        ],
        "08_mapping_summary": enhanced["corrected_system_mapping_v2"].value_counts().rename_axis("corrected_system_mapping_v2").reset_index(name="record_count"),
    }
    write_excel(OUTPUT_REVIEW_V2, sheets)
    write_report(OUTPUT_REPORT_V2, enhanced)
    print(
        {
            "output_review_v2": OUTPUT_REVIEW_V2.as_posix(),
            "output_report_v2": OUTPUT_REPORT_V2.as_posix(),
            "high_priority_research_count": int((enhanced["manual_review_priority"] == "high").sum()),
            "i_tech_transfer_candidate_count": int((enhanced["corrected_system_mapping_v2"] == "I_tech_transfer_candidate").sum()),
            "records": int(len(enhanced)),
        }
    )


if __name__ == "__main__":
    main()
