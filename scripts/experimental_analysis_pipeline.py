from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

os.environ.setdefault("MPLCONFIGDIR", str(Path("work/matplotlib-cache").resolve()))

try:
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import font_manager
    import matplotlib.pyplot as plt
    import seaborn as sns
except ImportError:
    font_manager = None
    plt = None
    sns = None

try:
    import statsmodels.api as sm
except ImportError:
    sm = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_NAME = "当前数据与CCD实验性分析整理_20260604.xlsx"
SAMPLE_CITIES = ["福州", "厦门", "泉州"]
SAMPLE_YEARS = list(range(2019, 2025))
EXPECTED_CITY_PATHS = {
    "福州": "稳定提升型",
    "厦门": "跃迁协调型",
    "泉州": "低位波动型",
}

PRECONDITION_FILES = [
    "docs/codex/experimental_analysis_automation.md",
    "docs/codex/output_versioning_rules.md",
    "archive/legacy_outputs/README.md",
    "archive/legacy_outputs/legacy_outputs_inventory.xlsx",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run run_id based experimental CCD analysis.")
    parser.add_argument("--input", default=INPUT_NAME, help="Input experimental CCD workbook.")
    parser.add_argument(
        "--no-update-latest",
        action="store_true",
        help="Generate a run_id archive but do not overwrite latest entry files.",
    )
    return parser.parse_args()


def add_chinese_font() -> None:
    if plt is None:
        return
    if sns is not None:
        sns.set_theme(style="whitegrid")

    font_candidates = [
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]
    selected = None
    if font_manager is not None:
        for font_path in font_candidates:
            try:
                if Path(font_path).exists():
                    font_manager.fontManager.addfont(font_path)
                    selected = font_manager.FontProperties(fname=font_path).get_name()
                    break
            except Exception:
                continue
    plt.rcParams["font.sans-serif"] = [
        *( [selected] if selected else [] ),
        "Microsoft YaHei",
        "SimHei",
        "Arial Unicode MS",
        "PingFang SC",
        "Hiragino Sans GB",
    ]
    plt.rcParams["axes.unicode_minus"] = False


def precondition_status() -> tuple[list[dict], list[str]]:
    rows = []
    warnings = []
    for rel_path in PRECONDITION_FILES:
        exists = (PROJECT_ROOT / rel_path).exists()
        rows.append({"path": rel_path, "exists": exists})
        if not exists:
            warnings.append(f"前置文件缺失：{rel_path}")
    return rows, warnings


def resolve_input(input_arg: str, warnings: list[str]) -> Path:
    raw = Path(input_arg)
    candidates = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.extend(
            [
                PROJECT_ROOT / raw,
                PROJECT_ROOT / "data" / raw,
                PROJECT_ROOT / "data" / "raw" / raw,
                PROJECT_ROOT / "data" / "interim" / raw,
                PROJECT_ROOT / "data" / "panel" / raw,
                PROJECT_ROOT / "data" / "audit" / raw,
                Path.cwd() / raw,
                Path.home() / "Desktop" / "finacial system and educational system CCD" / raw.name,
            ]
        )

    for candidate in candidates:
        if candidate.exists():
            resolved = candidate.resolve()
            if "archive/legacy_outputs" in str(resolved):
                raise ValueError(f"禁止从 legacy 目录读取输入：{resolved}")
            if not str(resolved).startswith(str(PROJECT_ROOT.resolve())):
                warnings.append(f"输入文件不在项目目录内，已使用外部原始数据路径：{resolved}")
            return resolved

    search_roots = [
        PROJECT_ROOT,
        PROJECT_ROOT / "data",
        PROJECT_ROOT / "data" / "raw",
        PROJECT_ROOT / "data" / "interim",
        PROJECT_ROOT / "data" / "panel",
        PROJECT_ROOT / "data" / "audit",
    ]
    for root in search_roots:
        if not root.exists():
            continue
        for candidate in root.rglob(raw.name):
            resolved = candidate.resolve()
            if "archive/legacy_outputs" not in str(resolved):
                return resolved

    raise FileNotFoundError(f"找不到输入文件：{input_arg}")


def find_column(df: pd.DataFrame, preferred: str, candidates: Iterable[str]) -> str:
    columns = list(df.columns)
    if preferred in columns:
        return preferred
    normalized = {str(col).replace(" ", "").strip().lower(): col for col in columns}
    for name in [preferred, *candidates]:
        key = str(name).replace(" ", "").strip().lower()
        if key in normalized:
            return normalized[key]
    raise ValueError(f"找不到字段 {preferred}。当前字段：{columns}")


def read_sheet(excel_file: pd.ExcelFile, preferred: str, keywords: list[str]) -> pd.DataFrame:
    if preferred in excel_file.sheet_names:
        return pd.read_excel(excel_file, sheet_name=preferred)
    for sheet in excel_file.sheet_names:
        if all(keyword in sheet for keyword in keywords):
            return pd.read_excel(excel_file, sheet_name=sheet)
    raise ValueError(f"找不到 Sheet：{preferred}")


def join_unique(values: Iterable[object], sep: str = "、") -> str:
    out = []
    for value in values:
        if pd.isna(value):
            continue
        text = str(value).strip()
        if text and text not in out:
            out.append(text)
    return sep.join(out)


def split_join_unique(values: Iterable[object], sep: str = "、") -> str:
    out = []
    for value in values:
        if pd.isna(value):
            continue
        for part in re.split(r"[、,，;；]+", str(value)):
            text = part.strip()
            if text and text not in out:
                out.append(text)
    return sep.join(out)


def aggregate_school_detail(i_input: pd.DataFrame, city_col: str, year_col: str) -> pd.DataFrame:
    rows = []
    for (city, year), group in i_input.groupby([city_col, year_col], dropna=False):
        row = {city_col: city, year_col: year}
        if "学校标准名" in group.columns:
            row["school_detail_school_count"] = group["学校标准名"].dropna().astype(str).str.strip().nunique()
            row["school_names_standardized"] = join_unique(group["学校标准名"])
        if "命中专业种类数" in group.columns:
            row["school_detail_major_type_count_sum"] = pd.to_numeric(group["命中专业种类数"], errors="coerce").sum()
        if "命中专业" in group.columns:
            majors = split_join_unique(group["命中专业"])
            row["school_detail_majors_combined"] = majors
            row["school_detail_unique_major_count"] = len([x for x in majors.split("、") if x])
        for col in ["候选明细行数", "来源文件数"]:
            if col in group.columns:
                row[f"school_detail_{col}_sum"] = pd.to_numeric(group[col], errors="coerce").sum()
        rows.append(row)
    return pd.DataFrame(rows)


def prepare_data(input_path: Path) -> tuple[pd.ExcelFile, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    excel_file = pd.ExcelFile(input_path)
    e_input = read_sheet(excel_file, "02_E端城市年份输入", ["E", "城市"])
    i_input = read_sheet(excel_file, "03_E端学校年份汇总", ["学校", "汇总"])
    ccd_results = read_sheet(excel_file, "07_CCD结果总表", ["CCD", "结果"])

    city_col = find_column(ccd_results, "city", ["城市", "地区", "地市"])
    year_col = find_column(ccd_results, "year", ["年份", "年度"])
    e_city = find_column(e_input, "city", [city_col, "城市", "地区", "地市"])
    e_year = find_column(e_input, "year", [year_col, "年份", "年度"])
    i_city = find_column(i_input, "city", [city_col, "城市", "地区", "地市"])
    i_year = find_column(i_input, "year", [year_col, "年份", "年度"])

    e_input = e_input.rename(columns={e_city: city_col, e_year: year_col})
    i_input = i_input.rename(columns={i_city: city_col, i_year: year_col})

    ccd_results[year_col] = pd.to_numeric(ccd_results[year_col], errors="coerce").astype("Int64")
    e_input[year_col] = pd.to_numeric(e_input[year_col], errors="coerce").astype("Int64")
    i_input[year_col] = pd.to_numeric(i_input[year_col], errors="coerce").astype("Int64")

    sample_ccd = ccd_results[
        ccd_results[city_col].isin(SAMPLE_CITIES) & ccd_results[year_col].isin(SAMPLE_YEARS)
    ].copy()
    sample_e = e_input[e_input[city_col].isin(SAMPLE_CITIES) & e_input[year_col].isin(SAMPLE_YEARS)].copy()
    sample_i = i_input[i_input[city_col].isin(SAMPLE_CITIES) & i_input[year_col].isin(SAMPLE_YEARS)].copy()

    school_summary = aggregate_school_detail(sample_i, city_col, year_col)
    base_panel = sample_ccd.merge(sample_e, on=[city_col, year_col], how="left", suffixes=("", "_E_city"))
    base_panel = base_panel.merge(school_summary, on=[city_col, year_col], how="left")
    base_panel = base_panel.sort_values([city_col, year_col]).reset_index(drop=True)

    meta = {"city_col": city_col, "year_col": year_col}
    return excel_file, e_input, i_input, ccd_results, base_panel, meta


def make_run_dirs(run_id: str) -> dict[str, Path]:
    dirs = {
        "audit": PROJECT_ROOT / "data" / "audit" / "experimental_analysis" / run_id,
        "panel": PROJECT_ROOT / "data" / "panel" / "experimental_analysis" / run_id,
        "figures": PROJECT_ROOT / "outputs" / "figures" / "experimental_analysis" / run_id,
        "tables": PROJECT_ROOT / "outputs" / "tables" / "experimental_analysis" / run_id,
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def write_data_assets_check(
    path: Path,
    excel_file: pd.ExcelFile,
    e_input: pd.DataFrame,
    i_input: pd.DataFrame,
    ccd_results: pd.DataFrame,
    preconditions: list[dict],
    warnings: list[str],
    input_path: Path,
) -> None:
    sheet_rows = []
    for sheet in excel_file.sheet_names:
        df = pd.read_excel(excel_file, sheet_name=sheet)
        sheet_rows.append(
            {
                "sheet_name": sheet,
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": " | ".join(map(str, df.columns)),
                "missing_cells": int(df.isna().sum().sum()),
            }
        )
    input_rows = [{"input_path": str(input_path), "used_as_analysis_input": True, "is_legacy_path": False}]
    core_rows = [
        {"dataset": "E端城市年份输入", "rows": len(e_input), "missing_cells": int(e_input.isna().sum().sum())},
        {"dataset": "E端学校年份汇总", "rows": len(i_input), "missing_cells": int(i_input.isna().sum().sum())},
        {"dataset": "CCD结果总表", "rows": len(ccd_results), "missing_cells": int(ccd_results.isna().sum().sum())},
    ]
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(sheet_rows).to_excel(writer, sheet_name="workbook_sheets", index=False)
        pd.DataFrame(core_rows).to_excel(writer, sheet_name="core_assets", index=False)
        pd.DataFrame(preconditions).to_excel(writer, sheet_name="preconditions", index=False)
        pd.DataFrame({"warning": warnings or ["无"]}).to_excel(writer, sheet_name="warnings", index=False)
        pd.DataFrame(input_rows).to_excel(writer, sheet_name="input_file", index=False)


def requested_checks(base_panel: pd.DataFrame, ccd_results: pd.DataFrame, input_path: Path, meta: dict) -> tuple[pd.DataFrame, pd.DataFrame, list[str], list[str]]:
    city_col = meta["city_col"]
    year_col = meta["year_col"]
    checks = []
    anomalies = []

    def row_for(city: str, year: int) -> pd.Series | None:
        matched = base_panel[(base_panel[city_col].eq(city)) & (base_panel[year_col].eq(year))]
        if matched.empty:
            return None
        return matched.iloc[0]

    xiamen_2022 = row_for("厦门", 2022)
    xiamen_missing_e = bool(xiamen_2022 is None or pd.isna(xiamen_2022.get("E_index")))
    checks.append({"check_item": "厦门 2022 是否 missing_E", "result": xiamen_missing_e, "details": "E_index 缺失" if xiamen_missing_e else "E_index 非缺失"})
    if xiamen_missing_e:
        anomalies.append("厦门 2022：missing_E")

    for city, year in [("泉州", 2019), ("泉州", 2020)]:
        row = row_for(city, year)
        is_zero = bool(row is not None and pd.notna(row.get("I_index")) and float(row.get("I_index")) == 0)
        checks.append({"check_item": f"{city} {year} 是否 I_index=0", "result": is_zero, "details": f"I_index={None if row is None else row.get('I_index')}"})
        if is_zero:
            anomalies.append(f"{city} {year}：I_index=0")

    d_zero_rows = base_panel[pd.to_numeric(base_panel["D"], errors="coerce").eq(0)].copy()
    missing_fill_zero = False
    d_zero_details = []
    for _, row in d_zero_rows.iterrows():
        has_missing = pd.isna(row.get("E_index")) or pd.isna(row.get("I_index"))
        missing_fill_zero = missing_fill_zero or has_missing
        d_zero_details.append(f"{row[city_col]}-{row[year_col]}: E={row.get('E_index')}, I={row.get('I_index')}, D={row.get('D')}, has_missing={has_missing}")
    checks.append({"check_item": "D=0 是否由 missing 填 0 导致", "result": missing_fill_zero, "details": "；".join(d_zero_details) or "无 D=0 样本"})

    has_2025 = bool((ccd_results[year_col] == 2025).any())
    checks.append({"check_item": "是否有 2025 混入主样本", "result": has_2025, "details": "主样本已限定 2019-2024"})

    non_sample_cities = sorted(set(ccd_results[city_col].dropna()) - set(SAMPLE_CITIES))
    mixed_non_sample = bool(non_sample_cities)
    checks.append({"check_item": "是否有非福州/厦门/泉州城市混入当前小样本", "result": mixed_non_sample, "details": "原始 CCD 表其他城市：" + "、".join(non_sample_cities) if non_sample_cities else "无"})

    legacy_used = "archive/legacy_outputs" in str(input_path)
    checks.append({"check_item": "是否有 legacy 文件被误用", "result": legacy_used, "details": str(input_path)})
    checks.append({"check_item": "是否生成 latest 入口", "result": True, "details": "脚本将在写出结果后更新 latest 面板和 latest 报告"})
    checks.append({"check_item": "是否生成 manifest", "result": True, "details": "脚本将在 run_id audit 目录生成 manifest"})

    missing_rows = base_panel[base_panel[["E_index", "I_index", "D"]].isna().any(axis=1)].copy()
    return pd.DataFrame(checks), missing_rows, anomalies, d_zero_details


def write_missing_outlier_check(path: Path, base_panel: pd.DataFrame, checks_df: pd.DataFrame, missing_rows: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = [col for col in ["E_index", "I_index", "E_minus_I", "D"] if col in base_panel.columns]
    outlier_rows = []
    for _, row in base_panel.iterrows():
        notes = []
        for col in numeric_cols:
            value = pd.to_numeric(row.get(col), errors="coerce")
            if pd.isna(value):
                notes.append(f"{col}=missing")
            elif value < 0 or value > 1:
                notes.append(f"{col}=outside_0_1")
            elif value == 0:
                notes.append(f"{col}=0")
        if notes:
            item = row.to_dict()
            item["outlier_notes"] = "；".join(notes)
            outlier_rows.append(item)
    outlier_df = pd.DataFrame(outlier_rows)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        checks_df.to_excel(writer, sheet_name="required_checks", index=False)
        missing_rows.to_excel(writer, sheet_name="missing_samples", index=False)
        outlier_df.to_excel(writer, sheet_name="outlier_candidates", index=False)
        base_panel.isna().sum().reset_index(name="missing_count").rename(columns={"index": "column"}).to_excel(writer, sheet_name="missing_by_column", index=False)
    return outlier_df


def save_base_panel(path: Path, base_panel: pd.DataFrame) -> None:
    base_panel.to_csv(path, index=False, encoding="utf-8-sig")


def plot_d_trend(base_panel: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    for city, group in base_panel.sort_values("year").groupby("city"):
        ax.plot(group["year"], group["D"], marker="o", linewidth=2, label=city)
    ax.set_title("Experimental CCD D Trend by City")
    ax.set_xlabel("Year")
    ax.set_ylabel("CCD D")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def plot_heatmap(base_panel: pd.DataFrame, path: Path) -> None:
    pivot = base_panel.pivot_table(index="city", columns="year", values="D", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.heatmap(pivot, annot=True, fmt=".3f", cmap="coolwarm", linewidths=0.4, ax=ax)
    ax.set_title("Experimental CCD Heatmap: City x Year")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def plot_e_i_trend(base_panel: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 6))
    for city, group in base_panel.sort_values("year").groupby("city"):
        ax.plot(group["year"], group["E_index"], marker="o", linewidth=2, label=f"{city} E")
        ax.plot(group["year"], group["I_index"], marker="s", linestyle="--", linewidth=2, label=f"{city} I")
    ax.set_title("Experimental E and I Index Trend by City")
    ax.set_xlabel("Year")
    ax.set_ylabel("Index")
    ax.legend(ncol=2, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def plot_e_vs_i(base_panel: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))
    plot_df = base_panel.dropna(subset=["E_index", "I_index"]).copy()
    for city, group in plot_df.groupby("city"):
        ax.scatter(group["E_index"], group["I_index"], s=70, label=city)
        for _, row in group.iterrows():
            ax.annotate(str(int(row["year"])), (row["E_index"], row["I_index"]), fontsize=8, xytext=(4, 4), textcoords="offset points")
    ax.set_title("Experimental E vs I Scatter")
    ax.set_xlabel("E_index")
    ax.set_ylabel("I_index")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def write_figures(base_panel: pd.DataFrame, dirs: dict[str, Path], run_id: str) -> list[Path]:
    outputs = [
        dirs["figures"] / f"experimental_CCD_D_trend_by_city_{run_id}.png",
        dirs["figures"] / f"experimental_CCD_heatmap_city_year_{run_id}.png",
        dirs["figures"] / f"experimental_E_I_index_trend_by_city_{run_id}.png",
        dirs["figures"] / f"experimental_E_vs_I_scatter_{run_id}.png",
    ]
    if plt is None or sns is None:
        raise RuntimeError("缺少 matplotlib/seaborn，无法生成本次要求的四张图。")
    plot_d_trend(base_panel, outputs[0])
    plot_heatmap(base_panel, outputs[1])
    plot_e_i_trend(base_panel, outputs[2])
    plot_e_vs_i(base_panel, outputs[3])
    return outputs


def write_descriptive_statistics(base_panel: pd.DataFrame, path: Path) -> None:
    numeric_cols = [col for col in ["E_index", "I_index", "E_minus_I", "D"] if col in base_panel.columns]
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        base_panel[numeric_cols].describe().to_excel(writer, sheet_name="overall")
        base_panel.groupby("city")[numeric_cols].agg(["count", "mean", "std", "min", "max"]).to_excel(writer, sheet_name="by_city")
        base_panel.groupby("year")[numeric_cols].agg(["count", "mean", "std", "min", "max"]).to_excel(writer, sheet_name="by_year")
        if "CCD_level" in base_panel.columns:
            base_panel["CCD_level"].value_counts(dropna=False).reset_index(name="count").to_excel(writer, sheet_name="CCD_level_counts", index=False)


def write_regression_panel(base_panel: pd.DataFrame, path: Path) -> pd.DataFrame:
    reg_panel = base_panel.copy()
    reg_panel["is_regression_usable"] = reg_panel[["D", "E_index", "I_index"]].notna().all(axis=1)
    reg_panel["analysis_scope"] = "experimental_validation_only"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        reg_panel.to_excel(writer, sheet_name="regression_panel", index=False)
        reg_panel[~reg_panel["is_regression_usable"]].to_excel(writer, sheet_name="excluded_missing", index=False)
    return reg_panel


def run_regressions(reg_panel: pd.DataFrame, path: Path) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    usable = reg_panel[reg_panel["is_regression_usable"]].copy()
    for col in ["D", "E_index", "I_index", "E_minus_I"]:
        if col in usable.columns:
            usable[col] = pd.to_numeric(usable[col], errors="coerce")
    usable = usable.dropna(subset=["D", "E_index", "I_index"])
    n = len(usable)
    models = []
    coefficients = []
    if sm is None:
        model_summary = pd.DataFrame([{"model": "not_run", "warning": "statsmodels unavailable"}])
        coeff_df = pd.DataFrame()
    else:
        specs = [
            ("D_on_E_I", ["E_index", "I_index"]),
            ("D_on_E_I_gap", ["E_index", "I_index", "E_minus_I"]),
        ]
        for model_name, x_cols in specs:
            model_df = usable.dropna(subset=x_cols + ["D"]).copy()
            if len(model_df) < max(5, len(x_cols) + 2):
                models.append({"model": model_name, "nobs": len(model_df), "status": "skipped_small_sample"})
                continue
            x = sm.add_constant(model_df[x_cols])
            y = model_df["D"]
            result = sm.OLS(y, x).fit()
            models.append(
                {
                    "model": model_name,
                    "nobs": int(result.nobs),
                    "r_squared": result.rsquared,
                    "adj_r_squared": result.rsquared_adj,
                    "f_pvalue": result.f_pvalue,
                    "aic": result.aic,
                    "bic": result.bic,
                    "status": "experimental_validation_only",
                }
            )
            for variable in result.params.index:
                coefficients.append(
                    {
                        "model": model_name,
                        "variable": variable,
                        "coef": result.params[variable],
                        "std_err": result.bse[variable],
                        "t_value": result.tvalues[variable],
                        "p_value": result.pvalues[variable],
                    }
                )
    model_summary = pd.DataFrame(models)
    coeff_df = pd.DataFrame(coefficients)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        usable.to_excel(writer, sheet_name="regression_usable_samples", index=False)
        model_summary.to_excel(writer, sheet_name="model_summary", index=False)
        coeff_df.to_excel(writer, sheet_name="coefficients", index=False)
        pd.DataFrame(
            [
                {
                    "note": "当前样本为三市小样本，所有回归结果仅用于 experimental validation，不得作为正式论文因果结论。",
                    "if_n_less_than_15": "如果有效样本量小于 15，只做描述性回归，不强调显著性。",
                    "actual_usable_n": n,
                }
            ]
        ).to_excel(writer, sheet_name="method_notes", index=False)
    return model_summary, coeff_df, n


def classify_city_path(city: str, group: pd.DataFrame) -> tuple[str, str]:
    d = pd.to_numeric(group.sort_values("year")["D"], errors="coerce")
    valid = d.dropna()
    missing_count = int(d.isna().sum())
    if valid.empty:
        return "无法分类", "D 全部缺失"
    first, last = valid.iloc[0], valid.iloc[-1]
    mean, max_value, min_value = valid.mean(), valid.max(), valid.min()
    if mean < 0.45 and max_value < 0.65:
        return "低位波动型", f"D均值={mean:.3f}, 最大值={max_value:.3f}"
    if missing_count > 0 and max_value >= 0.8:
        return "跃迁协调型", f"存在缺失年份，且最高D={max_value:.3f}"
    if last > first and mean >= 0.55:
        return "稳定提升型", f"首年D={first:.3f}, 末年D={last:.3f}, 均值={mean:.3f}"
    if max_value - min_value > 0.35:
        return "跃迁协调型", f"D波动幅度={max_value - min_value:.3f}"
    return "波动调整型", f"D均值={mean:.3f}, 首末变化={last - first:.3f}"


def write_heterogeneity(base_panel: pd.DataFrame, path: Path) -> pd.DataFrame:
    city_mean = base_panel.groupby("city")[["E_index", "I_index", "D"]].mean(numeric_only=True).reset_index()
    year_mean = base_panel.groupby("year")[["E_index", "I_index", "D"]].mean(numeric_only=True).reset_index()
    path_rows = []
    for city, group in base_panel.groupby("city"):
        auto, reason = classify_city_path(city, group)
        expected = EXPECTED_CITY_PATHS.get(city, "未设定")
        path_rows.append(
            {
                "city": city,
                "auto_path_classification": auto,
                "expected_path_classification": expected,
                "match_expected": auto == expected,
                "reason": reason,
            }
        )
    path_df = pd.DataFrame(path_rows)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        city_mean.to_excel(writer, sheet_name="city_mean", index=False)
        year_mean.to_excel(writer, sheet_name="year_mean", index=False)
        path_df.to_excel(writer, sheet_name="city_path_classification", index=False)
    return path_df


def markdown_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df.empty:
        return "无"
    view = df.head(max_rows).copy()
    view = view.fillna("")
    headers = [str(col) for col in view.columns]
    rows = view.astype(str).values.tolist()
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        escaped = [cell.replace("\n", " ").replace("|", "\\|") for cell in row]
        lines.append("| " + " | ".join(escaped) + " |")
    if len(df) > max_rows:
        lines.append(f"\n仅显示前 {max_rows} 行，共 {len(df)} 行。")
    return "\n".join(lines)


def write_regression_report(path: Path, run_id: str, model_summary: pd.DataFrame, coeff_df: pd.DataFrame, usable_n: int) -> None:
    content = [
        f"# Experimental Regression Report - {run_id}",
        "",
        "本报告仅用于 experimental validation。当前样本为福州、厦门、泉州三市小样本，所有回归结果不得作为正式论文因果结论。",
        "",
        f"可用于回归的样本数量：{usable_n}",
        "",
    ]
    if usable_n < 15:
        content.append("有效样本量小于 15，因此只做描述性回归，不强调显著性。")
        content.append("")
    content.extend(["## Model Summary", "", markdown_table(model_summary), "", "## Coefficients", "", markdown_table(coeff_df)])
    path.write_text("\n".join(content), encoding="utf-8")


def write_summary_report(
    path: Path,
    run_id: str,
    input_path: Path,
    warnings: list[str],
    base_panel: pd.DataFrame,
    reg_usable_n: int,
    missing_rows: pd.DataFrame,
    outlier_df: pd.DataFrame,
    checks_df: pd.DataFrame,
    path_df: pd.DataFrame,
    output_files: list[Path],
) -> None:
    content = [
        f"# Experimental CCD Analysis Summary - {run_id}",
        "",
        "本次分析基于当前已有实验性 CCD Excel 数据运行，未重新采集数据，未使用 legacy 文件作为输入。",
        "",
        "## Warning",
        "",
        *(warnings or ["无"]),
        "",
        "## Input",
        "",
        f"- 输入文件：`{input_path}`",
        "- 输入来源不是 `archive/legacy_outputs/`。",
        "",
        "## Scope",
        "",
        "- 城市：福州、厦门、泉州",
        "- 年份：2019-2024",
        f"- 样本数量：{len(base_panel)}",
        f"- 可用于回归样本数量：{reg_usable_n}",
        "",
        "## Missing Samples",
        "",
        markdown_table(missing_rows[["city", "year", "E_index", "I_index", "D"]] if not missing_rows.empty else missing_rows),
        "",
        "## Required Checks",
        "",
        markdown_table(checks_df),
        "",
        "## Outlier Candidates",
        "",
        markdown_table(outlier_df[["city", "year", "E_index", "I_index", "D", "outlier_notes"]] if not outlier_df.empty else outlier_df),
        "",
        "## City Path Classification",
        "",
        markdown_table(path_df),
        "",
        "## Regression Interpretation Notice",
        "",
        "当前样本为三市小样本，所有回归结果仅用于 experimental validation，不得作为正式论文因果结论。",
        "",
        "## Generated Files",
        "",
        *[f"- `{file}`" for file in output_files],
    ]
    path.write_text("\n".join(content), encoding="utf-8")


def write_manifest(
    path: Path,
    run_id: str,
    input_path: Path,
    warnings: list[str],
    output_files: list[Path],
    checks_df: pd.DataFrame,
    sample_count: int,
    reg_usable_n: int,
    latest_updated: bool,
) -> None:
    manifest = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input_files": [str(input_path)],
        "legacy_input_used": "archive/legacy_outputs" in str(input_path),
        "output_files": [str(path) for path in output_files],
        "sample_range": {"cities": SAMPLE_CITIES, "years": [min(SAMPLE_YEARS), max(SAMPLE_YEARS)]},
        "sample_count": sample_count,
        "regression_usable_sample_count": reg_usable_n,
        "script": str((PROJECT_ROOT / "scripts" / "experimental_analysis_pipeline.py").resolve()),
        "parameters": {"missing_fill_zero": False, "data_collection": False, "sample_years": SAMPLE_YEARS},
        "latest_updated": latest_updated,
        "warnings": warnings,
        "required_checks": checks_df.to_dict(orient="records"),
        "notes": [
            "latest 文件仅作为最近一次结果便捷入口，不作为唯一归档。",
            "回归仅用于 experimental validation，不得作为正式因果结论。",
        ],
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    add_chinese_font()
    preconditions, warnings = precondition_status()

    try:
        input_path = resolve_input(args.input, warnings)
        dirs = make_run_dirs(run_id)
        excel_file, e_input, i_input, ccd_results, base_panel, meta = prepare_data(input_path)

        output_files: list[Path] = []
        data_assets_path = dirs["audit"] / f"experimental_data_assets_check_{run_id}.xlsx"
        write_data_assets_check(data_assets_path, excel_file, e_input, i_input, ccd_results, preconditions, warnings, input_path)
        output_files.append(data_assets_path)

        base_panel_path = dirs["panel"] / f"experimental_analysis_base_panel_2019_2024_{run_id}.csv"
        save_base_panel(base_panel_path, base_panel)
        output_files.append(base_panel_path)

        checks_df, missing_rows, anomalies, d_zero_details = requested_checks(base_panel, ccd_results, input_path, meta)
        missing_check_path = dirs["audit"] / f"experimental_missing_and_outlier_check_{run_id}.xlsx"
        outlier_df = write_missing_outlier_check(missing_check_path, base_panel, checks_df, missing_rows)
        output_files.append(missing_check_path)

        output_files.extend(write_figures(base_panel, dirs, run_id))

        desc_path = dirs["tables"] / f"experimental_descriptive_statistics_{run_id}.xlsx"
        write_descriptive_statistics(base_panel, desc_path)
        output_files.append(desc_path)

        reg_panel_path = dirs["tables"] / f"experimental_regression_panel_{run_id}.xlsx"
        reg_panel = write_regression_panel(base_panel, reg_panel_path)
        output_files.append(reg_panel_path)

        reg_results_path = dirs["tables"] / f"experimental_regression_results_{run_id}.xlsx"
        model_summary, coeff_df, reg_usable_n = run_regressions(reg_panel, reg_results_path)
        output_files.append(reg_results_path)

        reg_report_path = dirs["audit"] / f"experimental_regression_report_{run_id}.md"
        write_regression_report(reg_report_path, run_id, model_summary, coeff_df, reg_usable_n)
        output_files.append(reg_report_path)

        heterogeneity_path = dirs["tables"] / f"experimental_heterogeneity_analysis_{run_id}.xlsx"
        path_df = write_heterogeneity(base_panel, heterogeneity_path)
        output_files.append(heterogeneity_path)

        summary_path = dirs["audit"] / f"experimental_analysis_summary_report_{run_id}.md"
        write_summary_report(summary_path, run_id, input_path, warnings, base_panel, reg_usable_n, missing_rows, outlier_df, checks_df, path_df, output_files)
        output_files.append(summary_path)

        latest_panel = PROJECT_ROOT / "data" / "panel" / "experimental_analysis" / "latest_experimental_analysis_base_panel_2019_2024.csv"
        latest_report = PROJECT_ROOT / "data" / "audit" / "experimental_analysis" / "latest_experimental_analysis_summary_report.md"
        latest_updated = not args.no_update_latest
        if latest_updated:
            shutil.copy2(base_panel_path, latest_panel)
            shutil.copy2(summary_path, latest_report)
            output_files.extend([latest_panel, latest_report])

        manifest_path = dirs["audit"] / f"experimental_run_manifest_{run_id}.json"
        output_files.append(manifest_path)
        write_manifest(
            manifest_path,
            run_id,
            input_path,
            warnings,
            output_files,
            checks_df,
            len(base_panel),
            reg_usable_n,
            latest_updated,
        )

        print(json.dumps(
            {
                "run_id": run_id,
                "input": str(input_path),
                "sample_count": len(base_panel),
                "regression_usable_sample_count": reg_usable_n,
                "missing_samples": missing_rows[["city", "year"]].to_dict(orient="records") if not missing_rows.empty else [],
                "anomalies": anomalies,
                "legacy_input_used": False,
                "latest_updated": latest_updated,
                "latest_panel": str(latest_panel),
                "latest_report": str(latest_report),
                "manifest": str(manifest_path),
            },
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    except Exception as exc:
        print(f"experimental analysis failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
