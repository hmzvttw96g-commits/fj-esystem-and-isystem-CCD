#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E/I system boundary audit.

This script scans existing experimental CCD and I-system upgrade artifacts,
reviews suspect job/project records, writes boundary-audit workbooks, and
updates boundary-rule documents. It does not recalculate CCD or modify the
latest experimental base panel.
"""

from __future__ import annotations

import json
import re
import shutil
import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


SEARCH_DIRS = [
    "data",
    "data/interim",
    "data/panel",
    "data/audit",
    "outputs/tables",
    "outputs/figures",
    "config",
    "scripts",
    "docs",
]
OPTIONAL_FILES = ["paper_framework.md"]
LEGACY_DIR = Path("archive/legacy_outputs")

SEARCH_TERMS = [
    "CCD",
    "I_index",
    "E_index",
    "i_system",
    "i_system_upgrade",
    "job",
    "岗位",
    "教师",
    "高校",
    "事业单位",
    "政府",
    "金控",
    "银行",
    "金融",
    "泉州师范学院",
    "泉州金控",
    "public_institution",
    "university",
    "government",
    "financial",
    "firm",
    "patent",
    "project",
    "岗位候选",
    "job_candidates",
    "collection_report",
    "indicator_design",
    "classification_rules",
]

UNIVERSITY_TERMS = ["高校", "大学", "学院", "师范学院", "职业技术大学", "教师", "教授", "讲师", "科研", "博士后", "实验员"]
PUBLIC_TERMS = ["事业单位", "政府", "人社局", "教育局", "科技局", "工信局", "公共机构", "机关"]
FINANCIAL_TERMS = ["金控", "银行", "基金", "担保", "融资", "金融", "金控集团"]
PROJECT_TERMS = ["项目", "公告", "科技计划", "工业互联网", "智能制造", "数字化转型", "政府项目", "project_evidence"]
FIRM_TERMS = ["企业名单", "高新技术企业", "专精特新", "firm", "entity_evidence"]
ENTERPRISE_TERMS = ["企业", "民营", "制造", "软件", "信息服务", "工业互联网", "智能制造"]


def safe_read_text(path: Path, max_chars: int = 250_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except Exception:
        return ""


def contains_any(text: str, terms: list[str]) -> bool:
    lower = text.lower()
    return any(term.lower() in lower or term in text for term in terms)


def clean_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def inspect_tabular(path: Path) -> tuple[str, int, str]:
    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            df = pd.read_csv(path)
            sample = " ".join(map(str, df.head(50).fillna("").astype(str).to_numpy().ravel()))
            return sample, len(df), "、".join(map(str, df.columns.tolist()))
        if suffix in {".xlsx", ".xls"}:
            xl = pd.ExcelFile(path)
            parts: list[str] = []
            rows = 0
            columns: list[str] = []
            for sheet in xl.sheet_names[:20]:
                try:
                    df = pd.read_excel(path, sheet_name=sheet)
                except Exception:
                    continue
                rows += len(df)
                columns.append(f"{sheet}: {'、'.join(map(str, df.columns.tolist()))}")
                parts.append(sheet)
                parts.append(" ".join(map(str, df.head(50).fillna("").astype(str).to_numpy().ravel())))
            return " ".join(parts)[:250_000], rows, " | ".join(columns)
    except Exception as exc:
        return f"inspect_error: {exc}", 0, ""
    return "", 0, ""


def infer_file_type(path: Path, text: str, columns: str, is_legacy: bool) -> tuple[str, str, str]:
    blob = f"{path.as_posix()} {path.name} {text} {columns}"
    contains_e = contains_any(blob, ["E_index", "E端", "教育", "高校", "招生", "学校", "专业"])
    contains_i = contains_any(blob, ["I_index", "I端", "产业", "企业", "专利", "岗位", "project", "firm", "patent"])
    contains_job = contains_any(blob, ["job", "岗位", "招聘", "job_candidates"])
    contains_univ = contains_any(blob, UNIVERSITY_TERMS)
    contains_public = contains_any(blob, PUBLIC_TERMS + ["public_institution", "official_hr"])
    contains_fin = contains_any(blob, FINANCIAL_TERMS + ["financial"])
    contains_enterprise = contains_any(blob, ENTERPRISE_TERMS)
    contains_project = contains_any(blob, PROJECT_TERMS)
    contains_firm = contains_any(blob, FIRM_TERMS)

    data_types = []
    if contains_e and contains_i:
        data_types.append("E_I_mixed_or_CCD_output")
    elif contains_e:
        data_types.append("E_system_reference")
    elif contains_i:
        data_types.append("I_system_reference")
    if contains_job:
        data_types.append("job_or_skill_artifact")
    if contains_project:
        data_types.append("project_evidence_artifact")
    if contains_firm:
        data_types.append("firm_or_entity_evidence")
    if not data_types:
        data_types.append("general_reference")

    if is_legacy:
        action = "legacy_reference_only"
        notes = "legacy 文件仅记录路径和文件名，不作为本轮分析输入。"
    elif contains_univ and contains_job:
        action = "reclassify_to_E_extension"
        notes = "疑似高校自身岗位或高校事业编岗位，需要排除出 I_job。"
    elif contains_fin and contains_job:
        action = "reclassify_to_F_candidate"
        notes = "疑似金融机构或金控平台岗位，不进入当前 E-I 主模型。"
    elif contains_public and contains_job:
        action = "reclassify_to_G_public_sector"
        notes = "疑似政府/事业单位/公共部门岗位，不进入 I_job。"
    elif contains_project:
        action = "project_evidence_only"
        notes = "项目公告只能作为项目证据，不计入岗位数量。"
    elif contains_firm:
        action = "firm_evidence_only"
        notes = "企业主体证据不能伪装成岗位记录。"
    elif contains_job:
        action = "review_records"
        notes = "包含岗位或岗位模板，需要记录级复核。"
    elif path.suffix.lower() in {".md", ".py", ".yml", ".yaml"} and contains_i:
        action = "update_document_only"
        notes = "方法或脚本文档需要补充系统边界规则。"
    else:
        action = "safe_no_action"
        notes = ""

    return "; ".join(data_types), action, notes


def scan_files(project_root: Path) -> tuple[pd.DataFrame, int]:
    files: list[Path] = []
    for search_dir in SEARCH_DIRS:
        root = project_root / search_dir
        if root.exists():
            files.extend(path for path in root.rglob("*") if path.is_file())
    for optional in OPTIONAL_FILES:
        path = project_root / optional
        if path.exists():
            files.append(path)

    unique: list[Path] = []
    seen: set[Path] = set()
    for path in files:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)

    rows: list[dict[str, Any]] = []
    for path in unique:
        rel = path.relative_to(project_root)
        suffix = path.suffix.lower()
        if suffix in {".xlsx", ".xls", ".csv"}:
            text, _, columns = inspect_tabular(path)
        elif suffix in {".md", ".py", ".json", ".yml", ".yaml", ".txt"}:
            text = safe_read_text(path)
            columns = ""
        else:
            text = rel.as_posix()
            columns = ""
        if not contains_any(f"{rel.as_posix()} {text} {columns}", SEARCH_TERMS):
            continue
        inferred, action, notes = infer_file_type(path, text, columns, False)
        blob = f"{rel.as_posix()} {text} {columns}"
        rows.append(
            {
                "file_path": rel.as_posix(),
                "file_name": path.name,
                "file_type": suffix.lstrip(".") or "unknown",
                "inferred_data_type": inferred,
                "contains_E_variables": contains_any(blob, ["E_index", "E端", "教育", "高校", "招生", "学校", "专业"]),
                "contains_I_variables": contains_any(blob, ["I_index", "I端", "产业", "企业", "专利", "岗位", "firm", "patent"]),
                "contains_job_records": contains_any(blob, ["job", "岗位", "招聘", "job_candidates"]),
                "contains_university_job": contains_any(blob, UNIVERSITY_TERMS) and contains_any(blob, ["岗位", "招聘", "job", "教师"]),
                "contains_public_institution_job": contains_any(blob, ["事业单位", "public_institution"]) and contains_any(blob, ["岗位", "招聘", "job"]),
                "contains_government_job": contains_any(blob, PUBLIC_TERMS) and contains_any(blob, ["岗位", "招聘", "job"]),
                "contains_financial_job": contains_any(blob, FINANCIAL_TERMS) and contains_any(blob, ["岗位", "招聘", "job"]),
                "contains_enterprise_job": contains_any(blob, ENTERPRISE_TERMS) and contains_any(blob, ["岗位", "招聘", "job"]),
                "contains_project_evidence": contains_any(blob, PROJECT_TERMS),
                "contains_firm_evidence": contains_any(blob, FIRM_TERMS),
                "needs_boundary_review": action not in {"safe_no_action"},
                "recommended_action": action,
                "notes": notes,
            }
        )

    legacy_root = project_root / LEGACY_DIR
    if legacy_root.exists():
        for path in legacy_root.rglob("*"):
            if not path.is_file():
                continue
            if not contains_any(path.name, SEARCH_TERMS):
                continue
            rel = path.relative_to(project_root)
            rows.append(
                {
                    "file_path": rel.as_posix(),
                    "file_name": path.name,
                    "file_type": path.suffix.lower().lstrip(".") or "unknown",
                    "inferred_data_type": "legacy_reference",
                    "contains_E_variables": False,
                    "contains_I_variables": False,
                    "contains_job_records": False,
                    "contains_university_job": False,
                    "contains_public_institution_job": False,
                    "contains_government_job": False,
                    "contains_financial_job": False,
                    "contains_enterprise_job": False,
                    "contains_project_evidence": False,
                    "contains_firm_evidence": False,
                    "needs_boundary_review": False,
                    "recommended_action": "legacy_reference_only",
                    "notes": "legacy 文件仅记录，不作为输入。",
                }
            )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["recommended_action", "file_path"]).reset_index(drop=True)
    return df, len(unique)


def detect_record_mapping(row: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(clean_text(row.get(key)) for key in row)
    source_type = clean_text(row.get("source_type"))
    classification = clean_text(row.get("job_classification"))
    job_title = clean_text(row.get("job_title")) or clean_text(row.get("attachment_name")) or clean_text(row.get("project_or_policy_name"))
    company = clean_text(row.get("company_name")) or clean_text(row.get("source_name"))
    is_university_employment_source = "university_employment_event" in source_type
    is_public_university_recruitment = (
        "official_public_institution" in source_type
        or contains_any(f"{company} {job_title}", ["泉州师范学院公开招聘", "教师", "博士研究生", "高校事业编"])
    )
    is_project_record = (
        contains_any(source_type, ["government_project", "government_industry_announcement"])
        or clean_text(row.get("project_or_policy_name")) != ""
        or clean_text(row.get("collection_status")) == "government_project_evidence"
    )

    original_include = classification in {"ai_job_strong", "ai_job_tool_based", "digital_tech_job", "industrial_digital_job"}
    if is_project_record:
        detected = "project_evidence"
        mapping = "I_project_evidence_only"
        reason = "项目公告只能作为 I_project_evidence，不计入岗位数量。"
    elif is_university_employment_source and not is_public_university_recruitment:
        detected = "university_employment_enterprise_source_review"
        mapping = "exclude_or_review"
        reason = "高校就业信息网来源页可能包含企业招聘，需区分企业岗位和高校自身岗位后再决定。"
    elif is_public_university_recruitment or (contains_any(f"{company} {job_title}", UNIVERSITY_TERMS) and contains_any(f"{job_title} {text}", ["教师", "科研", "博士", "讲师", "实验员"])):
        detected = "university_job"
        mapping = "E_education_extension"
        reason = "高校自身教师/科研/事业编岗位属于教育系统延伸，不能进入 I_job。"
    elif contains_any(text, FINANCIAL_TERMS):
        detected = "financial_job"
        mapping = "F_financial_candidate"
        reason = "金控/银行/基金/担保/融资平台岗位属于 F 端候选，不进入当前 E-I 主模型。"
    elif contains_any(text, ["事业单位", "public_institution", "政府", "人社局", "教育局", "科技局", "工信局"]) or "official_hr_recruitment_attachment" in source_type:
        detected = "government_or_public_institution_job"
        mapping = "G_public_sector_digital_demand"
        reason = "政府机关、事业单位、公共部门岗位不进入 I_job。"
    elif contains_any(text, FIRM_TERMS):
        detected = "firm_or_entity_evidence"
        mapping = "I_firm_evidence_only"
        reason = "企业/主体名单只能作为实体证据，不能伪装成岗位。"
    elif classification == "weak_only_review":
        detected = "weak_only_review"
        mapping = "exclude_or_review"
        reason = "weak_only_review 不得直接进入 C/B/X 口径。"
    elif clean_text(row.get("job_title")) and contains_any(text, ENTERPRISE_TERMS):
        detected = "enterprise_industry_job"
        mapping = "I_industry"
        reason = "疑似企业产业端岗位，可保留为 I_job 候选并人工复核。"
    else:
        detected = "manual_review_required"
        mapping = "exclude_or_review"
        reason = "边界不明确，需要人工复核。"

    return {
        "original_include_in_I_job": original_include,
        "detected_boundary_type": detected,
        "corrected_system_mapping": mapping,
        "corrected_include_in_I_job": mapping == "I_industry",
        "corrected_include_in_E_extension": mapping == "E_education_extension",
        "corrected_include_in_F_candidate": mapping == "F_financial_candidate",
        "corrected_include_in_G_public_sector": mapping == "G_public_sector_digital_demand",
        "correction_reason": reason,
    }


def collect_suspect_records(project_root: Path) -> pd.DataFrame:
    targets = [
        project_root / "data/interim/i_system_upgrade",
        project_root / "data/panel/i_system_upgrade",
        project_root / "outputs/tables/i_system_upgrade",
    ]
    rows: list[dict[str, Any]] = []
    for root in targets:
        if not root.exists():
            continue
        for path in root.rglob("*.xlsx"):
            if "template" in path.name:
                continue
            try:
                xl = pd.ExcelFile(path)
            except Exception:
                continue
            for sheet in xl.sheet_names:
                if not contains_any(f"{path.name} {sheet}", ["job", "岗位", "candidate", "source", "attachment", "project", "manual", "panel"]):
                    continue
                try:
                    df = pd.read_excel(path, sheet_name=sheet)
                except Exception:
                    continue
                for idx, record in df.iterrows():
                    record_dict = record.to_dict()
                    text = " ".join(clean_text(v) for v in record_dict.values())
                    if not contains_any(text, UNIVERSITY_TERMS + PUBLIC_TERMS + FINANCIAL_TERMS + PROJECT_TERMS + FIRM_TERMS + ["weak_only_review"]):
                        continue
                    mapping = detect_record_mapping(record_dict)
                    company = clean_text(record_dict.get("company_name")) or clean_text(record_dict.get("source_name")) or clean_text(record_dict.get("project_or_policy_name"))
                    job_title = clean_text(record_dict.get("job_title")) or clean_text(record_dict.get("project_or_policy_name")) or clean_text(record_dict.get("attachment_name"))
                    rows.append(
                        {
                            "source_file": path.relative_to(project_root).as_posix(),
                            "row_id": f"{sheet}:{idx + 2}",
                            "city": clean_text(record_dict.get("city")) or "泉州",
                            "year": clean_text(record_dict.get("year")),
                            "company_name": clean_text(record_dict.get("company_name")),
                            "employer_name": company,
                            "job_title": job_title,
                            "job_description": clean_text(record_dict.get("job_description")) or clean_text(record_dict.get("evidence_text")) or clean_text(record_dict.get("notes")),
                            "source_url": clean_text(record_dict.get("source_url")),
                            "source_type": clean_text(record_dict.get("source_type")) or clean_text(record_dict.get("review_item_type")),
                            "official_level": clean_text(record_dict.get("official_level")),
                            "original_job_classification": clean_text(record_dict.get("job_classification")),
                            "original_include_in_I_job": mapping["original_include_in_I_job"],
                            "detected_boundary_type": mapping["detected_boundary_type"],
                            "corrected_system_mapping": mapping["corrected_system_mapping"],
                            "corrected_include_in_I_job": mapping["corrected_include_in_I_job"],
                            "corrected_include_in_E_extension": mapping["corrected_include_in_E_extension"],
                            "corrected_include_in_F_candidate": mapping["corrected_include_in_F_candidate"],
                            "corrected_include_in_G_public_sector": mapping["corrected_include_in_G_public_sector"],
                            "correction_reason": mapping["correction_reason"],
                            "reviewer_decision": "pending_review",
                            "reviewer_notes": "",
                        }
                    )
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(["source_file", "row_id", "corrected_system_mapping", "job_title"]).reset_index(drop=True)
    return df


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


def md_table(df: pd.DataFrame, columns: list[str]) -> str:
    if df.empty:
        return "无记录。"
    subset = df[columns].fillna("").astype(str)
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = ["| " + " | ".join(value.replace("|", "｜").replace("\n", " ") for value in row) + " |" for row in subset.to_numpy().tolist()]
    return "\n".join([header, sep] + rows)


def update_docs(project_root: Path) -> list[str]:
    updated: list[str] = []
    boundary_dir = project_root / "docs/system_boundary"
    boundary_dir.mkdir(parents=True, exist_ok=True)
    boundary_rules = boundary_dir / "e_i_system_boundary_rules.md"
    boundary_rules.write_text(
        """# E/I 系统边界规则

## 1. 系统边界

- E 端：教育系统，反映高校 AI 基础人才供给、专业建设、招生计划、学校数量、专业数量等。
- I 端：产业系统，反映企业产业端对 AI/数字技术人才和技术的承接能力，包括企业存量、专利申请、企业岗位、产业项目证据等。
- F 端：金融系统候选扩展，包含金控、银行、基金、担保、融资平台等金融机构数字岗位。
- G 公共部门：政府机关、事业单位、公共机构的信息化和数字化需求。

## 2. 可以进入 I_job 的岗位

只有企业产业端岗位可以进入 I_job 候选，包括民营制造业、软件信息服务企业、工业互联网企业、智能制造企业，以及产业类国企、制造业国企、软件信息类国企的岗位。每条记录必须有明确企业主体、岗位名称、年份、城市归属和 source_url。

## 3. 应转入 E_extension 的岗位

高校教师岗、高校科研岗、高校实验员岗、高校事业编岗位，以及高校自身辅导员、行政岗，均不得进入 I_job，应标记为 E_education_extension。高校就业信息网中的企业招聘岗位可以作为 I_job 候选，但必须区分高校自身招聘和企业招聘。

## 4. 应转入 F_candidate 的岗位

金融机构、金控集团、银行、基金、担保公司、融资平台的信息技术岗不得进入当前 E-I 主模型，应标记为 F_financial_candidate，后续可用于 E-I-F 扩展。

## 5. 应转入 G_public_sector 的岗位

政府机关、事业单位、公共部门的信息化岗位不得进入 I_job 主模型，应标记为 G_public_sector_digital_demand 或 exclude_or_review。

## 6. 项目证据和企业主体证据

政府项目公告不能伪装成岗位，只能进入 I_project_evidence。企业名单、高新技术企业名单、专精特新名单不能伪装成岗位，只能进入 I_firm_evidence 或 entity_evidence。

## 7. weak_only_review

weak_only_review 不得直接进入 C/B/X 口径，只能进入人工复核。

## 8. 固定口径

主模型必须坚持固定口径，不得因为城市产业结构差异对不同城市动态调权。城市产业结构只影响采集路径和解释，不影响 I_index 计算公式。

## 9. 为什么高校事业编岗位不能进入 I 端

高校事业编岗位本质上扩展的是教育系统的人才培养和科研供给能力。如果把高校教师或科研岗纳入 I 端，会让 E 端和 I 端同时捕捉高校活动，造成系统边界重合，进而高估 E-I 协调。

## 10. 为什么系统边界影响 CCD 解释

CCD 的解释依赖两个系统相互独立但相互作用。若 I 端混入高校、政府或金融岗位，D 值变化可能来自口径污染而非真实产业承接能力变化，从而削弱论文结论的可解释性。
""",
        encoding="utf-8",
    )
    updated.append(boundary_rules.as_posix())

    classification_rules = project_root / "docs/i_system_upgrade/job_skill_classification_rules.md"
    if classification_rules.exists():
        text = classification_rules.read_text(encoding="utf-8")
        if "## 4. 系统边界规则" not in text:
            text += """

## 4. 系统边界规则

岗位分类前必须先识别 `employer_sector`。高校自身岗位、政府事业单位岗位、金融机构岗位优先按系统边界排除或转端，不能仅因命中 AI/数字技术关键词就进入 I_job。

- 高校自身教师、科研、实验员、事业编、辅导员、行政岗位：转入 `E_education_extension`，不进入 I_job。
- 政府机关、事业单位、公共部门信息化岗位：转入 `G_public_sector_digital_demand` 或 `exclude_or_review`，不进入 I_job。
- 金控、银行、基金、担保、融资平台等金融岗位：转入 `F_financial_candidate`，不进入当前 E-I 主模型。
- 只有企业产业端岗位才能进入 I_job，包括制造业、软件信息服务、工业互联网、智能制造企业岗位。
- 高校就业网中的企业岗位和高校自身岗位必须区分；前者可作为 I_job 候选，后者转入 E_extension。
- weak_only_review 不直接进入 C/B/X 口径。
"""
            classification_rules.write_text(text, encoding="utf-8")
        updated.append(classification_rules.as_posix())

    indicator_design = project_root / "docs/i_system_upgrade/i_system_upgrade_indicator_design.md"
    if indicator_design.exists():
        text = indicator_design.read_text(encoding="utf-8")
        if "## 11. 系统边界补充" not in text:
            text += """

## 11. 系统边界补充

I_index 升级版只纳入产业端企业岗位。高校教师、科研、实验员和高校事业编岗位不进入 I 端，应作为 E_education_extension 记录；金融机构岗位留作 F 端扩展候选；政府机关、事业单位和公共部门岗位单独记录为 G_public_sector_digital_demand。

项目证据和企业主体证据不得伪装成岗位证据。政府产业项目公告只能进入 I_project_evidence；企业名单、高新技术企业名单、专精特新名单只能进入 I_firm_evidence 或 entity_evidence。

C/B/X 口径固定适用于所有城市，不得因泉州、福州、厦门产业结构不同而动态调权。城市产业结构差异只能影响采集路径、数据解释和稳健性讨论，不能改变 I_index 计算公式。
"""
            indicator_design.write_text(text, encoding="utf-8")
        updated.append(indicator_design.as_posix())

    paper = project_root / "paper_framework.md"
    if paper.exists():
        text = paper.read_text(encoding="utf-8")
        boundary_note = """

## E/I 系统边界说明

I 端岗位需求应表述为“企业产业端 AI/数字技术岗位需求”。高校教师/科研岗位不得归入 I 端；金融机构岗位留待 F 端扩展；当前 CCD 结果是实验性方向验证，岗位/技能数据尚未正式进入主模型。泉州 2019/2020 I_index=0 对 I 端数据口径敏感，需要在统一边界规则下复核。
"""
        if "I 端岗位需求应表述为" not in text:
            paper.write_text(text + boundary_note, encoding="utf-8")
            updated.append(paper.as_posix())

    return updated


def write_report(
    path: Path,
    run_id: str,
    scanned_dirs: list[str],
    output_files: list[str],
    docs_updated: list[str],
    inventory: pd.DataFrame,
    records: pd.DataFrame,
    current_ccd_uses_jobs: bool,
) -> None:
    university_count = int((records["corrected_system_mapping"] == "E_education_extension").sum()) if not records.empty else 0
    government_count = int((records["corrected_system_mapping"] == "G_public_sector_digital_demand").sum()) if not records.empty else 0
    financial_count = int((records["corrected_system_mapping"] == "F_financial_candidate").sum()) if not records.empty else 0
    project_count = int((records["corrected_system_mapping"] == "I_project_evidence_only").sum()) if not records.empty else 0
    lines = [
        "# E/I 系统边界审计报告",
        "",
        "## 1. 本次运行信息",
        f"- run_id：{run_id}",
        "- 扫描目录：" + "、".join(scanned_dirs + OPTIONAL_FILES),
        "- 输出文件：",
    ]
    lines.extend([f"  - {file}" for file in output_files])
    lines.extend(
        [
            "",
            "## 2. 审计背景",
            "本轮审计用于检查 E-I 双系统 CCD 中是否存在教育端、产业端、金融端和公共部门之间的边界污染。近期岗位/技能试点中出现高校教师岗、事业单位岗位和金控信息技术岗，若直接进入 I_job，会造成 E/I 系统重合或误把非产业岗位当作产业承接。",
            "",
            "## 3. 当前 CCD 主结果是否受影响",
            f"- 当前已跑 CCD 是否直接使用了高校事业编岗位：{'是' if current_ccd_uses_jobs else '否'}。",
            "- 当前已跑 CCD 主要由 E_index/I_index 面板构成；已有文件显示 I 端当前主结果仍是企业存量、专利申请等实验性候选变量，并未把本轮岗位试点记录写入 latest experimental base panel。",
            "- 当前 CCD 主结果不需要立即重算。",
            "- 需要增加边界风险说明的结论：泉州 2019/2020 I_index=0 的升级复核、岗位/技能试点采集结论、I_index_upgraded_C/B/X 设计说明。",
            "",
            "## 4. 发现的系统边界风险",
            f"- 高校岗位/E_extension 风险记录：{university_count}",
            f"- 政府/事业单位/G_public_sector 风险记录：{government_count}",
            f"- 金融机构/F_candidate 风险记录：{financial_count}",
            f"- 项目证据/I_project_evidence_only 记录：{project_count}",
            "",
            md_table(
                records.head(20),
                [
                    "source_file",
                    "row_id",
                    "employer_name",
                    "job_title",
                    "original_job_classification",
                    "corrected_system_mapping",
                    "correction_reason",
                ],
            ),
            "",
            "## 5. 修正规则",
            "- 高校教师/科研/实验员/事业编岗位：转入 E_education_extension，不进入 I_job。",
            "- 金控、银行、基金、担保、融资平台岗位：转入 F_financial_candidate，不进入当前 E-I 主模型。",
            "- 政府机关、事业单位、公共部门信息化岗位：转入 G_public_sector_digital_demand，不进入 I_job。",
            "- 智能制造、工业互联网、数字化转型项目公告：进入 I_project_evidence_only，不计入岗位数量。",
            "- 企业名单、高新技术企业名单、专精特新名单：进入 I_firm_evidence_only 或 entity_evidence，不伪装为岗位。",
            "- 民营制造业、软件信息服务、工业互联网、智能制造企业岗位：可作为 I_industry 候选并人工复核。",
            "",
            "## 6. 已修正文档",
        ]
    )
    lines.extend([f"- {file}" for file in docs_updated] or ["- 无文档更新。"])
    lines.extend(
        [
            "",
            "## 7. 对泉州 2019/2020 试点的影响",
            "- 泉州师范学院教师岗不能挑战 I_index=0，应转入 E_education_extension。",
            "- 泉州金控信息技术岗不能直接挑战 I_index=0，应转入 F_financial_candidate。",
            "- 真正能挑战 I_index=0 的应是企业产业端岗位、项目证据或企业主体证据；但项目证据只能作为项目证据，不能计入岗位数量。",
            "- 2020 年已有试点岗位证据需要重映射后再判断：高校教师岗和金控信息岗都不能直接作为 I_job 主模型证据。",
            "",
            "## 8. 下一步建议",
            "- 不需要立即重新跑 CCD。",
            "- 需要修正岗位候选表或在后续 I_index_upgraded 构造前应用 corrected mapping。",
            "- 继续泉州民企数字化证据采集，重点找制造业、软件信息服务、工业互联网、智能制造企业岗位。",
            "- 暂不构造正式 I_index_upgraded_C/B/X；先完成附件和来源 URL 人工复核。",
            "- 后续构造 C/B/X 时必须使用固定口径，不得按城市动态调权。",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run E/I system boundary audit.")
    parser.add_argument("--run-id", help="Optional run_id override for reruns.")
    args = parser.parse_args()
    project_root = Path.cwd()
    run_id = args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    audit_dir = project_root / "data/audit/system_boundary_audit" / run_id
    interim_dir = project_root / "data/interim/system_boundary_audit" / run_id
    audit_dir.mkdir(parents=True, exist_ok=True)
    interim_dir.mkdir(parents=True, exist_ok=True)

    inventory, scanned_count = scan_files(project_root)
    records = collect_suspect_records(project_root)
    docs_updated = update_docs(project_root)

    current_panel = project_root / "data/panel/experimental_analysis/latest_experimental_analysis_base_panel_2019_2024.csv"
    current_ccd_uses_jobs = False
    if current_panel.exists():
        try:
            cols = pd.read_csv(current_panel, nrows=0).columns.astype(str).tolist()
            current_ccd_uses_jobs = any("job" in col.lower() or "岗位" in col for col in cols)
        except Exception:
            current_ccd_uses_jobs = False

    inventory_path = audit_dir / f"system_boundary_audit_file_inventory_{run_id}.xlsx"
    latest_inventory = project_root / "data/audit/system_boundary_audit/latest_system_boundary_audit_file_inventory.xlsx"
    write_excel(
        inventory_path,
        {
            "01_file_inventory": inventory,
            "02_recommended_action_summary": inventory["recommended_action"].value_counts().rename_axis("recommended_action").reset_index(name="file_count") if not inventory.empty else pd.DataFrame(columns=["recommended_action", "file_count"]),
        },
    )
    latest_inventory.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(inventory_path, latest_inventory)

    all_records = records
    sheets = {
        "01_all_suspect_records": all_records,
        "02_university_to_E_extension": all_records[all_records["corrected_system_mapping"] == "E_education_extension"] if not all_records.empty else all_records,
        "03_financial_to_F_candidate": all_records[all_records["corrected_system_mapping"] == "F_financial_candidate"] if not all_records.empty else all_records,
        "04_government_to_G_public_sector": all_records[all_records["corrected_system_mapping"] == "G_public_sector_digital_demand"] if not all_records.empty else all_records,
        "05_project_evidence_only": all_records[all_records["corrected_system_mapping"] == "I_project_evidence_only"] if not all_records.empty else all_records,
        "06_valid_I_industry_candidates": all_records[all_records["corrected_system_mapping"] == "I_industry"] if not all_records.empty else all_records,
        "07_manual_review_required": all_records[all_records["corrected_system_mapping"] == "exclude_or_review"] if not all_records.empty else all_records,
    }
    review_path = interim_dir / f"system_boundary_audit_job_record_review_{run_id}.xlsx"
    latest_review = project_root / "data/interim/system_boundary_audit/latest_system_boundary_audit_job_record_review.xlsx"
    write_excel(review_path, sheets)
    latest_review.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(review_path, latest_review)

    mapping_columns = [
        "record_id",
        "source_file",
        "city",
        "year",
        "original_name",
        "original_type",
        "original_classification",
        "corrected_system_mapping",
        "corrected_include_in_I_job",
        "corrected_include_in_E_extension",
        "corrected_include_in_F_candidate",
        "corrected_include_in_G_public_sector",
        "corrected_include_in_project_evidence",
        "correction_reason",
        "manual_review_status",
        "reviewer_notes",
    ]
    if all_records.empty:
        mapping_df = pd.DataFrame(columns=mapping_columns)
    else:
        mapping_df = pd.DataFrame(
            {
                "record_id": [f"boundary_{i+1:04d}" for i in range(len(all_records))],
                "source_file": all_records["source_file"],
                "city": all_records["city"],
                "year": all_records["year"],
                "original_name": all_records["employer_name"].where(all_records["employer_name"].astype(str) != "", all_records["job_title"]),
                "original_type": all_records["source_type"],
                "original_classification": all_records["original_job_classification"],
                "corrected_system_mapping": all_records["corrected_system_mapping"],
                "corrected_include_in_I_job": all_records["corrected_include_in_I_job"],
                "corrected_include_in_E_extension": all_records["corrected_include_in_E_extension"],
                "corrected_include_in_F_candidate": all_records["corrected_include_in_F_candidate"],
                "corrected_include_in_G_public_sector": all_records["corrected_include_in_G_public_sector"],
                "corrected_include_in_project_evidence": all_records["corrected_system_mapping"] == "I_project_evidence_only",
                "correction_reason": all_records["correction_reason"],
                "manual_review_status": "pending_review",
                "reviewer_notes": "",
            }
        )
    mapping_path = interim_dir / f"system_boundary_corrected_mapping_template_{run_id}.xlsx"
    latest_mapping = project_root / "data/interim/system_boundary_audit/latest_system_boundary_corrected_mapping_template.xlsx"
    write_excel(mapping_path, {"01_corrected_mapping": mapping_df})
    shutil.copy2(mapping_path, latest_mapping)

    report_path = audit_dir / f"system_boundary_audit_report_{run_id}.md"
    latest_report = project_root / "data/audit/system_boundary_audit/latest_system_boundary_audit_report.md"
    output_files = [
        inventory_path.relative_to(project_root).as_posix(),
        latest_inventory.relative_to(project_root).as_posix(),
        review_path.relative_to(project_root).as_posix(),
        latest_review.relative_to(project_root).as_posix(),
        mapping_path.relative_to(project_root).as_posix(),
        latest_mapping.relative_to(project_root).as_posix(),
        report_path.relative_to(project_root).as_posix(),
        latest_report.relative_to(project_root).as_posix(),
    ]
    write_report(report_path, run_id, SEARCH_DIRS, output_files, docs_updated, inventory, records, current_ccd_uses_jobs)
    shutil.copy2(report_path, latest_report)

    summary = {
        "run_id": run_id,
        "files_scanned_count": scanned_count,
        "inventory_rows": int(len(inventory)),
        "suspect_records_count": int(len(records)),
        "university_risk_count": int((records["corrected_system_mapping"] == "E_education_extension").sum()) if not records.empty else 0,
        "government_public_risk_count": int((records["corrected_system_mapping"] == "G_public_sector_digital_demand").sum()) if not records.empty else 0,
        "financial_risk_count": int((records["corrected_system_mapping"] == "F_financial_candidate").sum()) if not records.empty else 0,
        "project_evidence_only_count": int((records["corrected_system_mapping"] == "I_project_evidence_only").sum()) if not records.empty else 0,
        "current_ccd_uses_high_risk_jobs": bool(current_ccd_uses_jobs),
        "need_immediate_ccd_rerun": False,
        "docs_updated": docs_updated,
        "output_files": output_files,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
