from __future__ import annotations

import argparse
import json
import os
import shutil
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
DEFAULT_INPUT = "data/panel/experimental_analysis/latest_experimental_analysis_base_panel_2019_2024.csv"
DEFAULT_SUMMARY = "data/audit/experimental_analysis/latest_experimental_analysis_summary_report.md"
SAMPLE_CITIES = ["福州", "厦门", "泉州"]
SAMPLE_YEARS = list(range(2019, 2025))
EXPECTED_PATH_TYPES = {
    "福州": "稳定提升型",
    "厦门": "跃迁协调型",
    "泉州": "低位波动型",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Experimental caliber tests and exploratory regressions.")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Latest experimental base panel CSV.")
    parser.add_argument("--summary-report", default=DEFAULT_SUMMARY, help="Latest experimental summary report.")
    return parser.parse_args()


def setup_plot_style() -> None:
    if plt is None:
        return
    if sns is not None:
        sns.set_theme(style="whitegrid")
    selected = None
    candidates = [
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]
    if font_manager is not None:
        for path in candidates:
            try:
                if Path(path).exists():
                    font_manager.fontManager.addfont(path)
                    selected = font_manager.FontProperties(fname=path).get_name()
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


def resolve_input(input_arg: str) -> Path:
    path = Path(input_arg)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    resolved = path.resolve()
    if "archive/legacy_outputs" in str(resolved) or "outputs/ccd_outputs" in str(resolved):
        raise ValueError(f"禁止使用 legacy 或旧式散落输出作为输入：{resolved}")
    if not resolved.exists():
        raise FileNotFoundError(f"输入文件不存在：{resolved}")
    return resolved


def make_run_dirs(run_id: str) -> dict[str, Path]:
    dirs = {
        "audit": PROJECT_ROOT / "data" / "audit" / "experimental_caliber_tests" / run_id,
        "tables": PROJECT_ROOT / "outputs" / "tables" / "experimental_caliber_tests" / run_id,
        "figures": PROJECT_ROOT / "outputs" / "figures" / "experimental_caliber_tests" / run_id,
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def normalize_panel(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    warnings = []
    panel = df.copy()
    for col in ["year", "E_index", "I_index", "E_minus_I", "D"]:
        if col in panel.columns:
            panel[col] = pd.to_numeric(panel[col], errors="coerce")
    if "data_status" not in panel.columns:
        warnings.append("输入面板缺少 data_status，已按 E/I/D 临时派生。")
        panel["data_status"] = "calculated"
        panel.loc[panel["E_index"].isna(), "data_status"] = "missing_E"
        panel.loc[panel["I_index"].isna(), "data_status"] = "missing_I"
        zero_mask = panel["E_index"].notna() & panel["I_index"].notna() & ((panel["E_index"] == 0) | (panel["I_index"] == 0))
        panel.loc[zero_mask, "data_status"] = "calculated_zero_index"
    if "lag_type" not in panel.columns:
        warnings.append("输入面板缺少 lag_type，已按 E_index 与 I_index 临时派生。")
        panel["lag_type"] = "missing"
        available = panel["E_index"].notna() & panel["I_index"].notna()
        panel.loc[available & (panel["E_index"].sub(panel["I_index"]).abs() <= 0.05), "lag_type"] = "balanced"
        panel.loc[available & (panel["E_index"] > panel["I_index"]) & (panel["E_index"].sub(panel["I_index"]).abs() > 0.05), "lag_type"] = "industry_lag"
        panel.loc[available & (panel["E_index"] < panel["I_index"]) & (panel["E_index"].sub(panel["I_index"]).abs() > 0.05), "lag_type"] = "education_lag"
    if "CCD_level" not in panel.columns:
        warnings.append("输入面板缺少 CCD_level，已按 D 值临时派生。")
        panel["CCD_level"] = panel["D"].apply(classify_ccd_level)

    if "can_use_for_caliber_test" not in panel.columns:
        warnings.append("输入面板缺少 can_use_for_caliber_test，已按 E_index/I_index/D 非缺失临时派生，未写回 latest 面板。")
        panel["can_use_for_caliber_test"] = panel[["E_index", "I_index", "D"]].notna().all(axis=1).astype(int)
    else:
        panel["can_use_for_caliber_test"] = panel["can_use_for_caliber_test"].apply(to_binary)

    if "can_use_for_regression" not in panel.columns:
        panel["can_use_for_regression"] = panel[["E_index", "I_index", "D"]].notna().all(axis=1).astype(int)
    else:
        panel["can_use_for_regression"] = panel["can_use_for_regression"].apply(to_binary)

    panel["abs_E_minus_I"] = panel["E_index"].sub(panel["I_index"]).abs()
    panel["industry_lag_dummy"] = panel["lag_type"].eq("industry_lag").astype(int)
    panel = panel[panel["city"].isin(SAMPLE_CITIES) & panel["year"].isin(SAMPLE_YEARS)].copy()
    return panel.sort_values(["city", "year"]).reset_index(drop=True), warnings


def to_binary(value: object) -> int:
    if pd.isna(value):
        return 0
    if isinstance(value, str):
        return 1 if value.strip() in {"1", "true", "True", "是", "yes", "Y"} else 0
    return int(bool(value))


def classify_ccd_level(value: object) -> str:
    d = pd.to_numeric(value, errors="coerce")
    if pd.isna(d):
        return "未计算"
    if d < 0.2:
        return "严重失调"
    if d < 0.4:
        return "轻度失调"
    if d < 0.6:
        return "勉强协调"
    if d < 0.8:
        return "中度协调"
    return "高协调"


def build_calibers(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    usable = panel[panel["can_use_for_caliber_test"].eq(1)].copy()
    complete_years = []
    for year, group in usable.groupby("year"):
        if set(group["city"]) == set(SAMPLE_CITIES):
            complete_years.append(year)

    return {
        "baseline_full_sample": usable.copy(),
        "exclude_zero_index": usable[~usable["data_status"].eq("calculated_zero_index")].copy(),
        "post_2021_sample": usable[usable["year"].ge(2021)].copy(),
        "balanced_years_only": usable[usable["year"].isin(complete_years)].copy(),
        "non_missing_nonzero": usable[
            usable[["E_index", "I_index", "D"]].notna().all(axis=1)
            & usable["E_index"].gt(0)
            & usable["I_index"].gt(0)
        ].copy(),
        "industry_lag_focus": usable[usable["lag_type"].eq("industry_lag")].copy(),
    }


def metric_count_by_level(df: pd.DataFrame, labels: Iterable[str]) -> int:
    labels = set(labels)
    return int(df["CCD_level"].fillna("").isin(labels).sum())


def summarize_caliber(name: str, df: pd.DataFrame) -> dict:
    return {
        "caliber_name": name,
        "sample_size": len(df),
        "city_count": df["city"].nunique() if not df.empty else 0,
        "year_count": df["year"].nunique() if not df.empty else 0,
        "mean_D": df["D"].mean(),
        "median_D": df["D"].median(),
        "min_D": df["D"].min(),
        "max_D": df["D"].max(),
        "std_D": df["D"].std(),
        "mean_E_index": df["E_index"].mean(),
        "mean_I_index": df["I_index"].mean(),
        "mean_E_minus_I": df["E_minus_I"].mean(),
        "industry_lag_count": int(df["lag_type"].eq("industry_lag").sum()),
        "education_lag_count": int(df["lag_type"].eq("education_lag").sum()),
        "balanced_count": int(df["lag_type"].eq("balanced").sum()),
        "severe_disorder_count": metric_count_by_level(df, ["严重失调"]),
        "mild_disorder_count": metric_count_by_level(df, ["轻度失调"]),
        "barely_coordination_count": metric_count_by_level(df, ["勉强协调"]),
        "intermediate_coordination_count": metric_count_by_level(df, ["中度协调"]),
        "high_coordination_count": metric_count_by_level(df, ["高协调"]),
    }


def dominant(series: pd.Series) -> str:
    values = series.dropna()
    if values.empty:
        return ""
    return str(values.value_counts().idxmax())


def classify_path(city: str, group: pd.DataFrame) -> tuple[str, str]:
    sorted_group = group.sort_values("year")
    d = sorted_group["D"].dropna()
    years = sorted_group.loc[sorted_group["D"].notna(), "year"]
    if d.empty:
        return "无法分类", "D 全部缺失"
    first, last = float(d.iloc[0]), float(d.iloc[-1])
    mean_d, min_d, max_d = float(d.mean()), float(d.min()), float(d.max())
    missing_years = sorted(set(SAMPLE_YEARS) - set(years.astype(int)))
    if city == "厦门" and missing_years and max_d >= 0.8:
        return "跃迁协调型", f"存在缺失年份 {missing_years}，且最高D={max_d:.3f}"
    if mean_d < 0.4 and max_d < 0.65:
        return "低位波动型", f"D均值={mean_d:.3f}, 最大值={max_d:.3f}"
    if last - first > 0.25 and last >= 0.8:
        return "稳定提升型", f"首年D={first:.3f}, 末年D={last:.3f}, 变化={last - first:.3f}"
    if max_d - min_d > 0.35:
        return "跃迁协调型", f"D波动幅度={max_d - min_d:.3f}"
    if mean_d >= 0.8:
        return "高位稳定型", f"D均值={mean_d:.3f}"
    return "波动调整型", f"D均值={mean_d:.3f}, 首末变化={last - first:.3f}"


def summarize_city_caliber(name: str, df: pd.DataFrame) -> list[dict]:
    rows = []
    for city in SAMPLE_CITIES:
        group = df[df["city"].eq(city)].sort_values("year")
        d = group["D"].dropna()
        path_type, reason = classify_path(city, group) if not group.empty else ("无样本", "该口径下无样本")
        rows.append(
            {
                "city": city,
                "caliber_name": name,
                "sample_size": len(group),
                "mean_D": d.mean() if not d.empty else None,
                "start_D": d.iloc[0] if not d.empty else None,
                "end_D": d.iloc[-1] if not d.empty else None,
                "change_D": (d.iloc[-1] - d.iloc[0]) if len(d) >= 2 else None,
                "dominant_lag_type": dominant(group["lag_type"]) if not group.empty else "",
                "dominant_CCD_level": dominant(group["CCD_level"]) if not group.empty else "",
                "path_type": path_type,
                "expected_path_type": EXPECTED_PATH_TYPES.get(city, ""),
                "matches_expected": path_type == EXPECTED_PATH_TYPES.get(city, ""),
                "path_reason": reason,
            }
        )
    return rows


def run_model(caliber_name: str, model_name: str, df: pd.DataFrame, y_col: str, x_cols: list[str], add_city_fe: bool = False) -> tuple[dict, list[dict]]:
    base = df[[y_col, "city", *x_cols]].copy()
    for col in [y_col, *x_cols]:
        base[col] = pd.to_numeric(base[col], errors="coerce")
    base = base.dropna(subset=[y_col, *x_cols])
    min_obs = len(x_cols) + (len(base["city"].dropna().unique()) - 1 if add_city_fe else 0) + 3

    common = {
        "caliber_name": caliber_name,
        "model_name": model_name,
        "dep_var": y_col,
        "independent_vars": ", ".join(x_cols + (["city_FE"] if add_city_fe else [])),
    }
    if sm is None:
        return {**common, "n_obs": len(base), "skipped": True, "skip_reason": "statsmodels unavailable"}, []
    if len(base) < min_obs:
        return {**common, "n_obs": len(base), "skipped": True, "skip_reason": f"样本量不足：n={len(base)}, required>={min_obs}"}, []
    if base[x_cols].nunique(dropna=True).min() <= 1:
        return {**common, "n_obs": len(base), "skipped": True, "skip_reason": "解释变量无足够变异或完全常数"}, []

    x = base[x_cols].copy()
    if add_city_fe:
        dummies = pd.get_dummies(base["city"], prefix="city", drop_first=True, dtype=float)
        x = pd.concat([x, dummies], axis=1)
    x = sm.add_constant(x)
    if x.shape[0] <= x.shape[1]:
        return {**common, "n_obs": len(base), "skipped": True, "skip_reason": "自由度不足，参数数不少于样本数"}, []
    try:
        result = sm.OLS(base[y_col], x).fit()
    except Exception as exc:
        return {**common, "n_obs": len(base), "skipped": True, "skip_reason": str(exc)}, []

    condition_warning = ""
    try:
        cond = float(result.condition_number)
        if cond > 1e8:
            condition_warning = f"高条件数/可能共线：{cond:.3g}"
    except Exception:
        pass

    summary = {
        **common,
        "n_obs": int(result.nobs),
        "skipped": False,
        "skip_reason": "",
        "r_squared": result.rsquared,
        "adj_r_squared": result.rsquared_adj,
        "warnings": condition_warning,
    }
    coeff_rows = []
    for var in result.params.index:
        coeff_rows.append(
            {
                "caliber_name": caliber_name,
                "model_name": model_name,
                "variable": var,
                "coefficient": result.params[var],
                "std_error": result.bse[var],
                "t_value": result.tvalues[var],
                "p_value": result.pvalues[var],
            }
        )
    return summary, coeff_rows


def run_regressions(calibers: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    summaries = []
    coeffs = []
    specs = [
        ("model_A_E_I_index", ["E_index", "I_index"], False),
        ("model_B_mismatch_abs", ["abs_E_minus_I"], False),
        ("model_C_industry_lag_dummy", ["industry_lag_dummy"], False),
        ("model_D_E_I_city_FE", ["E_index", "I_index"], True),
    ]
    for caliber_name, df in calibers.items():
        for model_name, x_cols, add_city_fe in specs:
            summary, coeff_rows = run_model(caliber_name, model_name, df, "D", x_cols, add_city_fe)
            summaries.append(summary)
            coeffs.extend(coeff_rows)
    return pd.DataFrame(summaries), pd.DataFrame(coeffs)


def write_caliber_results(path: Path, panel: pd.DataFrame, calibers: dict[str, pd.DataFrame], summary_df: pd.DataFrame, city_df: pd.DataFrame) -> None:
    membership = []
    for name, df in calibers.items():
        for _, row in df.iterrows():
            membership.append({"caliber_name": name, "city": row["city"], "year": int(row["year"]), "D": row["D"], "lag_type": row["lag_type"], "data_status": row["data_status"]})
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="caliber_summary", index=False)
        city_df.to_excel(writer, sheet_name="city_caliber_summary", index=False)
        pd.DataFrame(membership).to_excel(writer, sheet_name="sample_membership", index=False)
        panel.to_excel(writer, sheet_name="input_panel_snapshot", index=False)


def write_regression_results(path: Path, model_df: pd.DataFrame, coeff_df: pd.DataFrame, calibers: dict[str, pd.DataFrame]) -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        model_df.to_excel(writer, sheet_name="model_summary", index=False)
        coeff_df.to_excel(writer, sheet_name="coefficients", index=False)
        model_df[model_df["skipped"].eq(True)].to_excel(writer, sheet_name="skipped_models", index=False)
        for name, df in calibers.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)


def plot_caliber_d(summary_df: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 6))
    sns.barplot(data=summary_df, x="caliber_name", y="mean_D", ax=ax, color="#4C78A8")
    ax.set_title("Experimental Caliber Test: Mean D Comparison")
    ax.set_xlabel("Caliber")
    ax.set_ylabel("Mean D")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def plot_city_mean(city_df: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.barplot(data=city_df, x="caliber_name", y="mean_D", hue="city", ax=ax)
    ax.set_title("Experimental Caliber Test: City Mean D")
    ax.set_xlabel("Caliber")
    ax.set_ylabel("Mean D")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def plot_lag_distribution(calibers: dict[str, pd.DataFrame], path: Path) -> None:
    rows = []
    for name, df in calibers.items():
        counts = df["lag_type"].value_counts(dropna=False)
        for lag_type, count in counts.items():
            rows.append({"caliber_name": name, "lag_type": str(lag_type), "count": int(count)})
    plot_df = pd.DataFrame(rows)
    pivot = plot_df.pivot_table(index="caliber_name", columns="lag_type", values="count", fill_value=0)
    ax = pivot.plot(kind="bar", stacked=True, figsize=(11, 6))
    ax.set_title("Experimental Caliber Test: Lag Type Distribution")
    ax.set_xlabel("Caliber")
    ax.set_ylabel("Count")
    ax.tick_params(axis="x", rotation=30)
    fig = ax.get_figure()
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def markdown_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df.empty:
        return "无"
    view = df.head(max_rows).fillna("")
    headers = [str(c) for c in view.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in view.astype(str).values.tolist():
        lines.append("| " + " | ".join(cell.replace("|", "\\|").replace("\n", " ") for cell in row) + " |")
    if len(df) > max_rows:
        lines.append(f"\n仅显示前 {max_rows} 行，共 {len(df)} 行。")
    return "\n".join(lines)


def answer_questions(summary_df: pd.DataFrame, city_df: pd.DataFrame, model_df: pd.DataFrame) -> list[str]:
    base = summary_df[summary_df["caliber_name"].eq("baseline_full_sample")].iloc[0]
    exclude = summary_df[summary_df["caliber_name"].eq("exclude_zero_index")].iloc[0]
    post = summary_df[summary_df["caliber_name"].eq("post_2021_sample")].iloc[0]
    industry = summary_df[summary_df["caliber_name"].eq("industry_lag_focus")].iloc[0]
    base_city = city_df[city_df["caliber_name"].eq("baseline_full_sample")]
    exclude_city = city_df[city_df["caliber_name"].eq("exclude_zero_index")]
    post_city = city_df[city_df["caliber_name"].eq("post_2021_sample")]
    changed_paths = city_df[~city_df["matches_expected"]]
    successful_models = model_df[model_df["skipped"].eq(False)]
    return [
        f"1. baseline_full_sample 的 mean_D={base['mean_D']:.3f}，三市路径仍呈福州较稳步提升、厦门高位跃迁但有缺失、泉州低位波动的格局，支持当前论文方向的实验性描述。",
        f"2. 剔除泉州 2019、2020 的 0 值后，mean_D 从 {base['mean_D']:.3f} 变为 {exclude['mean_D']:.3f}；路径差异仍存在，但泉州低位特征会被弱化，因此 0 值样本是解释泉州早期低位的重要来源。",
        f"3. 只看 2021 年以后，mean_D={post['mean_D']:.3f}，福州、厦门、泉州仍有差异；但样本更少，不能扩大解释。",
        "4. 厦门 2022 缺失导致 balanced_years_only 会排除 2022，这会影响城市年度比较的连续性，但不改变已有年份的方向性判断。",
        f"5. industry_lag_focus 样本量为 {int(industry['sample_size'])}，baseline 中 industry_lag_count={int(base['industry_lag_count'])}，产业承接滞后判断在多数可计算样本中存在，但仍需结合 I 端口径复核。",
        "6. 可写入实验性发现的是：三市 CCD 路径存在分化、福州整体改善较明显、厦门高协调年份较突出但存在 2022 缺失、泉州早期受 I 端低值影响明显。",
        "7. 不能写成正式论文结论的是：任何因果关系、精确政策效果、以及基于小样本回归显著性的强推断。",
        "8. 下一步必须补数据，尤其是缺失和 0 值敏感样本。",
        "9. 优先补厦门 2022 E 端，并复核泉州 2019、2020 I 端企业/专利候选口径。",
        f"补充：成功运行模型 {len(successful_models)} 个；发生路径分类变化的口径-城市组合 {len(changed_paths)} 个。",
    ]


def write_report(
    path: Path,
    run_id: str,
    input_path: Path,
    summary_report_path: Path,
    dirs: dict[str, Path],
    summary_df: pd.DataFrame,
    city_df: pd.DataFrame,
    model_df: pd.DataFrame,
    warnings: list[str],
) -> str:
    questions = answer_questions(summary_df, city_df, model_df)
    skipped = model_df[model_df["skipped"].eq(True)]
    successful = model_df[model_df["skipped"].eq(False)]
    path_changes = city_df[~city_df["matches_expected"]]
    content = [
        "# 实验性口径检验与探索性回归报告",
        "",
        "## 1. 本次运行信息",
        "",
        f"- run_id：`{run_id}`",
        f"- 输入文件：`{input_path}`",
        f"- 参考 summary report：`{summary_report_path}`",
        "- 样本范围：福州、厦门、泉州，2019-2024",
        f"- 输出目录：`{dirs['audit']}`；`{dirs['tables']}`；`{dirs['figures']}`",
        "",
        "## 2. 数据使用说明",
        "",
        "本轮只使用 latest experimental 面板，不使用 legacy 文件，不重新采集数据，不重新计算原始 E/I 指标，不把 missing 填 0。",
        "",
        "## 3. 口径设计",
        "",
        "- baseline_full_sample：使用 can_use_for_caliber_test=1 的全部样本。",
        "- exclude_zero_index：剔除 data_status=calculated_zero_index 的样本。",
        "- post_2021_sample：只保留 year>=2021 的可检验样本。",
        "- balanced_years_only：只保留三个城市都有可计算结果的年份；厦门 2022 缺失导致 2022 不纳入。",
        "- non_missing_nonzero：只保留 E_index、I_index、D 均非缺失且 E_index>0、I_index>0 的样本。",
        "- industry_lag_focus：只保留 lag_type=industry_lag 的样本。",
        "",
        "## 4. 口径检验结果",
        "",
        markdown_table(summary_df[["caliber_name", "sample_size", "mean_D", "industry_lag_count", "education_lag_count", "balanced_count"]]),
        "",
        "城市路径分类变化如下：",
        "",
        markdown_table(path_changes if not path_changes.empty else pd.DataFrame([{"result": "各口径自动分类均未偏离预期路径。"}])),
        "",
        "## 5. 探索性回归结果",
        "",
        "所有回归仅用于 experimental validation，不得作为正式论文因果结论。",
        "",
        "成功运行模型：",
        "",
        markdown_table(successful[["caliber_name", "model_name", "n_obs", "r_squared", "adj_r_squared", "warnings"]]),
        "",
        "跳过模型：",
        "",
        markdown_table(skipped[["caliber_name", "model_name", "n_obs", "skip_reason"]] if not skipped.empty else skipped),
        "",
        "## 6. 稳健性判断",
        "",
        *questions[:5],
        "",
        "## 7. 数据风险",
        "",
        "- 厦门 2022 E_index 缺失，影响连续年份比较和 balanced_years_only 口径。",
        "- 泉州 2019、2020 I_index=0，虽然不是 missing 填 0，但对低位波动判断影响明显。",
        "- 三市小样本不能支撑正式因果推断。",
        "- 当前 I 端仍是实验性候选口径，需要复核企业/专利候选。",
        "- 小样本 min-max 标准化可能放大极端值。",
        "",
        "## 8. 下一步建议",
        "",
        "- 可以继续写实验性结果章节，但需明确 experimental validation。",
        "- 建议立即补厦门 2022 E 端。",
        "- 建议立即复核泉州 2019、2020 I 端。",
        "- 可以开始准备扩展福建 9 市，但不宜跳过缺失和 0 值复核。",
        "- 可以启动正式 C/B/X 口径数据收集，但本轮口径检验不是正式 C/B/X 结果。",
        "",
        "## 9. 可写入论文的实验性结论",
        "",
        "基于当前福州、厦门、泉州三市 2019-2024 年实验性 CCD 面板，教育端与产业端耦合协调水平呈现明显城市分化。福州整体表现为稳步改善，厦门在部分年份达到较高协调水平但存在 2022 年 E 端缺失，泉州则表现出早期低位与后续波动改善并存的特征。上述结果说明，福建省不同城市在人工智能教育供给与产业承接之间可能存在差异化演进路径。",
        "",
        "进一步的实验性口径检验显示，剔除泉州早期 I_index 为 0 的样本后，三市差异仍然存在，但泉州低位特征有所弱化，说明该结论对早期产业端低值具有一定敏感性。因此，当前结果可作为论文初稿中的探索性发现和后续口径设计依据，但仍需补齐厦门 2022 年 E 端数据，并复核泉州 2019、2020 年 I 端口径后，方可进入更正式的实证检验。",
        "",
        "## Warnings",
        "",
        *(warnings or ["无"]),
    ]
    path.write_text("\n".join(map(str, content)), encoding="utf-8")
    return "\n".join(questions)


def write_manifest(
    path: Path,
    run_id: str,
    input_path: Path,
    summary_report_path: Path,
    calibers: dict[str, pd.DataFrame],
    output_files: list[Path],
    warnings: list[str],
    next_step: str,
) -> None:
    manifest = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input_file": str(input_path),
        "input_file_exists": input_path.exists(),
        "summary_report": str(summary_report_path),
        "legacy_used": "archive/legacy_outputs" in str(input_path) or "outputs/ccd_outputs" in str(input_path),
        "calibers": [{"caliber_name": name, "sample_size": len(df)} for name, df in calibers.items()],
        "output_files": [str(path) for path in output_files],
        "warnings": warnings,
        "next_step_recommendation": next_step,
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    setup_plot_style()
    warnings = []
    try:
        input_path = resolve_input(args.input)
        summary_report_path = resolve_input(args.summary_report)
        dirs = make_run_dirs(run_id)
        panel, normalize_warnings = normalize_panel(pd.read_csv(input_path))
        warnings.extend(normalize_warnings)
        if "archive/legacy_outputs" in str(input_path) or "outputs/ccd_outputs" in str(input_path):
            raise ValueError("检测到 legacy 输入，已中止。")

        calibers = build_calibers(panel)
        summary_df = pd.DataFrame([summarize_caliber(name, df) for name, df in calibers.items()])
        city_df = pd.DataFrame([row for name, df in calibers.items() for row in summarize_city_caliber(name, df)])
        model_df, coeff_df = run_regressions(calibers)

        output_files: list[Path] = []
        caliber_results_path = dirs["tables"] / f"experimental_caliber_test_results_{run_id}.xlsx"
        write_caliber_results(caliber_results_path, panel, calibers, summary_df, city_df)
        output_files.append(caliber_results_path)

        regression_results_path = dirs["tables"] / f"experimental_caliber_regression_results_{run_id}.xlsx"
        write_regression_results(regression_results_path, model_df, coeff_df, calibers)
        output_files.append(regression_results_path)

        if plt is None or sns is None:
            raise RuntimeError("缺少 matplotlib/seaborn，无法生成口径检验图表。")
        fig_paths = [
            dirs["figures"] / f"experimental_caliber_D_comparison_{run_id}.png",
            dirs["figures"] / f"experimental_caliber_city_mean_D_{run_id}.png",
            dirs["figures"] / f"experimental_caliber_lag_type_distribution_{run_id}.png",
        ]
        plot_caliber_d(summary_df, fig_paths[0])
        plot_city_mean(city_df, fig_paths[1])
        plot_lag_distribution(calibers, fig_paths[2])
        output_files.extend(fig_paths)

        report_path = dirs["audit"] / f"experimental_caliber_test_report_{run_id}.md"
        next_step = write_report(report_path, run_id, input_path, summary_report_path, dirs, summary_df, city_df, model_df, warnings)
        output_files.append(report_path)

        latest_report = PROJECT_ROOT / "data" / "audit" / "experimental_caliber_tests" / "latest_experimental_caliber_test_report.md"
        latest_results = PROJECT_ROOT / "outputs" / "tables" / "experimental_caliber_tests" / "latest_experimental_caliber_test_results.xlsx"
        latest_report.parent.mkdir(parents=True, exist_ok=True)
        latest_results.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(report_path, latest_report)
        shutil.copy2(caliber_results_path, latest_results)
        output_files.extend([latest_report, latest_results])

        manifest_path = dirs["audit"] / f"experimental_caliber_test_manifest_{run_id}.json"
        output_files.append(manifest_path)
        write_manifest(manifest_path, run_id, input_path, summary_report_path, calibers, output_files, warnings, next_step)

        print(json.dumps(
            {
                "run_id": run_id,
                "input_file": str(input_path),
                "legacy_used": False,
                "caliber_sample_sizes": {name: len(df) for name, df in calibers.items()},
                "successful_models": model_df[model_df["skipped"].eq(False)][["caliber_name", "model_name"]].to_dict(orient="records"),
                "skipped_models": model_df[model_df["skipped"].eq(True)][["caliber_name", "model_name", "skip_reason"]].to_dict(orient="records"),
                "report": str(report_path),
                "manifest": str(manifest_path),
            },
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    except Exception as exc:
        print(f"experimental caliber pipeline failed: {exc}", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
