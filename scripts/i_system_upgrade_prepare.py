from __future__ import annotations

import argparse
import json
import re
import shutil
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
    "config",
    "scripts",
    "docs",
]

LEGACY_DIR = Path("archive/legacy_outputs")

SEARCH_TERMS = [
    "i_system",
    "I_panel",
    "firm",
    "patent",
    "job",
    "岗位",
    "企业",
    "专利",
    "experimental_I",
    "i_b_ai_digital",
    "quanzhou",
    "泉州",
]

CITIES = ["福州", "厦门", "泉州"]
YEARS = [str(year) for year in range(2019, 2025)]

STRONG_AI_KEYWORDS = [
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
]

AI_TOOL_KEYWORDS = [
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
]

BASIC_DIGITAL_KEYWORDS = [
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
]

INDUSTRIAL_DIGITAL_KEYWORDS = [
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
]

WEAK_KEYWORDS = [
    "科技",
    "智能",
    "信息",
    "网络",
    "数字",
    "平台",
    "系统",
    "互联网",
]

JOB_CANDIDATE_COLUMNS = [
    "city",
    "year",
    "source_city",
    "job_title",
    "company_name",
    "posting_date",
    "job_description",
    "skill_text",
    "matched_strong_ai_keywords",
    "matched_ai_tool_keywords",
    "matched_basic_digital_keywords",
    "matched_industrial_digital_keywords",
    "matched_weak_keywords",
    "job_classification",
    "job_ai_score",
    "source_url",
    "source_type",
    "collection_status",
    "reviewer_decision",
    "reviewer_notes",
]

JOB_PANEL_COLUMNS = [
    "city",
    "year",
    "total_job_count",
    "ai_job_strong_count",
    "ai_tool_based_job_count",
    "digital_tech_job_count",
    "industrial_digital_job_count",
    "broad_ai_digital_job_count",
    "ai_job_ratio",
    "broad_ai_digital_job_ratio",
    "avg_job_ai_score",
    "data_status",
    "notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare I-system upgrade assets, keyword dictionary, templates, and recheck plan."
    )
    parser.add_argument("--run-id", default=None, help="Optional run_id override for reproducibility.")
    return parser.parse_args()


def unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return unique


def safe_read_text(path: Path, max_chars: int = 300_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="gb18030", errors="ignore")[:max_chars]
        except Exception:
            return ""
    except Exception:
        return ""


def search_terms_in_text(text: str) -> list[str]:
    lower = text.lower()
    hits: list[str] = []
    for term in SEARCH_TERMS:
        if term.lower() in lower or term in text:
            hits.append(term)
    return hits


def join_unique(values: list[Any]) -> str:
    cleaned = []
    for value in values:
        if pd.isna(value):
            continue
        text = str(value).strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return "、".join(cleaned)


def infer_from_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    info: dict[str, Any] = {
        "row_count": len(df),
        "columns": "、".join(map(str, df.columns.tolist())),
        "cities": [],
        "years": [],
        "contains_quanzhou_2019": False,
        "contains_quanzhou_2020": False,
    }
    columns_lower = {str(col).lower(): col for col in df.columns}
    city_col = None
    year_col = None
    for key in ["city", "城市", "source_city"]:
        if key.lower() in columns_lower:
            city_col = columns_lower[key.lower()]
            break
    for key in ["year", "年份"]:
        if key.lower() in columns_lower:
            year_col = columns_lower[key.lower()]
            break
    if city_col is not None:
        info["cities"] = sorted({str(v).strip() for v in df[city_col].dropna().tolist() if str(v).strip()})
    if year_col is not None:
        years = []
        for value in df[year_col].dropna().tolist():
            try:
                years.append(str(int(float(value))))
            except Exception:
                years.append(str(value).strip())
        info["years"] = sorted(set(years))
    if city_col is not None and year_col is not None:
        temp = df[[city_col, year_col]].dropna()
        temp["_city"] = temp[city_col].astype(str).str.strip()
        temp["_year"] = pd.to_numeric(temp[year_col], errors="coerce").astype("Int64")
        info["contains_quanzhou_2019"] = bool(((temp["_city"] == "泉州") & (temp["_year"] == 2019)).any())
        info["contains_quanzhou_2020"] = bool(((temp["_city"] == "泉州") & (temp["_year"] == 2020)).any())
    return info


def inspect_tabular_file(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    fallback: dict[str, Any] = {
        "row_count": "",
        "columns": "",
        "cities": [],
        "years": [],
        "contains_quanzhou_2019": False,
        "contains_quanzhou_2020": False,
        "text_sample": "",
    }
    try:
        if suffix == ".csv":
            df = pd.read_csv(path)
            info = infer_from_dataframe(df)
            info["text_sample"] = " ".join(map(str, df.head(30).fillna("").astype(str).to_numpy().ravel()))
            return info
        if suffix in {".xlsx", ".xls"}:
            xl = pd.ExcelFile(path)
            all_columns: list[str] = []
            total_rows = 0
            all_cities: list[str] = []
            all_years: list[str] = []
            has_qz_2019 = False
            has_qz_2020 = False
            text_parts: list[str] = []
            for sheet in xl.sheet_names[:20]:
                try:
                    df = pd.read_excel(path, sheet_name=sheet)
                except Exception:
                    continue
                info = infer_from_dataframe(df)
                total_rows += int(info["row_count"] or 0)
                all_columns.append(f"{sheet}: {info['columns']}")
                all_cities.extend(info["cities"])
                all_years.extend(info["years"])
                has_qz_2019 = has_qz_2019 or bool(info["contains_quanzhou_2019"])
                has_qz_2020 = has_qz_2020 or bool(info["contains_quanzhou_2020"])
                text_parts.append(sheet)
                text_parts.append(" ".join(map(str, df.head(20).fillna("").astype(str).to_numpy().ravel())))
            return {
                "row_count": total_rows,
                "columns": " | ".join(all_columns),
                "cities": sorted(set(all_cities)),
                "years": sorted(set(all_years)),
                "contains_quanzhou_2019": has_qz_2019,
                "contains_quanzhou_2020": has_qz_2020,
                "text_sample": " ".join(text_parts)[:300_000],
            }
    except Exception as exc:
        fallback["text_sample"] = f"inspect_error: {exc}"
    return fallback


def infer_data_type(path: Path, text: str, columns: str) -> str:
    blob = f"{path.name} {path.as_posix()} {text} {columns}".lower()
    types = []
    if any(token in blob for token in ["firm", "企业", "company"]):
        types.append("firm_candidate_or_reference")
    if any(token in blob for token in ["patent", "专利"]):
        types.append("patent_candidate_or_reference")
    if any(token in blob for token in ["job", "岗位", "招聘", "skill", "技能"]):
        types.append("job_or_skill_reference")
    if "i_index" in blob or "i_system" in blob or "experimental_i" in blob:
        types.append("i_system_panel_or_method")
    if "ccd" in blob or "d," in blob:
        types.append("ccd_derived_output")
    if not types:
        types.append("manual_review_required")
    return "; ".join(types)


def recommended_use_for(path: Path, inferred_type: str, is_legacy: bool) -> str:
    path_text = path.as_posix()
    name = path.name
    if is_legacy:
        return "legacy_reference_only"
    if "__pycache__" in path_text or name.endswith(".pyc"):
        return "do_not_use"
    if "latest_experimental_analysis_base_panel" in name or "experimental_analysis_base_panel" in name:
        return "current_CCD_input"
    if "experimental_data_assets_check" in name or "experimental_missing_and_outlier_check" in name:
        return "current_CCD_input"
    if "experimental_regression_panel" in name:
        return "current_CCD_input"
    if "job_or_skill_reference" in inferred_type:
        return "upgrade_candidate"
    if "firm_candidate_or_reference" in inferred_type or "patent_candidate_or_reference" in inferred_type:
        return "upgrade_candidate"
    if path.suffix.lower() in {".md", ".py", ".json"}:
        return "manual_review_required"
    return "manual_review_required"


def scan_assets(project_root: Path) -> tuple[pd.DataFrame, int, list[str]]:
    warnings: list[str] = []
    candidate_files: list[Path] = []
    for search_dir in SEARCH_DIRS:
        root = project_root / search_dir
        if not root.exists():
            warnings.append(f"搜索目录不存在：{search_dir}")
            continue
        candidate_files.extend([p for p in root.rglob("*") if p.is_file()])
    candidate_files = unique_paths(candidate_files)

    rows: list[dict[str, Any]] = []
    for path in candidate_files:
        suffix = path.suffix.lower()
        rel_path = path.relative_to(project_root)
        text = ""
        tabular_info = {
            "row_count": "",
            "columns": "",
            "cities": [],
            "years": [],
            "contains_quanzhou_2019": False,
            "contains_quanzhou_2020": False,
            "text_sample": "",
        }
        if suffix in {".csv", ".xlsx", ".xls"}:
            tabular_info = inspect_tabular_file(path)
            text = tabular_info.get("text_sample", "")
        elif suffix in {".py", ".md", ".json", ".yml", ".yaml", ".txt"}:
            text = safe_read_text(path)
        else:
            text = rel_path.as_posix()

        filename_hits = search_terms_in_text(path.name)
        content_hits = search_terms_in_text(text)
        if not filename_hits and not content_hits:
            continue

        full_blob = f"{rel_path.as_posix()} {path.name} {text} {tabular_info.get('columns', '')}"
        inferred_type = infer_data_type(path, full_blob, str(tabular_info.get("columns", "")))
        lower_blob = full_blob.lower()
        cities = tabular_info.get("cities", []) or [city for city in CITIES if city in full_blob]
        years = tabular_info.get("years", []) or [year for year in YEARS if year in full_blob]
        contains_qz_2019 = bool(tabular_info.get("contains_quanzhou_2019")) or ("泉州" in full_blob and "2019" in full_blob)
        contains_qz_2020 = bool(tabular_info.get("contains_quanzhou_2020")) or ("泉州" in full_blob and "2020" in full_blob)
        recommended_use = recommended_use_for(path, inferred_type, False)
        notes = []
        if "latest_experimental_analysis_base_panel" in path.name:
            notes.append("当前 latest experimental 面板，包含 I_index 与泉州 2019/2020 0 值状态；不得在本轮覆盖。")
        if "i_job_raw" in lower_blob or "job" in lower_blob or "岗位" in full_blob:
            notes.append("包含岗位/技能方法或占位线索；需人工确认是否为真实岗位数据。")
        if "patent" in lower_blob or "专利" in full_blob:
            notes.append("包含专利相关线索。")
        if "firm" in lower_blob or "企业" in full_blob:
            notes.append("包含企业相关线索。")
        if path.suffix.lower() in {".pyc"} or "__pycache__" in rel_path.as_posix():
            notes.append("缓存文件，不建议使用。")
        rows.append(
            {
                "file_path": rel_path.as_posix(),
                "file_name": path.name,
                "file_type": suffix.lstrip(".") or "unknown",
                "inferred_data_type": inferred_type,
                "cities_covered": "、".join(sorted(set(map(str, cities)))),
                "years_covered": "、".join(sorted(set(map(str, years)))),
                "row_count": tabular_info.get("row_count", ""),
                "columns": tabular_info.get("columns", ""),
                "contains_firm_data": bool(re.search(r"firm|企业|company", full_blob, flags=re.I)),
                "contains_patent_data": bool(re.search(r"patent|专利", full_blob, flags=re.I)),
                "contains_job_data": bool(re.search(r"job|岗位|招聘|skill|技能", full_blob, flags=re.I)),
                "contains_quanzhou_2019": contains_qz_2019,
                "contains_quanzhou_2020": contains_qz_2020,
                "used_in_current_CCD": recommended_use == "current_CCD_input",
                "recommended_use": recommended_use,
                "notes": " ".join(notes),
            }
        )

    legacy_root = project_root / LEGACY_DIR
    if legacy_root.exists():
        for path in unique_paths([p for p in legacy_root.rglob("*") if p.is_file()]):
            rel_path = path.relative_to(project_root)
            if not search_terms_in_text(path.name):
                continue
            rows.append(
                {
                    "file_path": rel_path.as_posix(),
                    "file_name": path.name,
                    "file_type": path.suffix.lower().lstrip(".") or "unknown",
                    "inferred_data_type": "legacy_output_reference",
                    "cities_covered": "",
                    "years_covered": "",
                    "row_count": "",
                    "columns": "",
                    "contains_firm_data": bool(re.search(r"firm|企业|company", path.name, flags=re.I)),
                    "contains_patent_data": bool(re.search(r"patent|专利", path.name, flags=re.I)),
                    "contains_job_data": bool(re.search(r"job|岗位|招聘|skill|技能", path.name, flags=re.I)),
                    "contains_quanzhou_2019": "泉州" in path.name and "2019" in path.name,
                    "contains_quanzhou_2020": "泉州" in path.name and "2020" in path.name,
                    "used_in_current_CCD": False,
                    "recommended_use": "legacy_reference_only",
                    "notes": "旧式散落输出，仅可追溯，不作为本轮 I 端升级输入。",
                }
            )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["recommended_use", "file_path"]).reset_index(drop=True)
    return df, len(candidate_files), warnings


def write_excel(path: Path, sheets: dict[str, pd.DataFrame]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            safe_sheet = sheet_name[:31]
            df.to_excel(writer, index=False, sheet_name=safe_sheet)
            ws = writer.book[safe_sheet]
            ws.freeze_panes = "A2"
            for col_cells in ws.columns:
                max_len = 0
                column_letter = col_cells[0].column_letter
                for cell in col_cells[:80]:
                    value = "" if cell.value is None else str(cell.value)
                    max_len = max(max_len, len(value))
                ws.column_dimensions[column_letter].width = min(max(max_len + 2, 12), 48)
            ws.auto_filter.ref = ws.dimensions


def write_keywords(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def block(name: str, values: list[str]) -> list[str]:
        return [f"{name}:"] + [f"  - {value}" for value in values] + [""]

    lines: list[str] = [
        "# I system upgrade keyword dictionary",
        "# This dictionary supports experimental job-skill pilot collection; it is not a CCD result file.",
        "",
    ]
    lines.extend(block("strong_ai_keywords", STRONG_AI_KEYWORDS))
    lines.extend(block("ai_tool_keywords", AI_TOOL_KEYWORDS))
    lines.extend(block("basic_digital_keywords", BASIC_DIGITAL_KEYWORDS))
    lines.extend(block("industrial_digital_keywords", INDUSTRIAL_DIGITAL_KEYWORDS))
    lines.extend(block("weak_keywords", WEAK_KEYWORDS))
    path.write_text("\n".join(lines), encoding="utf-8")


def write_job_rules(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = """# 岗位—技能识别规则

本文档用于 I 端产业系统升级版试点。规则只用于岗位/技能候选数据的实验性分类，不得倒填历史年份，也不得直接替代当前 experimental I_index。

## 1. 分类规则

1. 命中 `strong_ai_keywords >= 1`：
   `job_classification = ai_job_strong`

2. 命中 `ai_tool_keywords >= 1`，且岗位标题或描述包含“技术、研发、工程师、算法、开发、数据”之一：
   `job_classification = ai_job_tool_based`

3. 命中 `basic_digital_keywords >= 2`，且岗位标题或描述包含“技术、研发、工程师、开发、数据”之一：
   `job_classification = digital_tech_job`

4. 命中 `industrial_digital_keywords >= 1`，且岗位标题或描述包含“工程师、技术、研发、自动化、制造、设备、工业”之一：
   `job_classification = industrial_digital_job`

5. 只命中 `weak_keywords`：
   `job_classification = weak_only_review`

6. 没有有效命中：
   `job_classification = non_ai_job`

## 2. C/B/X 口径

- C 保守口径 = `ai_job_strong + ai_job_tool_based`
- B 基本口径 = `C + digital_tech_job`
- X 扩大口径 = `B + industrial_digital_job`
- `weak_only_review` 不直接纳入任何口径，只进入人工复核。

## 3. 人工复核原则

- 岗位标题只出现“智能、科技、平台、系统”等弱词时，不应自动认定为 AI 或数字技术岗位。
- 制造业岗位需要结合岗位描述识别是否涉及工业互联网、机器视觉、智能制造、自动化控制、工业软件等实质性数字化技能。
- 同一岗位多次发布时，需要保留原始记录，但城市—年份面板汇总时应标记去重口径。
- 岗位年份应以发布时间或招聘公告发布时间为准，不能用当前页面抓取日期倒推历史年份。
"""
    path.write_text(content, encoding="utf-8")


def write_indicator_design(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = """# I 端产业系统升级版指标设计说明

## 1. 为什么当前 I 端需要升级

当前 experimental CCD 的 I 端主要使用 AI/数字技术企业存量与 AI/数字技术专利申请数量。这两个变量能刻画城市产业端的组织基础和技术产出，但口径检验显示，泉州 2019、2020 的 `I_index=0` 对低位波动路径判断影响明显。因此，需要在现有企业和专利指标之外，补充更接近企业实际 AI 投入行为的岗位—技能需求指标。

## 2. 企业存量和专利申请的作用

企业存量用于刻画产业端是否已经形成 AI/数字技术相关经营主体。专利申请用于刻画技术创新和知识产出。二者适合作为产业系统的基础性、相对稳定指标。

## 3. 企业存量和专利申请的不足

企业注册或经营范围可能不能反映当年真实 AI 投入强度；专利申请存在滞后性和行业偏向，也可能遗漏制造业数字化、工业软件、机器视觉、工业互联网等岗位驱动型转型活动。对于泉州这类制造业基础较强的城市，单靠企业和专利可能低估产业数字化承接。

## 4. 方颖等招聘大数据方法的启发

方颖等关于企业 AI 投入的研究提示，企业对 AI 相关技能人才的招聘需求可以更直接反映企业采用、部署和扩展 AI 技术的行为。招聘数据不只是劳动力市场信息，也可作为企业技术投入和组织能力建设的观测窗口。

## 5. 新增岗位—技能指标的理论意义

岗位—技能指标能够连接教育供给与产业吸纳：教育端提供 AI/数字技术人才培养，产业端通过招聘岗位释放技能需求。该指标有助于识别企业和专利数据未能充分捕捉的“产业承接能力”。

## 6. I_upgrade_C、I_upgrade_B、I_upgrade_X 三种升级口径

- `I_upgrade_C`：保守口径，只纳入 `ai_job_strong` 与 `ai_job_tool_based`。
- `I_upgrade_B`：基本口径，在 C 基础上加入 `digital_tech_job`。
- `I_upgrade_X`：扩大口径，在 B 基础上加入 `industrial_digital_job`。

三种口径用于稳健性比较，不应预设其中某一口径必然正确。

## 7. 为什么不能用当前招聘数据倒填历史年份

招聘数据具有强时间属性。若用当前网页或当前招聘平台数据倒填 2019—2024，会把当期岗位需求错误投射到历史年份，造成时间错配和回看偏误。历史岗位数据必须来自带有历史发布时间或历史公告归档的来源。

## 8. 为什么泉州 2019、2020 是第一轮试点重点

泉州 2019、2020 在当前面板中 `I_index=0` 且 `D=0`，口径检验表明剔除这两个 0 值样本后，泉州低位波动路径明显弱化。因此，泉州 2019、2020 是判断当前 I 端是否低估制造业数字化承接能力的关键试点年份。

## 9. 后续如何将岗位指标纳入 CCD 对比

后续可先生成城市—年份岗位面板，再分别计算 `I_upgrade_C/B/X` 的标准化指标，并与 current I_index 进行并列表达。只有在岗位数据来源、时间口径、去重规则和城市归属规则通过核验后，才可进入新的 experimental CCD 对比运行。

## 10. 升级版指标和 current I_index 的关系

`I_upgrade_C/B/X` 是 current I_index 的扩展试验，不是对 current I_index 的直接覆盖。当前 latest experimental base panel 应保留为原始实验结果；升级版应另建面板、另设 run_id，并通过口径检验说明差异来源。
"""
    path.write_text(content, encoding="utf-8")


def write_recheck_plan(path: Path, run_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"""# 泉州 2019、2020 I 端升级试点复核计划

## 1. 当前问题

当前 experimental CCD 面板中，泉州 2019、2020 的 `I_index=0`，对应 `D=0`。口径检验显示，剔除这两个 0 值后，泉州低位波动路径会明显弱化，说明这两个年份是产业端口径敏感点。

## 2. 需要复核的内容

- 企业候选是否遗漏；
- 专利候选是否遗漏；
- 是否存在制造业数字化岗位；
- 是否存在工业互联网、机器视觉、智能制造相关岗位；
- 是否存在岗位发布时间可确认为 2019 或 2020 的历史招聘公告；
- 是否存在企业官网、政府公告或招聘会材料中的历史岗位线索。

## 3. 可尝试数据来源

- 泉州公共就业人才服务网站；
- 泉州高校就业信息网；
- 泉州企业官网招聘页；
- 招聘会公告；
- 地方政府数字化转型/智能制造项目公告。

## 4. 复核输出要求

- 仅记录带有明确年份依据的岗位或公告；
- 不使用当前招聘页面倒填历史年份；
- 保留 `source_url`、`source_type`、`posting_date`、`collection_status` 和 `reviewer_notes`；
- 先形成 `i_system_upgrade_job_posting_candidates_template` 候选表，再汇总为城市—年份岗位面板；
- `weak_only_review` 不直接计入升级口径，必须人工复核。

## 5. 对当前 CCD 结论的可能影响

若泉州 2019、2020 存在可核验的 AI/数字技术或制造业数字化岗位，则当前 `I_index=0` 可能低估了产业承接能力。后续 `I_upgrade_C/B/X` 口径下，泉州早期 D 值可能不再为 0，低位波动路径可能变为“低位改善”或“波动调整”。但在岗位数据核验前，不能直接修改当前 latest experimental base panel。

## 6. 下一步建议

建议进入泉州 2019、2020 岗位/技能小规模试点采集。试点范围应先限于泉州两个年份，不扩展全省，不重跑 CCD。待候选岗位数据通过人工复核后，再生成独立的 I 端升级版面板和后续 CCD 对比。

## 7. 运行信息

- run_id：{run_id}
- legacy_used_as_input：false
- 本计划不是 final 结论，仅用于 i_system_upgrade 试点准备。
"""
    path.write_text(content, encoding="utf-8")


def build_field_dictionary(columns: list[str], template_type: str) -> pd.DataFrame:
    descriptions = {
        "city": "样本城市，试点阶段优先为泉州。",
        "year": "岗位或面板年份，必须来自发布时间或历史公告依据。",
        "source_city": "来源页面或公告指向的城市。",
        "job_title": "岗位标题。",
        "company_name": "招聘企业名称。",
        "posting_date": "岗位发布时间或公告发布日期。",
        "job_description": "岗位描述原文或摘要。",
        "skill_text": "技能要求文本。",
        "matched_strong_ai_keywords": "命中的强 AI 关键词。",
        "matched_ai_tool_keywords": "命中的 AI 工具关键词。",
        "matched_basic_digital_keywords": "命中的基础数字技术关键词。",
        "matched_industrial_digital_keywords": "命中的产业数字化关键词。",
        "matched_weak_keywords": "命中的弱关键词，仅复核。",
        "job_classification": "按规则得到的岗位分类。",
        "job_ai_score": "实验性岗位 AI/数字技能强度分值，待后续定义。",
        "source_url": "原始来源 URL。",
        "source_type": "来源类型，如公共就业网站、企业官网、高校就业网、招聘会公告、政府公告。",
        "collection_status": "采集状态，如 pending_collected、collected、needs_review、excluded。",
        "reviewer_decision": "人工复核决策。",
        "reviewer_notes": "人工复核备注。",
        "total_job_count": "城市—年份岗位总数。",
        "ai_job_strong_count": "强 AI 岗位数量。",
        "ai_tool_based_job_count": "AI 工具型岗位数量。",
        "digital_tech_job_count": "基础数字技术岗位数量。",
        "industrial_digital_job_count": "产业数字化岗位数量。",
        "broad_ai_digital_job_count": "B/X 口径下广义 AI/数字岗位数量，具体公式需在试点后确认。",
        "ai_job_ratio": "AI 岗位占比。",
        "broad_ai_digital_job_ratio": "广义 AI/数字岗位占比。",
        "avg_job_ai_score": "平均岗位 AI/数字技能分值。",
        "data_status": "数据状态，如 pending_collection、partially_collected、verified、insufficient_evidence。",
        "notes": "备注。",
    }
    return pd.DataFrame(
        {
            "field_name": columns,
            "template_type": template_type,
            "description": [descriptions.get(col, "") for col in columns],
        }
    )


def create_outputs(project_root: Path, run_id: str) -> dict[str, Any]:
    audit_dir = project_root / "data/audit/i_system_upgrade" / run_id
    interim_dir = project_root / "data/interim/i_system_upgrade" / run_id
    panel_dir = project_root / "data/panel/i_system_upgrade" / run_id
    docs_dir = project_root / "docs/i_system_upgrade"
    config_dir = project_root / "config"

    for directory in [audit_dir, interim_dir, panel_dir, docs_dir, config_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    inventory_df, files_scanned_count, warnings = scan_assets(project_root)

    inventory_path = audit_dir / f"i_system_upgrade_existing_data_inventory_{run_id}.xlsx"
    latest_inventory_path = project_root / "data/audit/i_system_upgrade/latest_i_system_upgrade_existing_data_inventory.xlsx"
    write_excel(
        inventory_path,
        {
            "existing_i_assets": inventory_df,
            "search_terms": pd.DataFrame({"search_term": SEARCH_TERMS}),
            "search_dirs": pd.DataFrame({"search_dir": SEARCH_DIRS}),
        },
    )
    latest_inventory_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(inventory_path, latest_inventory_path)

    keywords_path = config_dir / "i_system_upgrade_keywords.yml"
    write_keywords(keywords_path)

    job_rules_path = docs_dir / "job_skill_classification_rules.md"
    write_job_rules(job_rules_path)

    indicator_path = docs_dir / "i_system_upgrade_indicator_design.md"
    write_indicator_design(indicator_path)

    job_candidates_path = interim_dir / f"i_system_upgrade_job_posting_candidates_template_{run_id}.xlsx"
    latest_job_candidates_path = project_root / "data/interim/i_system_upgrade/latest_i_system_upgrade_job_posting_candidates_template.xlsx"
    write_excel(
        job_candidates_path,
        {
            "job_posting_candidates": pd.DataFrame(columns=JOB_CANDIDATE_COLUMNS),
            "field_dictionary": build_field_dictionary(JOB_CANDIDATE_COLUMNS, "job_posting_candidates"),
            "classification_reference": pd.DataFrame(
                [
                    {"caliber": "I_upgrade_C", "included_classes": "ai_job_strong; ai_job_tool_based"},
                    {"caliber": "I_upgrade_B", "included_classes": "I_upgrade_C; digital_tech_job"},
                    {"caliber": "I_upgrade_X", "included_classes": "I_upgrade_B; industrial_digital_job"},
                    {"caliber": "manual_review_only", "included_classes": "weak_only_review"},
                ]
            ),
        },
    )
    shutil.copy2(job_candidates_path, latest_job_candidates_path)

    job_panel_path = panel_dir / f"i_system_upgrade_job_city_year_panel_template_{run_id}.xlsx"
    latest_job_panel_path = project_root / "data/panel/i_system_upgrade/latest_i_system_upgrade_job_city_year_panel_template.xlsx"
    write_excel(
        job_panel_path,
        {
            "job_city_year_panel": pd.DataFrame(columns=JOB_PANEL_COLUMNS),
            "field_dictionary": build_field_dictionary(JOB_PANEL_COLUMNS, "job_city_year_panel"),
            "status_reference": pd.DataFrame(
                {
                    "data_status": [
                        "pending_collection",
                        "partially_collected",
                        "verified",
                        "insufficient_evidence",
                        "manual_review_required",
                    ],
                    "description": [
                        "尚未开始采集。",
                        "已有部分候选记录，尚未完整核验。",
                        "候选记录已完成来源、年份、城市归属复核。",
                        "历史证据不足，不应填入有效岗位数。",
                        "弱关键词或边界岗位需人工复核。",
                    ],
                }
            ),
        },
    )
    shutil.copy2(job_panel_path, latest_job_panel_path)

    recheck_plan_path = audit_dir / f"i_system_upgrade_quanzhou_2019_2020_recheck_plan_{run_id}.md"
    latest_recheck_plan_path = project_root / "data/audit/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_recheck_plan.md"
    write_recheck_plan(recheck_plan_path, run_id)
    shutil.copy2(recheck_plan_path, latest_recheck_plan_path)

    actual_job_assets = inventory_df[
        (inventory_df["contains_job_data"] == True)
        & (~inventory_df["file_path"].str.contains("docs/|scripts/|__pycache__|archive/legacy_outputs", regex=True))
    ]
    qz_2019_assets = inventory_df[inventory_df["contains_quanzhou_2019"] == True]
    qz_2020_assets = inventory_df[inventory_df["contains_quanzhou_2020"] == True]
    manual_review = inventory_df[inventory_df["recommended_use"] == "manual_review_required"]

    output_files = [
        inventory_path,
        latest_inventory_path,
        keywords_path,
        job_rules_path,
        indicator_path,
        job_candidates_path,
        latest_job_candidates_path,
        job_panel_path,
        latest_job_panel_path,
        recheck_plan_path,
        latest_recheck_plan_path,
    ]

    if actual_job_assets.empty:
        warnings.append("当前指定目录未发现可直接作为岗位数据的历史招聘明细文件；仅发现岗位/技能方法线索或本轮模板。")
    if qz_2019_assets.empty or qz_2020_assets.empty:
        warnings.append("泉州 2019/2020 覆盖主要来自 experimental 面板或报告，尚未发现独立岗位/技能历史数据。")

    next_step = (
        "可以开始泉州 2019、2020 岗位/技能小规模试点采集；"
        "但不建议现在重跑 CCD。先补企业/专利遗漏复核与历史岗位候选采集，形成独立 I_upgrade 面板后再做 CCD 对比。"
    )

    manifest_path = audit_dir / f"i_system_upgrade_manifest_{run_id}.json"
    manifest = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input_search_dirs": SEARCH_DIRS,
        "files_scanned_count": files_scanned_count,
        "i_system_assets_found_count": int(len(inventory_df)),
        "output_files": [p.relative_to(project_root).as_posix() for p in output_files + [manifest_path]],
        "warnings": warnings,
        "legacy_used_as_input": False,
        "next_step_recommendation": next_step,
        "current_i_system_has_actual_job_data": bool(not actual_job_assets.empty),
        "quanzhou_2019_assets_found_count": int(len(qz_2019_assets)),
        "quanzhou_2020_assets_found_count": int(len(qz_2020_assets)),
        "manual_review_required_files_count": int(len(manual_review)),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "run_id": run_id,
        "files_scanned_count": files_scanned_count,
        "i_system_assets_found_count": int(len(inventory_df)),
        "actual_job_assets_count": int(len(actual_job_assets)),
        "quanzhou_2019_assets_found_count": int(len(qz_2019_assets)),
        "quanzhou_2020_assets_found_count": int(len(qz_2020_assets)),
        "manual_review_required_files_count": int(len(manual_review)),
        "manual_review_files": manual_review["file_path"].head(30).tolist() if not manual_review.empty else [],
        "warnings": warnings,
        "legacy_used_as_input": False,
        "next_step_recommendation": next_step,
        "output_files": [p.relative_to(project_root).as_posix() for p in output_files + [manifest_path]],
    }


def main() -> None:
    args = parse_args()
    project_root = Path.cwd()
    run_id = args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    result = create_outputs(project_root, run_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
