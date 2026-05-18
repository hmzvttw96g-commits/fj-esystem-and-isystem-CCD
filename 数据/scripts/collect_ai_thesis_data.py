"""
Collect public-source evidence for the AI finance-education-industry thesis.

The script is intentionally conservative:
- It searches public web sources, preferably through Tavily when TAVILY_API_KEY is set.
- It downloads only publicly reachable pages returned by search.
- It extracts candidate tables and numeric snippets, then writes a verification queue.
- It does not bypass logins, CAPTCHAs, paywalls, or database access restrictions.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from charset_normalizer import from_bytes


THESIS_ROOT = Path(r"C:\金融专硕\论文\硕士毕业论文_Obsidian_MD统一整理_20260512")
DATA_ROOT = THESIS_ROOT / "数据"

NARROW_PROVINCES = ["福建", "广东", "浙江", "江苏", "上海"]
CORE_PROVINCES = ["福建", "广东", "浙江", "江苏", "上海", "北京", "安徽", "山东", "湖北", "四川"]

AI_CORE_TERMS = [
    "人工智能",
    "机器学习",
    "深度学习",
    "计算机视觉",
    "自然语言处理",
    "大模型",
    "智能算法",
    "智能机器人",
]


@dataclass
class Indicator:
    indicator_id: str
    system: str
    label: str
    dimension: str
    unit: str
    method_note: str
    preferred_sources: str
    access_level: str
    query_templates: list[str] = field(default_factory=list)
    extraction_keywords: list[str] = field(default_factory=list)


INDICATORS: list[Indicator] = [
    Indicator(
        "F_FIN_GDP",
        "F_finance",
        "金融业增加值/GDP",
        "区域金融规模",
        "%",
        "金融业增加值除以地区生产总值；需统一当年价或年鉴口径。",
        "国家统计局、各省统计年鉴、统计公报",
        "public",
        [
            "{province} {year} 金融业增加值 GDP 统计年鉴",
            "{province} {year} 国民经济和社会发展统计公报 金融业 增加值",
        ],
        ["金融业增加值", "地区生产总值", "GDP"],
    ),
    Indicator(
        "F_LOAN_DEPOSIT_GDP",
        "F_finance",
        "存贷款余额/GDP",
        "金融深化程度",
        "%",
        "金融机构本外币存款余额与贷款余额之和除以GDP。",
        "人民银行分行金融运行报告、统计年鉴",
        "public",
        [
            "{province} {year} 存贷款余额 GDP 人民银行 金融运行报告",
            "{province} {year} 金融机构 本外币 存款余额 贷款余额",
        ],
        ["存款余额", "贷款余额", "本外币", "金融机构"],
    ),
    Indicator(
        "F_DIGITAL_FINANCE",
        "F_finance",
        "数字普惠金融指数",
        "数字金融环境",
        "index",
        "北京大学数字普惠金融指数；通常需下载公开数据包后导入。",
        "北京大学数字金融研究中心",
        "download_or_manual",
        [
            "北京大学 数字普惠金融指数 {year} {province}",
            "PKU Digital Financial Inclusion Index China {year} data",
        ],
        ["数字普惠金融指数", "覆盖广度", "使用深度"],
    ),
    Indicator(
        "F_AI_FINANCING_EVENTS",
        "F_finance",
        "AI融资事件数",
        "AI定向资本支持",
        "count",
        "按AI企业口径统计融资事件数；商业数据库结果需保留导出来源。",
        "IT桔子、清科、投中、企查查、天眼查、新闻稿",
        "restricted_or_public_news",
        [
            "{province} {year} 人工智能 融资 事件",
            "{province} {year} AI 企业 融资 投资",
            "{province} {year} 人工智能 创投 融资",
        ],
        ["融资", "投资", "轮", "人工智能", "AI"],
    ),
    Indicator(
        "F_AI_GUIDANCE_FUND",
        "F_finance",
        "AI/数字经济/战新产业基金规模",
        "政府引导资本",
        "亿元",
        "优先统计明确投向AI、数字经济或战略性新兴产业的政府基金规模。",
        "发改委、财政厅、工信厅、基金公告、政府官网",
        "public",
        [
            "{province} {year} 人工智能 产业基金 规模",
            "{province} {year} 数字经济 产业基金 政府引导基金",
            "{province} {year} 战略性新兴产业 引导基金 人工智能",
        ],
        ["产业基金", "引导基金", "规模", "人工智能", "数字经济"],
    ),
    Indicator(
        "E_AI_MAJOR_COUNT",
        "E_education",
        "AI相关专业数量",
        "人才培养入口",
        "count",
        "按E0/E1/E2三类专业口径分别统计；基准建议采用E1。",
        "教育部本科专业备案、高校官网、招生章程",
        "public",
        [
            "{province} {year} 人工智能 专业 高校 数量",
            "{province} {year} 教育部 本科专业备案 人工智能 智能科学与技术 数据科学 机器人工程",
        ],
        ["人工智能", "智能科学与技术", "数据科学与大数据技术", "机器人工程"],
    ),
    Indicator(
        "E_AI_MASTER_PHD",
        "E_education",
        "AI相关硕博点数量",
        "高层次培养能力",
        "count",
        "以人工智能、计算机、控制、电子信息、软件等相关学位点为基础，需说明口径。",
        "国务院学位委员会、教育部、高校研究生院",
        "public",
        [
            "{province} {year} 人工智能 硕士点 博士点 高校",
            "{province} {year} 计算机 软件工程 控制科学 电子信息 学位授权点",
        ],
        ["博士点", "硕士点", "学位授权点", "人工智能"],
    ),
    Indicator(
        "E_AI_PAPERS",
        "E_education",
        "高校AI论文数量",
        "高校知识产出",
        "count",
        "用AI关键词检索高校署名论文；CNKI/WoS/Scopus多为数据库导出。",
        "CNKI、Web of Science、Scopus、Google Scholar",
        "restricted_or_manual_export",
        [
            "{province} 高校 {year} 人工智能 论文 数量",
            "{province} university artificial intelligence papers {year}",
        ],
        ["论文", "人工智能", "高校", "机器学习", "深度学习"],
    ),
    Indicator(
        "E_UNIV_AI_PATENTS",
        "E_education",
        "高校AI专利数量",
        "高校技术产出",
        "count",
        "国家知识产权局或专利数据库按申请人所在地、申请人类型和AI关键词统计。",
        "国家知识产权局、专利检索系统、Incopat等",
        "restricted_or_manual_export",
        [
            "{province} 高校 人工智能 专利 {year}",
            "{province} 大学 机器学习 深度学习 专利 {year}",
        ],
        ["专利", "高校", "大学", "人工智能", "机器学习"],
    ),
    Indicator(
        "E_AI_INDUSTRY_COLLAB",
        "E_education",
        "AI产业学院/联合实验室数量",
        "产教连接",
        "count",
        "统计AI相关产业学院、校企联合实验室、现代产业学院。",
        "高校官网、教育厅、科技厅、工信厅",
        "public",
        [
            "{province} {year} 人工智能 产业学院",
            "{province} {year} AI 校企联合实验室",
            "{province} {year} 人工智能 现代产业学院",
        ],
        ["产业学院", "联合实验室", "校企", "人工智能"],
    ),
    Indicator(
        "I_AI_COMPANY_COUNT",
        "I_industry",
        "AI企业数量",
        "产业主体规模",
        "count",
        "按I0/I1/I2企业口径统计；商业数据库导出需留痕。",
        "企查查、天眼查、工商数据、政府重点企业名单",
        "restricted_or_public_lists",
        [
            "{province} {year} 人工智能 企业 数量",
            "{province} AI 企业 名单 人工智能 {year}",
            "{province} 重点 人工智能 企业 名单",
        ],
        ["企业", "人工智能", "名单", "数量"],
    ),
    Indicator(
        "I_AI_ENTERPRISE_PATENTS",
        "I_industry",
        "AI企业专利数量",
        "企业创新能力",
        "count",
        "按企业申请人、AI关键词和年份统计。",
        "国家知识产权局、专利数据库、企业年报",
        "restricted_or_manual_export",
        [
            "{province} 企业 人工智能 专利 {year}",
            "{province} AI 企业 专利 数量 {year}",
        ],
        ["专利", "企业", "人工智能", "机器学习", "深度学习"],
    ),
    Indicator(
        "I_TECH_CONTRACT",
        "I_industry",
        "技术合同成交额",
        "成果转化活跃度",
        "亿元",
        "若无法分离AI口径，可先用地区技术合同成交额作为成果转化环境。",
        "科技统计公报、科技厅、统计年鉴",
        "public",
        [
            "{province} {year} 技术合同成交额",
            "{province} {year} 技术市场 成交额 科技统计公报",
        ],
        ["技术合同成交额", "技术市场", "成交额"],
    ),
    Indicator(
        "I_AI_JOBS",
        "I_industry",
        "AI岗位数量",
        "产业人才需求",
        "count",
        "招聘平台数据存在样本偏差；建议作为增强变量或稳健性变量。",
        "BOSS直聘、智联招聘、猎聘、公开岗位页",
        "platform_limited",
        [
            "{province} {year} 人工智能 岗位 数量 招聘",
            "{province} AI 工程师 招聘 {year}",
        ],
        ["招聘", "岗位", "人工智能", "算法工程师", "机器学习"],
    ),
    Indicator(
        "I_AI_SCENARIOS",
        "I_industry",
        "AI应用示范项目/场景数量",
        "应用落地",
        "count",
        "统计工信、发改、科技部门公布的AI应用场景、示范项目。",
        "工信部、发改委、科技厅、工信厅",
        "public",
        [
            "{province} {year} 人工智能 应用场景 示范项目",
            "{province} {year} AI 应用场景 清单",
        ],
        ["应用场景", "示范项目", "人工智能", "清单"],
    ),
    Indicator(
        "S_SERVICE_AI_INTENSITY",
        "S_mechanism",
        "第三产业AI应用强度",
        "产业吸纳机制",
        "ratio",
        "增强变量；可用第三产业AI企业/岗位/专利/融资事件占全部AI对应数量之比。",
        "企业库、招聘平台、专利库、融资数据库",
        "derived_from_ai_records",
        [
            "{province} {year} 第三产业 人工智能 应用 企业 岗位",
            "{province} {year} 服务业 人工智能 应用 金融 医疗 教育 政务",
        ],
        ["第三产业", "服务业", "人工智能", "应用"],
    ),
    Indicator(
        "C_GDP_PER_CAPITA",
        "C_control",
        "人均GDP",
        "经济发展水平",
        "元/人",
        "控制变量。",
        "国家统计局、统计年鉴、统计公报",
        "public",
        [
            "{province} {year} 人均GDP 统计公报",
            "{province} {year} 人均地区生产总值",
        ],
        ["人均GDP", "人均地区生产总值"],
    ),
    Indicator(
        "C_INDUSTRY_STRUCTURE",
        "C_control",
        "第二产业/第三产业占比",
        "产业基础",
        "%",
        "控制变量；可拆为制造业占比、二产占比、三产占比。",
        "国家统计局、统计年鉴、统计公报",
        "public",
        [
            "{province} {year} 第二产业 第三产业 占比 统计公报",
            "{province} {year} 三次产业结构 统计年鉴",
        ],
        ["第二产业", "第三产业", "产业结构", "占比"],
    ),
    Indicator(
        "C_SCI_TECH_FISCAL",
        "C_control",
        "科技财政支出/GDP",
        "政府科技投入",
        "%",
        "控制变量；科技支出除以GDP。",
        "财政年鉴、统计年鉴、财政厅",
        "public",
        [
            "{province} {year} 科学技术支出 GDP 财政",
            "{province} {year} 科技财政支出 统计年鉴",
        ],
        ["科学技术支出", "科技支出", "财政"],
    ),
    Indicator(
        "C_DIGITAL_INFRA",
        "C_control",
        "数字基础设施",
        "数字基础",
        "count_or_index",
        "宽带用户、移动互联网用户、5G基站、算力中心等可择一或组合。",
        "通信管理局、统计年鉴、工信厅",
        "public",
        [
            "{province} {year} 互联网宽带用户 移动互联网用户 统计",
            "{province} {year} 5G基站 数字基础设施",
        ],
        ["宽带用户", "移动互联网", "5G基站", "数字基础设施"],
    ),
    Indicator(
        "C_URBANIZATION",
        "C_control",
        "城镇化率",
        "城镇化水平",
        "%",
        "控制变量。",
        "国家统计局、统计年鉴、统计公报",
        "public",
        [
            "{province} {year} 城镇化率 统计公报",
            "{province} {year} 常住人口城镇化率",
        ],
        ["城镇化率", "常住人口城镇化率"],
    ),
]


def ensure_directories(data_root: Path) -> dict[str, Path]:
    paths = {
        "config": data_root / "config",
        "processed": data_root / "processed",
        "raw_pages": data_root / "raw" / "pages",
        "raw_tables": data_root / "raw" / "tables",
        "logs": data_root / "logs",
        "manual_import": data_root / "manual_import",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def safe_name(text: str, limit: int = 80) -> str:
    text = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", text, flags=re.UNICODE).strip("_")
    return text[:limit] if text else "item"


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def indicator_rows() -> list[dict[str, Any]]:
    return [
        {
            "indicator_id": indicator.indicator_id,
            "system": indicator.system,
            "label": indicator.label,
            "dimension": indicator.dimension,
            "unit": indicator.unit,
            "method_note": indicator.method_note,
            "preferred_sources": indicator.preferred_sources,
            "access_level": indicator.access_level,
            "query_templates": " | ".join(indicator.query_templates),
            "extraction_keywords": " | ".join(indicator.extraction_keywords),
        }
        for indicator in INDICATORS
    ]


def build_panel_template(provinces: list[str], years: list[int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for province in provinces:
        for year in years:
            for indicator in INDICATORS:
                rows.append(
                    {
                        "province": province,
                        "year": year,
                        "indicator_id": indicator.indicator_id,
                        "system": indicator.system,
                        "label": indicator.label,
                        "value": "",
                        "unit": indicator.unit,
                        "source_url": "",
                        "source_title": "",
                        "source_type": indicator.access_level,
                        "confidence": "",
                        "verification_note": "",
                    }
                )
    return rows


def tavily_search(query: str, api_key: str, max_results: int, timeout: int) -> list[dict[str, Any]]:
    response = requests.post(
        "https://api.tavily.com/search",
        json={
            "api_key": api_key,
            "query": query,
            "search_depth": "basic",
            "include_answer": False,
            "include_raw_content": False,
            "max_results": max_results,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    results = []
    for item in data.get("results", []):
        results.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),
                "score": item.get("score", ""),
                "search_provider": "tavily",
            }
        )
    return results


def duckduckgo_search(query: str, max_results: int, timeout: int) -> list[dict[str, Any]]:
    url = "https://html.duckduckgo.com/html/"
    response = requests.post(
        url,
        data={"q": query},
        headers={"User-Agent": "Mozilla/5.0 thesis-data-collector/1.0"},
        timeout=timeout,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    for result in soup.select(".result")[:max_results]:
        link = result.select_one(".result__a")
        snippet = result.select_one(".result__snippet")
        if not link:
            continue
        results.append(
            {
                "title": link.get_text(" ", strip=True),
                "url": link.get("href", ""),
                "snippet": snippet.get_text(" ", strip=True) if snippet else "",
                "score": "",
                "search_provider": "duckduckgo_html",
            }
        )
    return results


def search_web(query: str, max_results: int, timeout: int) -> list[dict[str, Any]]:
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if api_key:
        try:
            return tavily_search(query, api_key, max_results, timeout)
        except Exception as exc:
            print(f"Tavily search failed, falling back to DuckDuckGo: {exc}")
    try:
        return duckduckgo_search(query, max_results, timeout)
    except Exception as exc:
        print(f"Search failed: {query} -> {exc}")
        return []


def make_queries(indicator: Indicator, province: str, year: int) -> list[str]:
    return [template.format(province=province, year=year) for template in indicator.query_templates]


def fetch_page(url: str, timeout: int, max_bytes: int) -> tuple[str, str]:
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 thesis-data-collector/1.0"},
        timeout=timeout,
        stream=True,
    )
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    chunks: list[bytes] = []
    size = 0
    for chunk in response.iter_content(chunk_size=8192):
        if not chunk:
            continue
        chunks.append(chunk)
        size += len(chunk)
        if size >= max_bytes:
            break
    raw = b"".join(chunks)
    encoding = response.encoding
    if not encoding or encoding.lower() in {"iso-8859-1", "latin-1"}:
        match = from_bytes(raw).best()
        encoding = match.encoding if match else "utf-8"
    text = raw.decode(encoding, errors="replace")
    return text, content_type


def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True))


def extract_numeric_candidates(
    text: str,
    indicator: Indicator,
    province: str,
    year: int,
    url: str,
    title: str,
    max_candidates: int = 12,
) -> list[dict[str, Any]]:
    keywords = indicator.extraction_keywords or [indicator.label]
    candidates: list[dict[str, Any]] = []
    number_pattern = r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?\s*(?:万亿元|亿元|万元|万人|人|家|个|项|%|％|件|次|亿美元|元/人|元)?"
    for keyword in keywords:
        for match in re.finditer(re.escape(keyword), text):
            start = max(0, match.start() - 80)
            end = min(len(text), match.end() + 120)
            context = text[start:end]
            numbers = re.findall(number_pattern, context)
            for number in numbers[:4]:
                candidates.append(
                    {
                        "province": province,
                        "year": year,
                        "indicator_id": indicator.indicator_id,
                        "label": indicator.label,
                        "keyword": keyword,
                        "candidate_value": number.strip(),
                        "context": context,
                        "source_title": title,
                        "source_url": url,
                    }
                )
            if len(candidates) >= max_candidates:
                return candidates
    return candidates


def extract_and_save_tables(html: str, table_dir: Path, file_prefix: str, source_url: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        tables = pd.read_html(StringIO(html))
    except Exception:
        return rows
    for idx, table in enumerate(tables):
        filename = f"{file_prefix}_table_{idx + 1}.csv"
        path = table_dir / filename
        table.to_csv(path, index=False, encoding="utf-8-sig")
        rows.append(
            {
                "table_file": str(path),
                "rows": len(table),
                "columns": len(table.columns),
                "source_url": source_url,
            }
        )
    return rows


def create_manual_todo(indicator_rows_data: list[dict[str, Any]], panel_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    restricted = {
        row["indicator_id"]: row
        for row in indicator_rows_data
        if row["access_level"] not in {"public", "derived_from_ai_records"}
    }
    todo: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in panel_rows:
        if row["indicator_id"] not in restricted:
            continue
        key = (row["indicator_id"], row["province"])
        if key in seen:
            continue
        seen.add(key)
        indicator = restricted[row["indicator_id"]]
        todo.append(
            {
                "indicator_id": row["indicator_id"],
                "label": indicator["label"],
                "province": row["province"],
                "needed_years": "2018-2024/2025",
                "access_level": indicator["access_level"],
                "recommended_action": "从商业数据库或学术数据库导出CSV/XLSX后放入 数据/manual_import，再运行本脚本 --index-manual-imports",
                "preferred_sources": indicator["preferred_sources"],
            }
        )
    return todo


def index_manual_imports(manual_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in manual_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".csv", ".xlsx", ".xls", ".json", ".txt"}:
            continue
        rows.append(
            {
                "file": str(path),
                "name": path.name,
                "suffix": path.suffix.lower(),
                "size_bytes": path.stat().st_size,
                "last_modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
            }
        )
    return rows


def run_collection(args: argparse.Namespace) -> None:
    paths = ensure_directories(Path(args.data_root))
    years = list(range(args.start_year, args.end_year + 1))
    provinces = args.provinces or (NARROW_PROVINCES if args.sample == "narrow" else CORE_PROVINCES)
    selected_ids = set(args.indicators or [])
    selected_indicators = [
        indicator for indicator in INDICATORS if not selected_ids or indicator.indicator_id in selected_ids
    ]

    indicator_data = indicator_rows()
    write_csv(
        paths["config"] / "indicator_catalog.csv",
        indicator_data,
        [
            "indicator_id",
            "system",
            "label",
            "dimension",
            "unit",
            "method_note",
            "preferred_sources",
            "access_level",
            "query_templates",
            "extraction_keywords",
        ],
    )

    panel_rows = build_panel_template(provinces, years)
    write_csv(
        paths["processed"] / "panel_template.csv",
        panel_rows,
        [
            "province",
            "year",
            "indicator_id",
            "system",
            "label",
            "value",
            "unit",
            "source_url",
            "source_title",
            "source_type",
            "confidence",
            "verification_note",
        ],
    )

    write_csv(
        paths["processed"] / "manual_todo.csv",
        create_manual_todo(indicator_data, panel_rows),
        [
            "indicator_id",
            "label",
            "province",
            "needed_years",
            "access_level",
            "recommended_action",
            "preferred_sources",
        ],
    )

    manual_rows = index_manual_imports(paths["manual_import"])
    write_csv(
        paths["processed"] / "manual_import_index.csv",
        manual_rows,
        ["file", "name", "suffix", "size_bytes", "last_modified"],
    )

    if args.index_manual_imports or args.dry_run:
        write_manifest(paths, args, search_rows=[], numeric_rows=[], table_rows=[])
        return

    search_rows: list[dict[str, Any]] = []
    numeric_rows: list[dict[str, Any]] = []
    table_rows: list[dict[str, Any]] = []
    fetched_urls: set[str] = set()
    page_count = 0

    for province in provinces:
        for year in years:
            for indicator in selected_indicators:
                for query in make_queries(indicator, province, year):
                    print(f"Searching: {query}")
                    results = search_web(query, args.limit_per_query, args.timeout)
                    for rank, result in enumerate(results, start=1):
                        url = result.get("url", "")
                        row = {
                            "province": province,
                            "year": year,
                            "indicator_id": indicator.indicator_id,
                            "label": indicator.label,
                            "query": query,
                            "rank": rank,
                            "title": result.get("title", ""),
                            "url": url,
                            "snippet": result.get("snippet", ""),
                            "score": result.get("score", ""),
                            "search_provider": result.get("search_provider", ""),
                        }
                        search_rows.append(row)
                    time.sleep(args.delay)

                    for result in results[: args.download_top_n]:
                        if args.max_pages and page_count >= args.max_pages:
                            continue
                        url = result.get("url", "")
                        if not url or url in fetched_urls:
                            continue
                        fetched_urls.add(url)
                        try:
                            html, content_type = fetch_page(url, args.timeout, args.max_bytes)
                        except Exception as exc:
                            print(f"Fetch failed: {url} -> {exc}")
                            continue

                        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
                        domain = safe_name(urlparse(url).netloc)
                        prefix = safe_name(f"{province}_{year}_{indicator.indicator_id}_{domain}_{digest}")
                        page_file = paths["raw_pages"] / f"{prefix}.html"
                        page_file.write_text(html, encoding="utf-8", errors="replace")
                        page_count += 1

                        text = extract_text(html)
                        numeric_rows.extend(
                            extract_numeric_candidates(
                                text=text,
                                indicator=indicator,
                                province=province,
                                year=year,
                                url=url,
                                title=result.get("title", ""),
                            )
                        )
                        table_rows.extend(
                            extract_and_save_tables(
                                html=html,
                                table_dir=paths["raw_tables"],
                                file_prefix=prefix,
                                source_url=url,
                            )
                        )
                        print(f"Saved page: {page_file}")
                        time.sleep(args.delay)

    write_csv(
        paths["processed"] / "search_results.csv",
        search_rows,
        [
            "province",
            "year",
            "indicator_id",
            "label",
            "query",
            "rank",
            "title",
            "url",
            "snippet",
            "score",
            "search_provider",
        ],
    )
    write_csv(
        paths["processed"] / "numeric_candidates.csv",
        numeric_rows,
        [
            "province",
            "year",
            "indicator_id",
            "label",
            "keyword",
            "candidate_value",
            "context",
            "source_title",
            "source_url",
        ],
    )
    write_csv(
        paths["processed"] / "table_index.csv",
        table_rows,
        ["table_file", "rows", "columns", "source_url"],
    )
    write_manifest(paths, args, search_rows, numeric_rows, table_rows)


def write_manifest(
    paths: dict[str, Path],
    args: argparse.Namespace,
    search_rows: list[dict[str, Any]],
    numeric_rows: list[dict[str, Any]],
    table_rows: list[dict[str, Any]],
) -> None:
    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "data_root": str(Path(args.data_root)),
        "sample": args.sample,
        "provinces": args.provinces,
        "start_year": args.start_year,
        "end_year": args.end_year,
        "selected_indicators": args.indicators,
        "dry_run": args.dry_run,
        "index_manual_imports": args.index_manual_imports,
        "tavily_enabled": bool(os.getenv("TAVILY_API_KEY", "").strip()),
        "search_rows": len(search_rows),
        "numeric_candidates": len(numeric_rows),
        "tables": len(table_rows),
    }
    (paths["logs"] / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect thesis indicator source evidence.")
    parser.add_argument("--data-root", default=str(DATA_ROOT), help="Output data directory.")
    parser.add_argument("--sample", choices=["narrow", "core"], default="narrow")
    parser.add_argument("--provinces", nargs="*", help="Override province list, e.g. 福建 广东")
    parser.add_argument("--start-year", type=int, default=2018)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--indicators", nargs="*", help="Limit to indicator ids.")
    parser.add_argument("--limit-per-query", type=int, default=3)
    parser.add_argument("--download-top-n", type=int, default=1)
    parser.add_argument("--max-pages", type=int, default=0, help="0 means unlimited.")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--max-bytes", type=int, default=2_000_000)
    parser.add_argument("--dry-run", action="store_true", help="Only create catalogs/templates.")
    parser.add_argument("--index-manual-imports", action="store_true", help="Only refresh manual import index.")
    return parser.parse_args()


if __name__ == "__main__":
    run_collection(parse_args())
