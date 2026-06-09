#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""泉州 2019/2020 民企/产业端数字化岗位采集与系统边界维护。

本脚本只结构化本轮人工检索到的官方、政府、高校就业与公开招聘证据。
它不读取 legacy 输出，不重算 CCD，不覆盖 latest experimental base panel。
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


CITY = "泉州"
YEARS = [2019, 2020]

BASE_PANEL = Path("data/panel/experimental_analysis/latest_experimental_analysis_base_panel_2019_2024.csv")
RULE_DOC = Path("docs/system_boundary/e_i_system_boundary_rules.md")
JOB_RULE_DOC = Path("docs/i_system_upgrade/job_skill_classification_rules.md")

INTERIM_ROOT = Path("data/interim/i_system_upgrade")
PANEL_ROOT = Path("data/panel/i_system_upgrade")
BOUNDARY_INTERIM_ROOT = Path("data/interim/system_boundary_audit")
BOUNDARY_AUDIT_ROOT = Path("data/audit/system_boundary_audit")
TABLE_ROOT = Path("outputs/tables/i_system_upgrade")


JOB_COLUMNS = [
    "record_id",
    "city",
    "year",
    "source_city",
    "source_name",
    "source_type",
    "official_level",
    "company_name",
    "employer_name",
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
    "employer_sector",
    "job_function",
    "system_mapping",
    "evidence_level",
    "include_in_I_job",
    "manual_review_priority",
    "source_url",
    "evidence_text",
    "collection_status",
    "reviewer_decision",
    "reviewer_notes",
]

PANEL_COLUMNS = [
    "city",
    "year",
    "total_scanned_job_records",
    "total_evidence_count",
    "total_job_count",
    "I_job_included_count",
    "I_job_pending_count",
    "E_extension_count",
    "G_public_sector_count",
    "F_financial_candidate_count",
    "I_tech_transfer_candidate_count",
    "I_project_evidence_count",
    "I_firm_evidence_count",
    "private_enterprise_job_count",
    "state_owned_industrial_job_count",
    "software_it_job_count",
    "ai_job_strong_count",
    "ai_tool_based_job_count",
    "digital_tech_job_count",
    "industrial_digital_job_count",
    "weak_only_review_count",
    "C_job_count",
    "B_job_count",
    "X_job_count",
    "ai_job_ratio",
    "broad_ai_digital_job_ratio",
    "avg_job_ai_score",
    "official_source_job_count",
    "university_source_job_count",
    "commercial_supplement_job_count",
    "manual_review_high_count",
    "data_status",
    "notes",
]

REVIEW_COLUMNS = [
    "source_file",
    "row_id",
    "record_id",
    "city",
    "year",
    "company_name",
    "employer_name",
    "job_title",
    "job_description",
    "source_url",
    "source_type",
    "official_level",
    "original_job_classification",
    "original_include_in_I_job",
    "employer_sector",
    "job_function",
    "evidence_level",
    "detected_boundary_type",
    "corrected_system_mapping",
    "corrected_include_in_I_job",
    "corrected_include_in_E_extension",
    "corrected_include_in_F_candidate",
    "corrected_include_in_G_public_sector",
    "corrected_include_in_project_evidence",
    "manual_review_priority",
    "correction_reason",
    "reviewer_decision",
    "reviewer_notes",
]


def semijoin(items: list[str]) -> str:
    return "、".join(dict.fromkeys([item for item in items if item]))


def classify_keywords(text: str) -> dict[str, Any]:
    strong = [k for k in ["人工智能", "AI", "机器学习", "大数据", "数据智能"] if k.lower() in text.lower()]
    tools = [k for k in ["TensorFlow", "PyTorch", "OpenCV"] if k.lower() in text.lower()]
    basic = [
        k
        for k in ["Java", "C++", "C#", ".NET", "SQL", "软件", "计算机", "数据", "大数据", "信息技术", "信息管理"]
        if k.lower() in text.lower()
    ]
    industrial = [
        k
        for k in ["智能制造", "工业互联网", "工业软件", "MES", "ERP", "PLC", "机器视觉", "智能工厂", "自动化", "数字化车间", "IC CAD"]
        if k.lower() in text.lower()
    ]
    weak = [k for k in ["科技", "智能", "信息", "网络", "数字", "平台", "系统", "互联网"] if k.lower() in text.lower()]

    if strong:
        classification = "ai_job_strong"
        score = 3.0
    elif tools:
        classification = "ai_job_tool_based"
        score = 2.5
    elif len(basic) >= 2:
        classification = "digital_tech_job"
        score = 1.5
    elif industrial:
        classification = "industrial_digital_job"
        score = 1.2
    elif weak:
        classification = "weak_only_review"
        score = 0.2
    else:
        classification = "non_ai_job"
        score = 0.0

    return {
        "matched_strong_ai_keywords": semijoin(strong),
        "matched_ai_tool_keywords": semijoin(tools),
        "matched_basic_digital_keywords": semijoin(basic),
        "matched_industrial_digital_keywords": semijoin(industrial),
        "matched_weak_keywords": semijoin(weak),
        "job_classification": classification,
        "job_ai_score": score,
    }


def job(
    record_id: str,
    year: int,
    source_name: str,
    source_type: str,
    official_level: str,
    company_name: str,
    job_title: str,
    job_description: str,
    posting_date: str,
    employer_sector: str,
    job_function: str,
    system_mapping: str,
    evidence_level: str,
    include_in_i_job: str | int,
    manual_review_priority: str,
    source_url: str,
    evidence_text: str,
    collection_status: str = "probable_job_candidate",
    reviewer_notes: str = "",
) -> dict[str, Any]:
    text = f"{company_name} {job_title} {job_description} {evidence_text}"
    row: dict[str, Any] = {
        "record_id": record_id,
        "city": CITY,
        "year": year,
        "source_city": CITY,
        "source_name": source_name,
        "source_type": source_type,
        "official_level": official_level,
        "company_name": company_name,
        "employer_name": company_name,
        "job_title": job_title,
        "job_description": job_description,
        "posting_date": posting_date,
        "employer_sector": employer_sector,
        "job_function": job_function,
        "system_mapping": system_mapping,
        "evidence_level": evidence_level,
        "include_in_I_job": include_in_i_job,
        "manual_review_priority": manual_review_priority,
        "source_url": source_url,
        "evidence_text": evidence_text,
        "collection_status": collection_status,
        "reviewer_decision": "pending_review",
        "reviewer_notes": reviewer_notes,
    }
    row.update(classify_keywords(text))
    return row


def source_page(
    year: int,
    source_name: str,
    source_type: str,
    official_level: str,
    source_url: str,
    availability: str,
    notes: str,
) -> dict[str, Any]:
    return {
        "city": CITY,
        "year": year,
        "source_name": source_name,
        "source_type": source_type,
        "official_level": official_level,
        "source_url": source_url,
        "availability": availability,
        "notes": notes,
    }


def evidence(
    record_id: str,
    year: int,
    evidence_type: str,
    source_name: str,
    source_type: str,
    official_level: str,
    source_url: str,
    evidence_text: str,
    system_mapping: str,
    evidence_level: str,
    manual_review_priority: str,
    notes: str,
) -> dict[str, Any]:
    return {
        "record_id": record_id,
        "city": CITY,
        "year": year,
        "evidence_type": evidence_type,
        "source_name": source_name,
        "source_type": source_type,
        "official_level": official_level,
        "source_url": source_url,
        "evidence_text": evidence_text,
        "system_mapping": system_mapping,
        "evidence_level": evidence_level,
        "include_in_I_job": 0,
        "manual_review_priority": manual_review_priority,
        "collection_status": evidence_type,
        "reviewer_decision": "pending_review",
        "notes": notes,
    }


def build_inputs() -> dict[str, list[dict[str, Any]]]:
    candidates = [
        job(
            "QZ2019-IJOB-001",
            2019,
            "泉州兰台信息科技股份公司招聘简章",
            "university_employment_page",
            "university_employment_verified",
            "泉州兰台信息科技股份公司",
            "Java软件技术员",
            "岗位表显示 Java 软件技术员，工作地点泉州软件园，需求人数10人。",
            "2019-05-14",
            "private_enterprise",
            "software_it",
            "I_industry",
            "B",
            1,
            "medium",
            "https://jy.mbu.cn/index.php?s=/home/article/detail/id/1411.html",
            "高校就业页面收录企业招聘简章，企业位于泉州软件园，岗位为 Java 软件技术员。",
            reviewer_notes="需人工复核高校就业网页原文和企业主体。",
        ),
        job(
            "QZ2019-IJOB-002",
            2019,
            "泉州兰台信息科技股份公司招聘简章",
            "university_employment_page",
            "university_employment_verified",
            "泉州兰台信息科技股份公司",
            "C++软件技术员",
            "岗位表显示 C++ 软件技术员，工作地点泉州软件园，需求人数5人。",
            "2019-05-14",
            "private_enterprise",
            "software_it",
            "I_industry",
            "B",
            1,
            "medium",
            "https://jy.mbu.cn/index.php?s=/home/article/detail/id/1411.html",
            "高校就业页面收录企业招聘简章，岗位为 C++ 软件技术员。",
            reviewer_notes="需人工复核高校就业网页原文和岗位人数。",
        ),
        job(
            "QZ2019-IJOB-003",
            2019,
            "泉州兰台信息科技股份公司招聘简章",
            "university_employment_page",
            "university_employment_verified",
            "泉州兰台信息科技股份公司",
            "前端页面设计",
            "岗位表显示前端页面设计岗位，工作地点泉州软件园，需求人数5人。",
            "2019-05-14",
            "private_enterprise",
            "software_it",
            "I_industry",
            "B",
            1,
            "medium",
            "https://jy.mbu.cn/index.php?s=/home/article/detail/id/1411.html",
            "高校就业页面收录企业招聘简章，岗位为前端页面设计。",
            reviewer_notes="前端岗位可作为软件信息服务岗位候选，但需人工确认原网页。",
        ),
        job(
            "QZ2019-IJOB-004",
            2019,
            "泉州市八家市属国有企业2019年度招聘人员公告",
            "official_state_owned_enterprise_recruitment",
            "municipal_sasac_official",
            "泉州市搏浪信息科技有限公司",
            "产品经理",
            "要求计算机科学与技术、计算机软件、计算机网络技术或计算机信息管理等专业，具备 IT 软件产品策划、需求分析、设计和项目管理能力。",
            "2019-04-08",
            "state_owned_industrial",
            "software_it",
            "I_industry",
            "A",
            1,
            "medium",
            "https://gzw.quanzhou.gov.cn/gzdt/tzgg/201904/t20190408_1492150.htm",
            "泉州市国资委公告列示泉州市搏浪信息科技有限公司产品经理岗位，专业和能力要求指向 IT 软件产品。",
            collection_status="confirmed_job_candidate",
            reviewer_notes="市属信息科技企业岗位，非金融、非高校、非政府机关岗位。",
        ),
        job(
            "QZ2019-IJOB-005",
            2019,
            "泉州三安半导体科技有限公司招聘简章",
            "university_employment_archive",
            "university_verified_repost",
            "泉州三安半导体科技有限公司",
            "软件工程师",
            "计算机专业，掌握 .NET/C# 开发技巧和 Oracle SQL 应用，负责 MES 系统运行及二次开发，工作地点泉州。",
            "2018-10-27",
            "private_enterprise",
            "industrial_digitalization",
            "I_industry",
            "B",
            1,
            "medium",
            "https://archiverm.yingjiesheng.com/job-003-999-096.html",
            "转载页面说明信息由山西大学审核并发布；岗位表中软件工程师负责 MES 系统运行及二次开发。",
            reviewer_notes="发布日期为2018年末、面向2019招聘，作为2019候选需人工确认年份口径。",
        ),
        job(
            "QZ2020-IJOB-001",
            2020,
            "福建省晋华集成电路有限公司招聘简章",
            "university_employment_page",
            "university_employment_verified",
            "福建省晋华集成电路有限公司",
            "软件工程师",
            "软件工程、计算机科学与技术相关，岗位需求包含 C/C++/C#/Java/.NET 方向，工作地点泉州晋江。",
            "2020-03-09",
            "state_owned_industrial",
            "software_it",
            "I_industry",
            "A",
            1,
            "medium",
            "https://apd.wh.sdu.edu.cn/info/1567/4380.htm",
            "高校就业页面显示福建晋华位于泉州晋江，招聘软件工程师。",
            collection_status="confirmed_job_candidate",
            reviewer_notes="产业企业 IT/软件岗位，可进入 I_job 候选。",
        ),
        job(
            "QZ2020-IJOB-002",
            2020,
            "福建省晋华集成电路有限公司招聘简章",
            "university_employment_page",
            "university_employment_verified",
            "福建省晋华集成电路有限公司",
            "大数据工程师",
            "专业要求为信息技术、计算机软件、数学等，工作地点泉州晋江。",
            "2020-03-09",
            "state_owned_industrial",
            "data_ai",
            "I_industry",
            "A",
            1,
            "medium",
            "https://career.hebut.edu.cn/home/correcruit/content/id/25973.html",
            "高校就业页面列示大数据工程师岗位，企业地址为福建省泉州市晋江市集成电路科学园。",
            collection_status="confirmed_job_candidate",
            reviewer_notes="产业企业数据岗位，可进入 I_job 候选。",
        ),
        job(
            "QZ2020-IJOB-003",
            2020,
            "晋华集成电路2020春季校园招聘",
            "commercial_campus_supplement",
            "commercial_supplement_needs_original_confirmation",
            "福建省晋华集成电路有限公司",
            "IC CAD工程师",
            "岗位名称为 IC CAD 工程师，专业涉及集成电路、微电子、物理、电子信息科学、计算机等。",
            "2020-03-09",
            "state_owned_industrial",
            "engineering_development",
            "exclude_or_review",
            "G",
            "pending",
            "medium",
            "https://campus.51job.com/jhicc/job.html",
            "晋华集成电路2020春季校园招聘岗位页列示 IC CAD 工程师、软件工程师、大数据工程师等岗位。",
            collection_status="supplement_candidate",
            reviewer_notes="51job 为商业招聘平台承载页，本轮不作为 I_job 主数据源；需找到企业或高校官方来源后再纳入。",
        ),
        job(
            "QZ2020-E-001",
            2020,
            "2020年泉州师范学院公开招聘博士研究生学历学位教师公告",
            "official_public_institution_recruitment",
            "municipal_hr_official",
            "泉州师范学院",
            "教师A24（计算机/软件工程/人工智能/物联网工程方向）",
            "岗位需求表线索包含计算机应用技术、软件工程、人工智能、物联网工程、自动化控制等方向。",
            "2020-04-30",
            "university",
            "teaching",
            "E_education_extension",
            "F",
            0,
            "high",
            "https://rsj.quanzhou.gov.cn/zwgk/zxdt/tzgg/202004/t20200430_2234402.htm",
            "高校自身教师招聘属于教育系统延伸，即使命中 AI/物联网关键词也不得计入 I_job。",
            reviewer_notes="边界排除：高校教师岗。",
        ),
        job(
            "QZ2020-F-001",
            2020,
            "泉州市金控集团及权属企业公开招聘公告",
            "official_state_owned_enterprise_recruitment",
            "municipal_government_portal",
            "泉州金控集团及权属企业",
            "信息技术岗",
            "要求数学、电子信息、计算机科学与技术类专业，掌握计算机软硬件技术基础和系统运行知识。",
            "2020-06-02",
            "financial",
            "software_it",
            "F_financial_candidate",
            "F",
            0,
            "low",
            "https://www.quanzhou.gov.cn/zfb/xxgk/zfxxgkzl/rsxx/zkzp/202006/t20200602_2303269.htm",
            "泉州金控信息技术岗属于金融端候选，不进入当前 E-I 主模型。",
            reviewer_notes="边界排除：金融机构信息技术岗。",
        ),
        job(
            "QZ2020-G-001",
            2020,
            "2020年泉州市事业单位公开招聘编制内工作人员岗位信息表",
            "official_hr_recruitment_attachment",
            "municipal_hr_official",
            "泉州市事业单位",
            "信息化/计算机相关岗位附件线索",
            "官方人社页面提供事业单位招聘岗位信息表压缩包，需人工筛选计算机、软件、信息、安全相关岗位。",
            "2020-08-10",
            "public_institution",
            "public_administration",
            "G_public_sector",
            "C",
            0,
            "medium",
            "https://rsj.quanzhou.gov.cn/zwgk/zxdt/syzk/202008/t20200810_2403095.htm",
            "事业单位内部岗位不得进入 I_job，附件仅作公共部门数字需求复核线索。",
            collection_status="attachment_manual_required",
            reviewer_notes="边界排除：普通事业单位/公共部门岗位。",
        ),
    ]

    sources = [
        source_page(2019, "泉州市国资委八家市属国企赴福州大学招聘公告", "official_state_owned_enterprise_recruitment", "municipal_sasac_official", "https://gzw.quanzhou.gov.cn/gzdt/tzgg/201904/t20190408_1492150.htm", "available_by_search", "检索到市属信息科技企业岗位，可人工打开复核。"),
        source_page(2019, "泉州兰台信息科技股份公司招聘简章", "university_employment_page", "university_employment_verified", "https://jy.mbu.cn/index.php?s=/home/article/detail/id/1411.html", "available_by_search", "高校就业页面收录泉州软件园企业岗位。"),
        source_page(2019, "泉州三安半导体科技有限公司2019招聘", "university_employment_archive", "university_verified_repost", "https://archiverm.yingjiesheng.com/job-003-999-096.html", "available", "转载页说明信息由山西大学审核并发布，需人工核对原发布页。"),
        source_page(2020, "福建省晋华集成电路有限公司招聘", "university_employment_page", "university_employment_verified", "https://apd.wh.sdu.edu.cn/info/1567/4380.htm", "available", "高校就业页面列示晋华 2020 招聘与岗位。"),
        source_page(2020, "晋华集成电路2020春季校园招聘岗位页", "commercial_campus_supplement", "commercial_supplement_needs_original_confirmation", "https://campus.51job.com/jhicc/job.html", "available_by_search", "商业平台校招承载页仅作补充线索，不进入主数据源。"),
        source_page(2020, "泉州市金控集团及权属企业公开招聘公告", "official_state_owned_enterprise_recruitment", "municipal_government_portal", "https://www.quanzhou.gov.cn/zfb/xxgk/zfxxgkzl/rsxx/zkzp/202006/t20200602_2303269.htm", "available", "金融端岗位，不进入当前 I_job。"),
        source_page(2020, "2020年泉州师范学院公开招聘博士研究生学历学位教师公告", "official_public_institution_recruitment", "municipal_hr_official", "https://rsj.quanzhou.gov.cn/zwgk/zxdt/tzgg/202004/t20200430_2234402.htm", "available_by_search", "高校教师岗，不进入 I_job。"),
        source_page(2020, "2020年泉州市事业单位公开招聘编制内工作人员岗位信息表", "official_hr_recruitment_attachment", "municipal_hr_official", "https://rsj.quanzhou.gov.cn/zwgk/zxdt/syzk/202008/t20200810_2403095.htm", "attachment_manual_required", "事业单位附件需人工复核，但不计入 I_job。"),
        source_page(2020, "借力5G+智能制造 创新产业数字发展", "government_industry_project", "municipal_industry_official", "https://gxj.quanzhou.gov.cn/zwgk/gzdt/202011/t20201124_2463941.htm", "available", "工信局项目证据，不计入岗位数量。"),
        source_page(2020, "12个高新产业项目签约落地泉州市软件与工业设计基地", "government_industry_project", "district_government_official", "https://www.qzfz.gov.cn/zwgk/xwzx/fzxw/202012/t20201211_2476018.htm", "available", "项目/企业主体证据，不伪装为岗位。"),
    ]

    project_evidence = [
        evidence(
            "QZ2020-PROJ-001",
            2020,
            "government_project_evidence",
            "借力5G+智能制造 创新产业数字发展",
            "government_industry_project",
            "municipal_industry_official",
            "https://gxj.quanzhou.gov.cn/zwgk/gzdt/202011/t20201124_2463941.htm",
            "泉州市工信局页面提到 2019 年华为、中国电信、九牧 5G 智慧制造示范产业园项目签约，以及 2020 年智能制造相关活动。",
            "I_project_evidence_only",
            "D",
            "medium",
            "项目证据只能说明产业数字化活动存在，不计入岗位数。",
        ),
        evidence(
            "QZ2020-PROJ-002",
            2020,
            "government_project_evidence",
            "12个高新产业项目签约落地泉州市软件与工业设计基地",
            "government_industry_project",
            "district_government_official",
            "https://www.qzfz.gov.cn/zwgk/xwzx/fzxw/202012/t20201211_2476018.htm",
            "丰泽区政府页面列示机器人产业园、智能制造科技成果转移转化中心、5G、工业互联网等项目。",
            "I_project_evidence_only",
            "D",
            "high",
            "含技术转化中心和研究院项目，需人工复核是否后续形成 I_tech_transfer 岗位，但本轮不计入岗位数。",
        ),
        evidence(
            "QZ2020-PROJ-003",
            2020,
            "government_project_evidence",
            "泉州市工业和信息化局关于2020年工作总结及2021年工作计划",
            "government_industry_project",
            "municipal_industry_official",
            "https://gxj.quanzhou.gov.cn/zwgk/ghjh/202102/t20210204_2508845.htm",
            "工信局总结提到数字化车间、智能工厂、工业互联网平台、智能制造试点示范企业等。",
            "I_project_evidence_only",
            "D",
            "medium",
            "年度总结为背景/项目证据，不是岗位记录。",
        ),
    ]

    firm_evidence = [
        evidence(
            "QZ2020-FIRM-001",
            2020,
            "firm_evidence",
            "泉州市产教融合公共服务平台企业页",
            "public_industry_education_platform",
            "public_service_platform",
            "https://www.qzcjrh.com/industry_edu_integ/appsystem/industry/company?industry_id=4childtag_id%3D12&is_mobile=1&page=2",
            "平台列示兰台信息、海邻网络、万维智能、劲氏电子商务等软件/信息技术企业线索。",
            "I_firm_evidence_only",
            "E",
            "medium",
            "企业主体证据不能伪装成岗位；可作为后续企业端名单复核来源。",
        ),
        evidence(
            "QZ2020-FIRM-002",
            2020,
            "firm_evidence",
            "12个高新产业项目落地泉州软件园",
            "government_industry_project",
            "official_or_government_repost",
            "https://tradeinservices.mofcom.gov.cn/article/lingyu/rjckou/202012/112132.html",
            "商务部服务贸易平台转载东南早报报道，提到泉州软件园入驻企业、高新技术企业和软件工业设计产业集聚。",
            "I_firm_evidence_only",
            "E",
            "low",
            "作为企业/园区主体背景证据，不计入岗位数。",
        ),
    ]

    notes = [
        {
            "item": "采集原则",
            "note": "本轮只整理官方、政府、高校就业与公开招聘线索；商业招聘平台不作为主来源。",
        },
        {
            "item": "边界原则",
            "note": "高校、政府/事业单位、金融岗位均不计入 I_job；项目公告和企业名单不伪装成岗位。",
        },
        {
            "item": "年份原则",
            "note": "2018 年末面向 2019 届招聘的泉州企业岗位暂列 2019 候选，并保留人工复核备注。",
        },
    ]

    return {
        "job_candidates": candidates,
        "source_pages": sources,
        "project_evidence": project_evidence,
        "firm_evidence": firm_evidence,
        "collection_notes": notes,
    }


def make_panel(job_df: pd.DataFrame, project_df: pd.DataFrame, firm_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for year in YEARS:
        j = job_df[job_df["year"] == year].copy()
        p = project_df[project_df["year"] == year].copy()
        f = firm_df[firm_df["year"] == year].copy()
        i_job = j[j["include_in_I_job"].astype(str) == "1"]
        pending = j[j["include_in_I_job"].astype(str) == "pending"]
        c_jobs = i_job[i_job["job_classification"].isin(["ai_job_strong", "ai_job_tool_based"])]
        b_jobs = i_job[i_job["job_classification"].isin(["ai_job_strong", "ai_job_tool_based", "digital_tech_job"])]
        x_jobs = i_job[i_job["job_classification"].isin(["ai_job_strong", "ai_job_tool_based", "digital_tech_job", "industrial_digital_job"])]
        total_jobs = len(j)
        included_count = len(i_job)
        row = {
            "city": CITY,
            "year": year,
            "total_scanned_job_records": total_jobs,
            "total_evidence_count": total_jobs + len(p) + len(f),
            "total_job_count": total_jobs,
            "I_job_included_count": included_count,
            "I_job_pending_count": len(pending),
            "E_extension_count": int(j["system_mapping"].isin(["E_education_extension", "E_research_extension"]).sum()),
            "G_public_sector_count": int(j["system_mapping"].eq("G_public_sector").sum()),
            "F_financial_candidate_count": int(j["system_mapping"].eq("F_financial_candidate").sum()),
            "I_tech_transfer_candidate_count": int(j["system_mapping"].eq("I_tech_transfer_candidate").sum()),
            "I_project_evidence_count": len(p),
            "I_firm_evidence_count": len(f),
            "private_enterprise_job_count": int(i_job["employer_sector"].eq("private_enterprise").sum()),
            "state_owned_industrial_job_count": int(i_job["employer_sector"].eq("state_owned_industrial").sum()),
            "software_it_job_count": int(i_job["job_function"].eq("software_it").sum()),
            "ai_job_strong_count": int(i_job["job_classification"].eq("ai_job_strong").sum()),
            "ai_tool_based_job_count": int(i_job["job_classification"].eq("ai_job_tool_based").sum()),
            "digital_tech_job_count": int(i_job["job_classification"].eq("digital_tech_job").sum()),
            "industrial_digital_job_count": int(i_job["job_classification"].eq("industrial_digital_job").sum()),
            "weak_only_review_count": int(j["job_classification"].eq("weak_only_review").sum()),
            "C_job_count": len(c_jobs),
            "B_job_count": len(b_jobs),
            "X_job_count": len(x_jobs),
            "ai_job_ratio": round(len(c_jobs) / included_count, 4) if included_count else 0,
            "broad_ai_digital_job_ratio": round(len(x_jobs) / included_count, 4) if included_count else 0,
            "avg_job_ai_score": round(float(i_job["job_ai_score"].mean()), 4) if included_count else 0,
            "official_source_job_count": int(i_job["source_type"].str.contains("official", na=False).sum()),
            "university_source_job_count": int(i_job["source_type"].str.contains("university", na=False).sum()),
            "commercial_supplement_job_count": int(j["source_type"].str.contains("commercial", na=False).sum()),
            "manual_review_high_count": int(j["manual_review_priority"].eq("high").sum() + p["manual_review_priority"].eq("high").sum() + f["manual_review_priority"].eq("high").sum()),
            "data_status": "pilot_evidence_only",
            "notes": "本轮不更新 CCD；岗位候选均需人工复核后才可用于 I_index_upgraded。",
        }
        rows.append(row)
    return pd.DataFrame(rows, columns=PANEL_COLUMNS)


def boundary_type(row: pd.Series) -> str:
    mapping = str(row.get("system_mapping", ""))
    if mapping == "I_industry":
        return "enterprise_industry_job"
    if mapping == "I_tech_transfer_candidate":
        return "tech_transfer_candidate"
    if mapping.startswith("E_"):
        return "university_or_education_extension"
    if mapping == "G_public_sector":
        return "government_or_public_institution"
    if mapping == "F_financial_candidate":
        return "financial_candidate"
    if mapping == "I_project_evidence_only":
        return "project_evidence_only"
    if mapping == "I_firm_evidence_only":
        return "firm_evidence_only"
    return "manual_review_required"


def make_review(job_df: pd.DataFrame, project_df: pd.DataFrame, firm_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    source_file = "本轮结构化采集表"
    for idx, row in job_df.iterrows():
        mapping = str(row["system_mapping"])
        include_i = str(row["include_in_I_job"]) == "1"
        rows.append(
            {
                "source_file": source_file,
                "row_id": f"job_candidates:{idx + 2}",
                "record_id": row["record_id"],
                "city": row["city"],
                "year": row["year"],
                "company_name": row["company_name"],
                "employer_name": row["employer_name"],
                "job_title": row["job_title"],
                "job_description": row["job_description"],
                "source_url": row["source_url"],
                "source_type": row["source_type"],
                "official_level": row["official_level"],
                "original_job_classification": row["job_classification"],
                "original_include_in_I_job": row["include_in_I_job"],
                "employer_sector": row["employer_sector"],
                "job_function": row["job_function"],
                "evidence_level": row["evidence_level"],
                "detected_boundary_type": boundary_type(row),
                "corrected_system_mapping": mapping,
                "corrected_include_in_I_job": include_i,
                "corrected_include_in_E_extension": mapping.startswith("E_"),
                "corrected_include_in_F_candidate": mapping == "F_financial_candidate",
                "corrected_include_in_G_public_sector": mapping == "G_public_sector",
                "corrected_include_in_project_evidence": False,
                "manual_review_priority": row["manual_review_priority"],
                "correction_reason": correction_reason(mapping),
                "reviewer_decision": "pending_review",
                "reviewer_notes": row.get("reviewer_notes", ""),
            }
        )

    for df, prefix in [(project_df, "project_evidence"), (firm_df, "firm_evidence")]:
        for idx, row in df.iterrows():
            mapping = str(row["system_mapping"])
            rows.append(
                {
                    "source_file": source_file,
                    "row_id": f"{prefix}:{idx + 2}",
                    "record_id": row["record_id"],
                    "city": row["city"],
                    "year": row["year"],
                    "company_name": "",
                    "employer_name": row["source_name"],
                    "job_title": "",
                    "job_description": row["evidence_text"],
                    "source_url": row["source_url"],
                    "source_type": row["source_type"],
                    "official_level": row["official_level"],
                    "original_job_classification": "",
                    "original_include_in_I_job": 0,
                    "employer_sector": "government" if mapping == "I_project_evidence_only" else "enterprise_or_platform",
                    "job_function": "project_evidence" if mapping == "I_project_evidence_only" else "firm_evidence",
                    "evidence_level": row["evidence_level"],
                    "detected_boundary_type": boundary_type(row),
                    "corrected_system_mapping": mapping,
                    "corrected_include_in_I_job": False,
                    "corrected_include_in_E_extension": False,
                    "corrected_include_in_F_candidate": False,
                    "corrected_include_in_G_public_sector": False,
                    "corrected_include_in_project_evidence": mapping == "I_project_evidence_only",
                    "manual_review_priority": row["manual_review_priority"],
                    "correction_reason": correction_reason(mapping),
                    "reviewer_decision": "pending_review",
                    "reviewer_notes": row["notes"],
                }
            )
    return pd.DataFrame(rows, columns=REVIEW_COLUMNS)


def correction_reason(mapping: str) -> str:
    return {
        "I_industry": "企业产业端岗位，具备主体、岗位、年份、城市和来源，进入 I_job 候选。",
        "I_tech_transfer_candidate": "产业技术转化候选，需人工确认服务企业研发/工程化/产业化后才可进入 I_job。",
        "E_education_extension": "高校自身岗位属于教育系统延伸，不进入 I_job。",
        "E_research_extension": "高校或学术科研岗位属于教育/科研延伸，不进入 I_job。",
        "G_public_sector": "政府或普通事业单位岗位属于公共部门数字需求，不进入 I_job。",
        "F_financial_candidate": "金融机构信息技术岗留作 F 端候选，不进入当前 E-I 主模型。",
        "I_project_evidence_only": "项目公告只能作为产业项目证据，不计入岗位数量。",
        "I_firm_evidence_only": "企业名单或主体证据不能伪装成岗位，只作企业端复核线索。",
    }.get(mapping, "边界或证据不足，需人工复核。")


def mapping_template(review_df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "record_id": review_df["record_id"],
            "source_file": review_df["source_file"],
            "city": review_df["city"],
            "year": review_df["year"],
            "original_name": review_df["company_name"].fillna("").where(review_df["company_name"].fillna("") != "", review_df["employer_name"].fillna("")),
            "original_type": review_df["source_type"],
            "original_classification": review_df["original_job_classification"],
            "employer_sector": review_df["employer_sector"],
            "job_function": review_df["job_function"],
            "evidence_level": review_df["evidence_level"],
            "corrected_system_mapping": review_df["corrected_system_mapping"],
            "corrected_include_in_I_job": review_df["corrected_include_in_I_job"],
            "corrected_include_in_E_extension": review_df["corrected_include_in_E_extension"],
            "corrected_include_in_F_candidate": review_df["corrected_include_in_F_candidate"],
            "corrected_include_in_G_public_sector": review_df["corrected_include_in_G_public_sector"],
            "corrected_include_in_project_evidence": review_df["corrected_include_in_project_evidence"],
            "manual_review_priority": review_df["manual_review_priority"],
            "correction_reason": review_df["correction_reason"],
            "manual_review_status": "pending",
            "reviewer_notes": review_df["reviewer_notes"],
        }
    )


def write_excel(path: Path, sheets: dict[str, pd.DataFrame]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            safe_name = sheet_name[:31]
            df.to_excel(writer, sheet_name=safe_name, index=False)


def make_report(run_id: str, counts: dict[str, int], output_files: list[str], searched_sources: pd.DataFrame) -> str:
    source_lines = "\n".join(
        f"- {row.source_name}：{row.source_type}，{row.source_url}"
        for row in searched_sources.itertuples(index=False)
    )
    return f"""# 泉州民企数字化岗位采集与 I 端系统边界审计报告

## 1. 本次运行信息

- run_id：{run_id}
- 采集城市：泉州
- 采集年份：2019、2020
- latest experimental base panel：{BASE_PANEL}
- 本轮不重算 CCD，不覆盖 latest experimental base panel，不使用 legacy 文件。

## 2. 本轮收集的来源

{source_lines}

## 3. 岗位数量和类型

- 总扫描岗位记录：{counts["total_job_records"]}
- I_job 纳入数量：{counts["i_job_included"]}
- E_extension 数量：{counts["e_extension"]}
- G_public_sector 数量：{counts["g_public"]}
- F_financial_candidate 数量：{counts["f_financial"]}
- I_tech_transfer_candidate 数量：{counts["tech_transfer"]}
- 项目证据数量：{counts["project_evidence"]}
- 企业主体证据数量：{counts["firm_evidence"]}
- 高优先级人工复核数量：{counts["high_priority"]}

## 4. 系统边界修正说明

本轮继续执行 v2 边界规则：先识别 `employer_sector`，再判断 `job_function`，最后确定 `system_mapping`。高校教师/科研/实验员岗位转入 E 端延伸，政府机关和普通事业单位信息化岗位转入 G 公共部门，金控、银行、基金、担保等金融岗位转入 F 端候选。项目公告、科技计划、智能制造示范、企业名单和园区企业名录均不得伪装成岗位。

产业端企业岗位只有在具备企业主体、岗位名称、年份、城市归属和 source_url 时，才进入 I_job 候选。本轮新增可进入 I_job 候选的记录主要来自泉州兰台信息科技、泉州市搏浪信息科技、泉州三安半导体、福建省晋华集成电路等企业岗位线索。

## 5. 人工复核队列

高优先级复核集中在两类记录：一是高校教师/科研相关记录，防止误计入 I_job；二是政府项目中涉及技术转化中心、研究院、工业互联网或智能制造平台的记录，后续需要确认是否存在明确岗位。当前未发现可直接标记为 `I_tech_transfer_candidate` 的研究员/工程化岗位记录。

## 6. 对泉州 2019/2020 I_index 的潜在影响

本轮找到若干企业产业端数字化岗位候选，说明泉州 2019/2020 I 端完全为 0 的口径可能偏保守，尤其是 2019 年泉州软件园企业岗位、半导体企业 MES/软件岗位，以及 2020 年晋华集成电路软件/大数据岗位。但这些记录仍需人工复核 source_url、原始附件和年份口径后，才能用于构造 `I_index_upgraded_C/B/X`。

项目证据能够支持泉州存在智能制造、5G+工业互联网、软件园高新项目活动，但不能计入岗位数量，也不能单独推翻 I_index=0。

## 7. 是否需要重算 CCD

本轮不需要重算 CCD。当前 CCD 主结果仍基于企业存量和专利等 experimental I 端输入，岗位/技能数据尚未正式进入主模型。只有在人工复核完成并构造升级版 I_index 后，才建议另行运行升级版 CCD 对比。

## 8. 下一步建议

1. 优先人工打开并保存兰台信息、三安半导体、晋华集成电路、搏浪信息科技岗位原始页面或附件。
2. 对政府项目中的技术转化中心、研究院、智能制造平台继续查找是否有明确企业服务型岗位。
3. 暂不重跑当前 experimental CCD。
4. 人工复核通过后，构造 `I_index_upgraded_C/B/X`，再做升级版 CCD 对比。

## 9. 输出文件

{chr(10).join(f"- {path}" for path in output_files)}
"""


def main() -> None:
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    warnings: list[str] = []
    for required in [BASE_PANEL, RULE_DOC, JOB_RULE_DOC]:
        if not required.exists():
            warnings.append(f"前置文件缺失：{required}")

    interim_dir = INTERIM_ROOT / run_id
    panel_dir = PANEL_ROOT / run_id
    boundary_interim_dir = BOUNDARY_INTERIM_ROOT / run_id
    audit_dir = BOUNDARY_AUDIT_ROOT / run_id
    table_dir = TABLE_ROOT / run_id
    for directory in [interim_dir, panel_dir, boundary_interim_dir, audit_dir, table_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    data = build_inputs()
    job_df = pd.DataFrame(data["job_candidates"], columns=JOB_COLUMNS)
    source_df = pd.DataFrame(data["source_pages"])
    project_df = pd.DataFrame(data["project_evidence"])
    firm_df = pd.DataFrame(data["firm_evidence"])
    notes_df = pd.DataFrame(data["collection_notes"])

    panel_df = make_panel(job_df, project_df, firm_df)
    review_df = make_review(job_df, project_df, firm_df)
    mapping_df = mapping_template(review_df)
    manual_df = review_df[review_df["manual_review_priority"].isin(["high", "medium"])].copy()

    counts = {
        "total_job_records": len(job_df),
        "i_job_included": int((job_df["include_in_I_job"].astype(str) == "1").sum()),
        "e_extension": int(job_df["system_mapping"].isin(["E_education_extension", "E_research_extension"]).sum()),
        "g_public": int(job_df["system_mapping"].eq("G_public_sector").sum()),
        "f_financial": int(job_df["system_mapping"].eq("F_financial_candidate").sum()),
        "tech_transfer": int(job_df["system_mapping"].eq("I_tech_transfer_candidate").sum()),
        "project_evidence": len(project_df),
        "firm_evidence": len(firm_df),
        "high_priority": int((review_df["manual_review_priority"] == "high").sum()),
    }

    candidate_path = interim_dir / f"i_system_upgrade_quanzhou_2019_2020_private_digital_official_job_candidates_{run_id}.xlsx"
    candidate_latest = INTERIM_ROOT / "latest_i_system_upgrade_quanzhou_2019_2020_private_digital_official_job_candidates.xlsx"
    panel_path = panel_dir / f"i_system_upgrade_quanzhou_2019_2020_private_digital_job_city_year_panel_{run_id}.xlsx"
    panel_latest = PANEL_ROOT / "latest_i_system_upgrade_quanzhou_2019_2020_private_digital_job_city_year_panel.xlsx"
    review_path = boundary_interim_dir / f"system_boundary_audit_job_record_review_{run_id}.xlsx"
    review_latest = BOUNDARY_INTERIM_ROOT / "latest_system_boundary_audit_job_record_review.xlsx"
    mapping_path = boundary_interim_dir / f"system_boundary_corrected_mapping_template_{run_id}.xlsx"
    mapping_latest = BOUNDARY_INTERIM_ROOT / "latest_system_boundary_corrected_mapping_template.xlsx"
    report_path = audit_dir / f"system_boundary_audit_report_{run_id}.md"
    report_latest = BOUNDARY_AUDIT_ROOT / "latest_system_boundary_audit_report.md"
    manifest_path = audit_dir / f"system_boundary_audit_manifest_{run_id}.json"
    table_candidate_path = table_dir / f"i_system_upgrade_quanzhou_2019_2020_official_job_candidates_{run_id}.xlsx"
    table_panel_path = table_dir / f"i_system_upgrade_quanzhou_2019_2020_job_city_year_panel_{run_id}.xlsx"

    candidate_sheets = {
        "01_job_candidates": job_df,
        "02_source_pages": source_df,
        "03_government_project_evidence": project_df,
        "04_firm_evidence": firm_df,
        "05_manual_review_required": manual_df,
        "06_collection_notes": notes_df,
    }
    write_excel(candidate_path, candidate_sheets)
    shutil.copy2(candidate_path, candidate_latest)
    shutil.copy2(candidate_path, table_candidate_path)

    write_excel(panel_path, {"01_job_city_year_panel": panel_df})
    shutil.copy2(panel_path, panel_latest)
    shutil.copy2(panel_path, table_panel_path)

    review_sheets = {
        "01_all_records": review_df,
        "02_I_industry": review_df[review_df["corrected_system_mapping"].eq("I_industry")],
        "03_E_extension": review_df[review_df["corrected_system_mapping"].str.startswith("E_", na=False)],
        "04_G_public_sector": review_df[review_df["corrected_system_mapping"].eq("G_public_sector")],
        "05_F_financial_candidate": review_df[review_df["corrected_system_mapping"].eq("F_financial_candidate")],
        "06_I_project_evidence_only": review_df[review_df["corrected_system_mapping"].eq("I_project_evidence_only")],
        "07_I_firm_evidence_only": review_df[review_df["corrected_system_mapping"].eq("I_firm_evidence_only")],
        "08_manual_review_queue": manual_df,
    }
    write_excel(review_path, review_sheets)
    shutil.copy2(review_path, review_latest)

    write_excel(mapping_path, {"01_corrected_mapping": mapping_df})
    shutil.copy2(mapping_path, mapping_latest)

    output_files = [
        str(candidate_path),
        str(candidate_latest),
        str(panel_path),
        str(panel_latest),
        str(review_path),
        str(review_latest),
        str(mapping_path),
        str(mapping_latest),
        str(report_path),
        str(report_latest),
        str(manifest_path),
        str(table_candidate_path),
        str(table_panel_path),
    ]
    report = make_report(run_id, counts, output_files, source_df)
    report_path.write_text(report, encoding="utf-8")
    shutil.copy2(report_path, report_latest)

    manifest = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "city": CITY,
        "years": YEARS,
        "latest_experimental_base_panel_exists": BASE_PANEL.exists(),
        "legacy_used_as_input": False,
        "ccd_recomputed": False,
        "commercial_sources_used_as_primary": False,
        "counts": counts,
        "output_files": output_files,
        "warnings": warnings,
        "next_step_recommendation": "先人工复核 I_job 候选 source_url 和附件，再构造 I_index_upgraded_C/B/X；本轮不建议立即重跑 CCD。",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"run_id": run_id, "counts": counts, "output_files": output_files}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
