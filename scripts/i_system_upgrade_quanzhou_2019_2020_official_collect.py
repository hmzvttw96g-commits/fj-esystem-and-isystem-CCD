#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""泉州 2019/2020 I 端岗位—技能官方来源小规模试点采集。

本脚本将人工核验到的官方/高校/政府网页证据结构化为岗位候选表、
城市年份岗位面板、采集报告和 manifest。它不重新计算 CCD，不读取
legacy 文件，不使用商业招聘平台作为主来源。
"""

from __future__ import annotations

import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


CITY = "泉州"
YEARS = [2019, 2020]
RUN_SCOPE = "quanzhou_2019_2020"

KEYWORDS_FILE = Path("config/i_system_upgrade_keywords.yml")
RULES_FILE = Path("docs/i_system_upgrade/job_skill_classification_rules.md")
TEMPLATE_FILE = Path("data/interim/i_system_upgrade/latest_i_system_upgrade_job_posting_candidates_template.xlsx")
PANEL_TEMPLATE_FILE = Path("data/panel/i_system_upgrade/latest_i_system_upgrade_job_city_year_panel_template.xlsx")
INVENTORY_FILE = Path("data/audit/i_system_upgrade/latest_i_system_upgrade_existing_data_inventory.xlsx")
RECHECK_PLAN_FILE = Path("data/audit/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_recheck_plan.md")

TECH_TRIGGERS = ["技术", "研发", "工程师", "算法", "开发", "数据"]
INDUSTRIAL_TRIGGERS = ["工程师", "技术", "研发", "自动化", "制造", "设备", "工业"]

FALLBACK_KEYWORDS = {
    "strong_ai_keywords": [
        "人工智能",
        "AI",
        "机器学习",
        "深度学习",
        "自然语言处理",
        "NLP",
        "计算机视觉",
        "CV",
        "图像识别",
        "语音识别",
        "大模型",
        "LLM",
        "AIGC",
        "推荐算法",
        "强化学习",
        "神经网络",
        "智能算法",
        "算法工程师",
        "数据智能",
    ],
    "ai_tool_keywords": [
        "TensorFlow",
        "PyTorch",
        "Keras",
        "OpenCV",
        "Transformers",
        "BERT",
        "GPT",
        "LangChain",
        "向量数据库",
        "知识图谱",
    ],
    "basic_digital_keywords": [
        "Python",
        "SQL",
        "Java",
        "数据分析",
        "数据挖掘",
        "数据建模",
        "大数据",
        "云计算",
        "Hadoop",
        "Spark",
        "数据仓库",
        "数据治理",
        "物联网",
        "工业互联网",
        "网络安全",
        "信息安全",
    ],
    "industrial_digital_keywords": [
        "智能制造",
        "机器视觉",
        "工业视觉",
        "自动化控制",
        "工业软件",
        "MES",
        "ERP",
        "PLC",
        "数字孪生",
        "智能工厂",
        "工业机器人",
        "智能装备",
        "数控系统",
    ],
    "weak_keywords": ["科技", "智能", "信息", "网络", "数字", "平台", "系统", "互联网"],
}

JOB_COLUMNS = [
    "city",
    "year",
    "source_city",
    "source_name",
    "source_type",
    "official_level",
    "company_name",
    "job_title",
    "job_description",
    "posting_date",
    "matched_strong_ai_keywords",
    "matched_ai_tool_keywords",
    "matched_basic_digital_keywords",
    "matched_industrial_digital_keywords",
    "matched_weak_keywords",
    "job_classification",
    "job_ai_score",
    "source_url",
    "evidence_text",
    "collection_status",
    "reviewer_decision",
    "reviewer_notes",
]

PANEL_COLUMNS = [
    "city",
    "year",
    "total_evidence_count",
    "total_job_count",
    "ai_job_strong_count",
    "ai_tool_based_job_count",
    "digital_tech_job_count",
    "industrial_digital_job_count",
    "weak_only_review_count",
    "government_project_evidence_count",
    "broad_ai_digital_job_count",
    "C_job_count",
    "B_job_count",
    "X_job_count",
    "ai_job_ratio",
    "broad_ai_digital_job_ratio",
    "avg_job_ai_score",
    "official_source_job_count",
    "university_source_job_count",
    "commercial_supplement_job_count",
    "data_status",
    "notes",
]


def ensure_not_legacy(path: Path) -> None:
    text = path.as_posix()
    if "archive/legacy_outputs" in text or "outputs/ccd_outputs" in text:
        raise ValueError(f"禁止读取 legacy 或旧式散落输出作为输入：{text}")


def parse_simple_keyword_yaml(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return FALLBACK_KEYWORDS
    ensure_not_legacy(path)
    keywords: dict[str, list[str]] = {}
    current_key: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith(":"):
            current_key = line[:-1]
            keywords.setdefault(current_key, [])
            continue
        if line.startswith("- ") and current_key:
            keywords[current_key].append(line[2:].strip())
    return keywords or FALLBACK_KEYWORDS


def matched_keywords(text: str, keywords: list[str]) -> list[str]:
    text_lower = text.lower()
    return [keyword for keyword in keywords if keyword.lower() in text_lower]


def has_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def classify_record(record: dict[str, Any], keywords: dict[str, list[str]]) -> dict[str, Any]:
    text = " ".join(
        str(record.get(key, "") or "")
        for key in ["job_title", "job_description", "evidence_text", "company_name"]
    )
    strong = matched_keywords(text, keywords.get("strong_ai_keywords", []))
    tools = matched_keywords(text, keywords.get("ai_tool_keywords", []))
    basic = matched_keywords(text, keywords.get("basic_digital_keywords", []))
    industrial = matched_keywords(text, keywords.get("industrial_digital_keywords", []))
    weak = matched_keywords(text, keywords.get("weak_keywords", []))

    if strong:
        classification = "ai_job_strong"
        score = 3.0
    elif tools and has_any(text, TECH_TRIGGERS):
        classification = "ai_job_tool_based"
        score = 2.5
    elif len(basic) >= 2 and has_any(text, TECH_TRIGGERS):
        classification = "digital_tech_job"
        score = 1.5
    elif industrial and has_any(text, INDUSTRIAL_TRIGGERS):
        classification = "industrial_digital_job"
        score = 1.2
    elif weak and not (strong or tools or basic or industrial):
        classification = "weak_only_review"
        score = 0.2
    else:
        classification = "non_ai_job"
        score = 0.0

    record["matched_strong_ai_keywords"] = "、".join(strong)
    record["matched_ai_tool_keywords"] = "、".join(tools)
    record["matched_basic_digital_keywords"] = "、".join(basic)
    record["matched_industrial_digital_keywords"] = "、".join(industrial)
    record["matched_weak_keywords"] = "、".join(weak)
    record["job_classification"] = classification
    record["job_ai_score"] = score
    return record


def build_source_pages() -> list[dict[str, Any]]:
    return [
        {
            "source_name": "泉州市国资委八家市属国企赴福州大学招聘公告",
            "source_type": "official_state_owned_enterprise_recruitment",
            "official_level": "municipal_government_department",
            "source_url": "https://gzw.quanzhou.gov.cn/gzdt/tzgg/201904/t20190408_1492150.htm",
            "year": 2019,
            "source_city": "泉州",
            "availability": "available",
            "notes": "页面含2019年市属国企招聘岗位信息，存在计算机/信息相关岗位线索，需人工复核是否纳入岗位指标。",
        },
        {
            "source_name": "福州大学2019届毕业生泉港石化专场双选会",
            "source_type": "university_employment_event",
            "official_level": "university_official",
            "source_url": "https://che.fzu.edu.cn/info/1055/4502.htm",
            "year": 2019,
            "source_city": "泉州",
            "availability": "available",
            "notes": "页面列示泉港石化企业岗位，更多是化工/设备/研发岗位，暂作为人工复核来源。",
        },
        {
            "source_name": "2020年泉州师范学院公开招聘博士研究生学历学位教师公告",
            "source_type": "official_public_institution_recruitment",
            "official_level": "municipal_hr_official",
            "source_url": "https://rsj.quanzhou.gov.cn/zwgk/zxdt/tzgg/202004/t20200430_2234402.htm",
            "year": 2020,
            "source_city": "泉州",
            "availability": "search_result_verified_open_timeout",
            "notes": "搜索结果显示官方页面与岗位需求表；页面打开超时，候选需人工复核附件。",
        },
        {
            "source_name": "2020年泉州市事业单位公开招聘编制内工作人员公告",
            "source_type": "official_hr_recruitment",
            "official_level": "municipal_hr_official",
            "source_url": "https://rsj.quanzhou.gov.cn/zwgk/zxdt/syzk/202008/t20200810_2403095.htm",
            "year": 2020,
            "source_city": "泉州",
            "availability": "available_with_attachment",
            "notes": "页面含岗位信息表RAR附件，附件需人工下载解析。",
        },
        {
            "source_name": "泉州市金控集团及权属企业公开招聘公告",
            "source_type": "official_state_owned_enterprise_recruitment",
            "official_level": "municipal_government_portal",
            "source_url": "https://www.quanzhou.gov.cn/zfb/xxgk/zfxxgkzl/rsxx/zkzp/202006/t20200602_2303269.htm",
            "year": 2020,
            "source_city": "泉州",
            "availability": "available",
            "notes": "页面列示信息技术岗，属于可人工复核的数字岗位线索。",
        },
        {
            "source_name": "泉州市工信局推进5G+工业互联网和智能制造报道",
            "source_type": "government_industry_announcement",
            "official_level": "municipal_industry_department",
            "source_url": "https://gxj.quanzhou.gov.cn/zwgk/gzdt/202011/t20201124_2463941.htm",
            "year": 2020,
            "source_city": "泉州",
            "availability": "available",
            "notes": "政府产业证据，不计入岗位数。",
        },
        {
            "source_name": "2019年泉州市级科技计划项目公示",
            "source_type": "government_project_announcement",
            "official_level": "municipal_science_department",
            "source_url": "https://kj.quanzhou.gov.cn/xxgk/tzgg/201911/t20191106_1937191.htm",
            "year": 2019,
            "source_city": "泉州",
            "availability": "available",
            "notes": "含机器视觉、智能控制、工业互联网相关项目线索，作为背景证据。",
        },
        {
            "source_name": "2020年丰泽区科技计划项目立项",
            "source_type": "government_project_announcement",
            "official_level": "district_government_department",
            "source_url": "https://qzfz.gov.cn/zwgk/kjzscq/kjyw/202007/t20200713_2385691.htm",
            "year": 2020,
            "source_city": "泉州",
            "availability": "available",
            "notes": "含物联网、AI算法、物流信息化等项目线索，作为背景证据。",
        },
    ]


def build_job_candidates(keywords: dict[str, list[str]]) -> list[dict[str, Any]]:
    raw_records = [
        {
            "city": CITY,
            "year": 2020,
            "source_city": "泉州",
            "source_name": "2020年泉州师范学院公开招聘博士研究生学历学位教师公告",
            "source_type": "official_public_institution_recruitment",
            "official_level": "municipal_hr_official",
            "company_name": "泉州师范学院",
            "job_title": "教师A24（计算机/软件工程/人工智能/物联网工程方向）",
            "job_description": "岗位需求表线索包含计算机应用技术、软件工程、人工智能、物联网工程、自动化控制等方向，需求人数5人。",
            "posting_date": "2020-04-30",
            "source_url": "https://rsj.quanzhou.gov.cn/zwgk/zxdt/tzgg/202004/t20200430_2234402.htm",
            "evidence_text": "官方人社页面搜索结果显示该招聘公告含岗位需求表；A24岗位方向包含人工智能、物联网工程、自动化控制等。",
            "collection_status": "probable_job_candidate",
            "reviewer_decision": "pending_review",
            "reviewer_notes": "官方页面打开超时，需人工下载岗位需求表复核。",
        },
        {
            "city": CITY,
            "year": 2020,
            "source_city": "泉州",
            "source_name": "泉州市金控集团及权属企业公开招聘公告",
            "source_type": "official_state_owned_enterprise_recruitment",
            "official_level": "municipal_government_portal",
            "company_name": "泉州金控集团及权属企业",
            "job_title": "信息技术岗",
            "job_description": "岗位要求数学、电子信息、计算机科学与技术类专业，掌握计算机软硬件技术基础和系统运行知识。",
            "posting_date": "2020-06-02",
            "source_url": "https://www.quanzhou.gov.cn/zfb/xxgk/zfxxgkzl/rsxx/zkzp/202006/t20200602_2303269.htm",
            "evidence_text": "泉州市政府门户公开招聘公告列示信息技术岗及计算机相关专业要求。",
            "collection_status": "probable_job_candidate",
            "reviewer_decision": "pending_review",
            "reviewer_notes": "按现有词典多为弱词命中，需人工判断是否作为数字技术岗位。",
        },
    ]
    return [classify_record(record, keywords) for record in raw_records]


def build_attachment_candidates() -> list[dict[str, Any]]:
    return [
        {
            "year": 2020,
            "source_name": "2020年泉州市事业单位公开招聘编制内工作人员岗位信息表",
            "source_type": "official_hr_recruitment_attachment",
            "official_level": "municipal_hr_official",
            "source_url": "https://rsj.quanzhou.gov.cn/zwgk/zxdt/syzk/202008/t20200810_2403095.htm",
            "attachment_name": "岗位信息表及其他附件（RAR）",
            "collection_status": "attachment_manual_required",
            "evidence_text": "官方人社页面提供岗位信息表压缩包附件；本轮未自动下载解析。",
            "reviewer_decision": "pending_review",
            "reviewer_notes": "需要人工下载附件并筛选计算机、软件、信息、安全、智能制造相关岗位。",
        },
        {
            "year": 2020,
            "source_name": "泉州师范学院公开招聘岗位需求表",
            "source_type": "official_public_institution_attachment",
            "official_level": "municipal_hr_official",
            "source_url": "https://rsj.quanzhou.gov.cn/zwgk/zxdt/tzgg/202004/t20200430_2234402.htm",
            "attachment_name": "2020年泉州师范学院公开招聘博士研究生学历学位教师岗位需求信息表",
            "collection_status": "attachment_manual_required",
            "evidence_text": "搜索结果显示官方公告含岗位需求信息表附件，需人工复核原附件。",
            "reviewer_decision": "pending_review",
            "reviewer_notes": "优先核验A24岗位和是否属于泉州本地岗位需求。",
        },
    ]


def build_government_project_evidence() -> list[dict[str, Any]]:
    return [
        {
            "year": 2019,
            "source_name": "2019年泉州市级科技计划项目公示",
            "source_type": "government_project_evidence",
            "official_level": "municipal_science_department",
            "source_url": "https://kj.quanzhou.gov.cn/xxgk/tzgg/201911/t20191106_1937191.htm",
            "project_or_policy_name": "机器视觉/智能控制/工业互联网相关科技计划项目",
            "matched_keywords": "机器视觉、智能控制、工业互联网",
            "evidence_text": "项目清单中出现机器视觉、智能管控、工业互联网等产业数字化方向。",
            "collection_status": "government_project_evidence",
            "reviewer_decision": "pending_review",
            "reviewer_notes": "只作为产业背景证据，不计入岗位数。",
        },
        {
            "year": 2019,
            "source_name": "泉州市工信工作总结",
            "source_type": "government_industry_announcement",
            "official_level": "municipal_industry_department",
            "source_url": "https://gxj.quanzhou.gov.cn/zwgk/ghjh/202002/t20200218_2037649.htm",
            "project_or_policy_name": "数字化车间、智能制造试点、工业互联网平台",
            "matched_keywords": "智能制造、数字化、工业互联网",
            "evidence_text": "工信工作材料显示泉州推进数字化车间、智能制造和工业互联网相关工作。",
            "collection_status": "government_project_evidence",
            "reviewer_decision": "pending_review",
            "reviewer_notes": "链接可用性需人工复核。",
        },
        {
            "year": 2020,
            "source_name": "泉州市工信局推进5G+工业互联网和智能制造报道",
            "source_type": "government_industry_announcement",
            "official_level": "municipal_industry_department",
            "source_url": "https://gxj.quanzhou.gov.cn/zwgk/gzdt/202011/t20201124_2463941.htm",
            "project_or_policy_name": "5G+工业互联网与智能制造",
            "matched_keywords": "5G、工业互联网、智能制造",
            "evidence_text": "泉州市工信局页面显示2020年举办5G+工业互联网和智能制造相关活动。",
            "collection_status": "government_project_evidence",
            "reviewer_decision": "pending_review",
            "reviewer_notes": "不计入岗位数，可作为泉州产业端非零背景证据。",
        },
        {
            "year": 2020,
            "source_name": "2020年丰泽区科技计划项目立项",
            "source_type": "government_project_announcement",
            "official_level": "district_government_department",
            "source_url": "https://qzfz.gov.cn/zwgk/kjzscq/kjyw/202007/t20200713_2385691.htm",
            "project_or_policy_name": "物联网、AI算法、物流信息化等科技项目",
            "matched_keywords": "物联网、AI、算法、信息化",
            "evidence_text": "丰泽区科技项目清单出现AI算法、物联网、物流信息化等项目线索。",
            "collection_status": "government_project_evidence",
            "reviewer_decision": "pending_review",
            "reviewer_notes": "区级项目证据，不计入岗位数。",
        },
        {
            "year": 2020,
            "source_name": "泉州市工信局2020年工作总结",
            "source_type": "government_industry_announcement",
            "official_level": "municipal_industry_department",
            "source_url": "https://gxj.quanzhou.gov.cn/zwgk/ghjh/202102/t20210204_2508845.htm",
            "project_or_policy_name": "智能制造、工业互联网、上云上平台",
            "matched_keywords": "智能制造、工业互联网、云平台",
            "evidence_text": "工信材料显示泉州推进智能制造、工业互联网、企业上云上平台等工作。",
            "collection_status": "government_project_evidence",
            "reviewer_decision": "pending_review",
            "reviewer_notes": "链接可用性需人工复核。",
        },
    ]


def build_manual_review(source_pages: list[dict[str, Any]], attachments: list[dict[str, Any]], gov_evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in attachments:
        rows.append(
            {
                "review_item_type": "attachment",
                "year": item["year"],
                "source_name": item["source_name"],
                "source_url": item["source_url"],
                "reason": item["reviewer_notes"],
                "reviewer_decision": "pending_review",
            }
        )
    for item in source_pages:
        if item["availability"] != "available":
            rows.append(
                {
                    "review_item_type": "source_page",
                    "year": item["year"],
                    "source_name": item["source_name"],
                    "source_url": item["source_url"],
                    "reason": item["notes"],
                    "reviewer_decision": "pending_review",
                }
            )
    for item in gov_evidence:
        if "需人工复核" in item.get("reviewer_notes", ""):
            rows.append(
                {
                    "review_item_type": "government_project_evidence",
                    "year": item["year"],
                    "source_name": item["source_name"],
                    "source_url": item["source_url"],
                    "reason": item["reviewer_notes"],
                    "reviewer_decision": "pending_review",
                }
            )
    return rows


def deduplicate_jobs(jobs: pd.DataFrame) -> pd.DataFrame:
    if jobs.empty:
        return jobs
    priority = {
        "municipal_hr_official": 1,
        "municipal_government_portal": 2,
        "municipal_government_department": 3,
        "university_official": 4,
    }
    jobs = jobs.copy()
    jobs["_priority"] = jobs["official_level"].map(priority).fillna(9)
    jobs = jobs.sort_values(["year", "company_name", "job_title", "_priority"])
    deduped = jobs.drop_duplicates(["year", "company_name", "job_title", "source_url"], keep="first")
    return deduped.drop(columns=["_priority"])


def build_panel(jobs: pd.DataFrame, gov: pd.DataFrame, attachments: pd.DataFrame, manual: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year in YEARS:
        year_jobs = jobs[jobs["year"] == year]
        year_gov = gov[gov["year"] == year]
        year_attach = attachments[attachments["year"] == year]
        year_manual = manual[manual["year"] == year]
        strong = int((year_jobs["job_classification"] == "ai_job_strong").sum())
        tool = int((year_jobs["job_classification"] == "ai_job_tool_based").sum())
        digital = int((year_jobs["job_classification"] == "digital_tech_job").sum())
        industrial = int((year_jobs["job_classification"] == "industrial_digital_job").sum())
        weak = int((year_jobs["job_classification"] == "weak_only_review").sum())
        c_count = strong + tool
        b_count = c_count + digital
        x_count = b_count + industrial
        official_jobs = int((year_jobs["source_type"].str.contains("official|state_owned|hr", case=False, na=False)).sum())
        university_jobs = int((year_jobs["source_type"].str.contains("university", case=False, na=False)).sum())
        total_jobs = int(len(year_jobs))
        total_evidence = total_jobs + int(len(year_gov)) + int(len(year_attach)) + int(len(year_manual))
        rows.append(
            {
                "city": CITY,
                "year": year,
                "total_evidence_count": total_evidence,
                "total_job_count": total_jobs,
                "ai_job_strong_count": strong,
                "ai_tool_based_job_count": tool,
                "digital_tech_job_count": digital,
                "industrial_digital_job_count": industrial,
                "weak_only_review_count": weak,
                "government_project_evidence_count": int(len(year_gov)),
                "broad_ai_digital_job_count": x_count,
                "C_job_count": c_count,
                "B_job_count": b_count,
                "X_job_count": x_count,
                "ai_job_ratio": c_count / total_jobs if total_jobs else pd.NA,
                "broad_ai_digital_job_ratio": x_count / total_jobs if total_jobs else pd.NA,
                "avg_job_ai_score": year_jobs["job_ai_score"].mean() if total_jobs else pd.NA,
                "official_source_job_count": official_jobs,
                "university_source_job_count": university_jobs,
                "commercial_supplement_job_count": 0,
                "data_status": "candidate_evidence_found_pending_review" if total_evidence else "no_evidence_found",
                "notes": "项目公告未计入岗位数；所有岗位候选均需人工复核后才能进入升级版指标。",
            }
        )
    return pd.DataFrame(rows, columns=PANEL_COLUMNS)


def write_excel(path: Path, sheets: dict[str, pd.DataFrame]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
            ws = writer.book[sheet_name[:31]]
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for col_cells in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col_cells[:100])
                ws.column_dimensions[col_cells[0].column_letter].width = min(max(max_len + 2, 12), 54)


def md_table(df: pd.DataFrame, columns: list[str]) -> str:
    if df.empty:
        return "无记录。"
    subset = df[columns].fillna("").astype(str)
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = [
        "| "
        + " | ".join(value.replace("\n", " ").replace("|", "｜") for value in row)
        + " |"
        for row in subset.to_numpy().tolist()
    ]
    return "\n".join([header, sep] + rows)


def write_report(path: Path, run_id: str, output_files: list[str], source_pages: pd.DataFrame, jobs: pd.DataFrame, attachments: pd.DataFrame, gov: pd.DataFrame, manual: pd.DataFrame, panel: pd.DataFrame) -> None:
    job_counts = jobs.groupby("year").size().to_dict() if not jobs.empty else {}
    strong_counts = jobs[jobs["job_classification"] == "ai_job_strong"].groupby("year").size().to_dict() if not jobs.empty else {}
    gov_counts = gov.groupby("year").size().to_dict() if not gov.empty else {}
    lines = [
        "# 泉州 2019/2020 I端升级版岗位/技能试点采集报告",
        "",
        "## 1. 本次运行信息",
        f"- run_id：{run_id}",
        "- 采集城市：泉州",
        "- 采集年份：2019、2020",
        "- 输出文件：",
    ]
    lines.extend([f"  - {file}" for file in output_files])
    lines.extend(
        [
            "",
            "## 2. 数据来源原则",
            "本轮优先使用政府、人社、公共就业、高校就业和政府产业公告来源。商业招聘平台没有作为主数据来源；政府项目公告只作为背景证据，不计入岗位数量。",
            "",
            "## 3. 来源覆盖情况",
            md_table(source_pages, ["year", "source_name", "source_type", "availability", "source_url"]),
            "",
            "## 4. 岗位候选结果",
            f"- 2019 岗位候选数量：{int(job_counts.get(2019, 0))}",
            f"- 2020 岗位候选数量：{int(job_counts.get(2020, 0))}",
            f"- 2020 强 AI 岗位候选数量：{int(strong_counts.get(2020, 0))}",
            "",
            md_table(jobs, ["year", "company_name", "job_title", "job_classification", "collection_status", "source_url"]) if not jobs.empty else "未形成岗位候选记录。",
            "",
            "## 5. 政府项目证据",
            f"- 2019 政府项目/产业证据数量：{int(gov_counts.get(2019, 0))}",
            f"- 2020 政府项目/产业证据数量：{int(gov_counts.get(2020, 0))}",
            "",
            md_table(gov, ["year", "source_name", "project_or_policy_name", "matched_keywords", "source_url"]) if not gov.empty else "未形成政府项目证据。",
            "",
            "## 6. 人工复核清单",
            md_table(manual, ["year", "review_item_type", "source_name", "source_url", "reason"]) if not manual.empty else "暂无人工复核项。",
            "",
            "## 7. 对当前 I_index=0 的影响判断",
            "- 2019：本轮未找到可直接纳入 C/B/X 岗位口径的强岗位证据，但找到政府科技/产业项目背景证据。它能提示产业数字化活动可能存在，但还不足以单独推翻 2019 年 I_index=0。",
            "- 2020：本轮找到泉州师范学院人工智能/物联网方向教师岗位候选，以及金控信息技术岗候选；同时存在工业互联网、智能制造、AI算法、物联网等政府项目证据。该结果对 2020 年 I_index=0 构成初步挑战，但仍需人工复核附件后才能进入 I_index_upgraded。",
            "- 政府项目公告是背景证据，不等同于企业岗位需求，不能冒充岗位数据。",
            "- 建议进入升级版 I_index 构造准备，但前提是人工复核岗位附件和来源可用性。",
            "",
            "## 8. 下一步建议",
            "- 继续人工下载和解析泉州市事业单位岗位信息表、泉州师范学院岗位需求表等附件。",
            "- 先不要重跑 CCD；应先完成岗位候选人工复核。",
            "- 复核通过后可构造 `I_index_upgraded_C/B/X`，再与 current I_index 做并列对比。",
            "- 建议扩展福州、厦门作为对照，但应在泉州试点规则稳定后进行。",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Quanzhou 2019/2020 official job-skill pilot evidence.")
    parser.add_argument("--run-id", help="Optional run_id override for reruns.")
    args = parser.parse_args()
    project_root = Path.cwd()
    run_id = args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    created_at = datetime.now().isoformat(timespec="seconds")

    input_files = [KEYWORDS_FILE, RULES_FILE, TEMPLATE_FILE, PANEL_TEMPLATE_FILE, INVENTORY_FILE, RECHECK_PLAN_FILE]
    warnings = []
    for input_file in input_files:
        ensure_not_legacy(input_file)
        if not (project_root / input_file).exists():
            warnings.append(f"缺少参考输入文件：{input_file}")

    keywords = parse_simple_keyword_yaml(project_root / KEYWORDS_FILE)

    source_pages = pd.DataFrame(build_source_pages())
    jobs = deduplicate_jobs(pd.DataFrame(build_job_candidates(keywords), columns=JOB_COLUMNS))
    attachments = pd.DataFrame(build_attachment_candidates())
    gov = pd.DataFrame(build_government_project_evidence())
    manual = pd.DataFrame(build_manual_review(source_pages.to_dict("records"), attachments.to_dict("records"), gov.to_dict("records")))
    notes = pd.DataFrame(
        [
            {
                "item": "collection_scope",
                "value": "泉州2019/2020官方来源小规模试点；不扩展全省；不使用商业招聘平台作为主来源。",
            },
            {
                "item": "data_quality",
                "value": "所有候选均为 pending_review；政府项目证据不计入岗位数量。",
            },
            {
                "item": "web_search_summary",
                "value": "已检索政府公共就业/人社、泉州政府门户、泉州市工信/科技相关公告、泉州高校/高校就业来源。",
            },
        ]
    )
    panel = build_panel(jobs, gov, attachments, manual)

    interim_dir = project_root / "data/interim/i_system_upgrade" / run_id
    panel_dir = project_root / "data/panel/i_system_upgrade" / run_id
    audit_dir = project_root / "data/audit/i_system_upgrade" / run_id
    tables_dir = project_root / "outputs/tables/i_system_upgrade" / run_id
    for directory in [interim_dir, panel_dir, audit_dir, tables_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    candidates_path = interim_dir / f"i_system_upgrade_{RUN_SCOPE}_official_job_candidates_{run_id}.xlsx"
    panel_path = panel_dir / f"i_system_upgrade_{RUN_SCOPE}_job_city_year_panel_{run_id}.xlsx"
    summary_path = tables_dir / f"i_system_upgrade_{RUN_SCOPE}_collection_summary_{run_id}.xlsx"
    report_path = audit_dir / f"i_system_upgrade_{RUN_SCOPE}_collection_report_{run_id}.md"
    manifest_path = audit_dir / f"i_system_upgrade_{RUN_SCOPE}_manifest_{run_id}.json"

    write_excel(
        candidates_path,
        {
            "01_job_candidates": jobs,
            "02_source_pages": source_pages,
            "03_attachment_candidates": attachments,
            "04_government_project_evidence": gov,
            "05_manual_review_required": manual,
            "06_collection_notes": notes,
        },
    )
    write_excel(panel_path, {"01_job_city_year_panel": panel})
    write_excel(
        summary_path,
        {
            "01_panel": panel,
            "02_job_candidates": jobs,
            "03_government_project_evidence": gov,
            "04_manual_review_required": manual,
        },
    )

    output_files = [
        candidates_path,
        panel_path,
        summary_path,
        report_path,
        manifest_path,
    ]
    write_report(
        report_path,
        run_id,
        [path.relative_to(project_root).as_posix() for path in output_files],
        source_pages,
        jobs,
        attachments,
        gov,
        manual,
        panel,
    )

    latest_files = [
        (
            candidates_path,
            project_root / "data/interim/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_official_job_candidates.xlsx",
        ),
        (
            panel_path,
            project_root / "data/panel/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_job_city_year_panel.xlsx",
        ),
        (
            report_path,
            project_root / "data/audit/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_collection_report.md",
        ),
    ]
    for src, dst in latest_files:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        output_files.append(dst)

    source_priority = [
        "government_public_employment_and_hr",
        "quanzhou_university_employment_sites",
        "government_industry_project_announcements",
        "commercial_recruitment_platforms_supplement_only",
    ]

    manifest = {
        "run_id": run_id,
        "created_at": created_at,
        "city": CITY,
        "years": YEARS,
        "source_priority": source_priority,
        "input_files": [path.as_posix() for path in input_files],
        "output_files": [path.relative_to(project_root).as_posix() for path in output_files],
        "source_pages_found_count": int(len(source_pages)),
        "job_candidates_count": int(len(jobs)),
        "job_candidates_2019_count": int((jobs["year"] == 2019).sum()),
        "job_candidates_2020_count": int((jobs["year"] == 2020).sum()),
        "government_project_evidence_count": int(len(gov)),
        "attachment_candidates_count": int(len(attachments)),
        "manual_review_required_count": int(len(manual)),
        "legacy_used_as_input": False,
        "commercial_sources_used_as_primary": False,
        "warnings": warnings,
        "next_step_recommendation": "先人工复核岗位附件和来源页面；建议构造 I_index_upgraded_C/B/X 的准备表，但不建议现在重跑 CCD。",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
