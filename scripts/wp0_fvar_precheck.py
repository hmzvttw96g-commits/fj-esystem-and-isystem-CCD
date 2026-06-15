#!/usr/bin/env python3
"""WP0 F端变异度预检：判定样本边界 = 福建9市 or 扩展闽浙粤。

为何存在：论文B 的识别功率与少聚类推断取决于样本规模与 F 变量的跨城/时序变异。
本脚本用统计年鉴现成 F 变量（无需一手采集），对每个 F 变量计算：
  - 组间单因素 ANOVA F 统计量与 p 值（城市间是否有足够横截面对比）
  - ICC(1) 组内相关系数（变异中有多少来自城市间 vs 城市内时序）
  - 组内时序变异系数（两向固定效应实际利用的变异）
并结合聚类数（城市数）给出 EXPAND / FUJIAN_OK 建议。脚本只出建议，研究者拍板。

纯标准库实现（含 F 分布 p 值的正则不完全 Beta 函数），不依赖 pandas/numpy/statsmodels，
保证在未装科学计算栈的环境下即可运行。沿用项目 run_id/manifest/latest_ 纪律。

用法：
  python3 scripts/wp0_fvar_precheck.py --self-test       # 合成数据自检，证明统计内核正确
  python3 scripts/wp0_fvar_precheck.py --make-template    # 生成空白输入面板模板（待填年鉴数据）
  python3 scripts/wp0_fvar_precheck.py --input <panel.csv>  # 对真实面板出预检报告
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("需要 pyyaml：pip3 install --user pyyaml")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "wp0_fvar_precheck.yml"
AUDIT_DIR = PROJECT_ROOT / "data" / "audit" / "wp0_fvar_precheck"
PANEL_DIR = PROJECT_ROOT / "data" / "panel" / "wp0_fvar_precheck"


# ----------------------------- 统计内核（纯标准库） -----------------------------
def _betacf(a: float, b: float, x: float) -> float:
    """正则不完全 Beta 的连分式（Numerical Recipes）。"""
    MAXIT, EPS, FPMIN = 200, 3.0e-12, 1.0e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < EPS:
            break
    return h


def betai(a: float, b: float, x: float) -> float:
    """正则不完全 Beta 函数 I_x(a,b)。"""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    bt = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def f_sf(f: float, df1: int, df2: int) -> float:
    """F 分布上尾概率 P(F>f)（p 值）。"""
    if f <= 0 or df1 <= 0 or df2 <= 0:
        return 1.0
    x = df2 / (df2 + df1 * f)
    return betai(df2 / 2.0, df1 / 2.0, x)


def oneway_anova(groups: list[list[float]]) -> dict:
    """单因素 ANOVA + ICC(1)。groups = 每个城市的时序观测列表。"""
    groups = [g for g in groups if len(g) > 0]
    G = len(groups)
    allvals = [v for g in groups for v in g]
    N = len(allvals)
    if G < 2 or N <= G:
        return {"ok": False, "reason": "城市数<2或观测不足"}
    grand = statistics.fmean(allvals)
    ss_between = sum(len(g) * (statistics.fmean(g) - grand) ** 2 for g in groups)
    ss_within = sum((v - statistics.fmean(g)) ** 2 for g in groups for v in g)
    df_b, df_w = G - 1, N - G
    ms_b = ss_between / df_b
    ms_w = ss_within / df_w if df_w > 0 else float("nan")
    f_stat = ms_b / ms_w if ms_w and ms_w > 0 else float("inf")
    p = f_sf(f_stat, df_b, df_w) if math.isfinite(f_stat) else 0.0
    # ICC(1)：平均组规模 k（不均衡用调整 k0）
    sizes = [len(g) for g in groups]
    n_sum, n_sq = sum(sizes), sum(s * s for s in sizes)
    k0 = (n_sum - n_sq / n_sum) / (G - 1)
    icc = (ms_b - ms_w) / (ms_b + (k0 - 1) * ms_w) if (ms_b + (k0 - 1) * ms_w) != 0 else float("nan")
    # 组内时序变异系数（各城市 CV 的均值）
    within_cvs = []
    for g in groups:
        if len(g) >= 2:
            m = statistics.fmean(g)
            if m != 0:
                within_cvs.append(statistics.pstdev(g) / abs(m))
    within_cv = statistics.fmean(within_cvs) if within_cvs else float("nan")
    return {
        "ok": True, "G": G, "N": N, "f_stat": f_stat, "p_between": p,
        "icc1": icc, "within_cv_mean": within_cv,
        "overall_cv": statistics.pstdev(allvals) / abs(grand) if grand else float("nan"),
    }


# ----------------------------- 主流程 -----------------------------
def load_cfg() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_id_now() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def make_template(cfg: dict, run_id: str) -> Path:
    cities = cfg["samples"]["fujian_9"]["cities"]
    years = list(range(2015, 2025))
    cols = ["city", "year"] + [v["col"] for v in cfg["f_variables"]]
    out = PANEL_DIR / run_id
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"wp0_fvar_panel_template_{run_id}.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for c in cities:
            for y in years:
                w.writerow([c, y] + [""] * len(cfg["f_variables"]))
    # 扩样城市清单参考
    ref = out / f"wp0_extended_city_reference_{run_id}.csv"
    with open(ref, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["sample", "city"])
        for s, node in cfg["samples"].items():
            for c in node["cities"]:
                w.writerow([s, c])
    return path


def read_panel(path: Path, cfg: dict) -> dict:
    """读 CSV → {var_col: {city: [values...]}}。空值跳过。"""
    var_cols = [v["col"] for v in cfg["f_variables"]]
    data = {vc: {} for vc in var_cols}
    cities = set()
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            city = (row.get("city") or "").strip()
            if not city:
                continue
            cities.add(city)
            for vc in var_cols:
                raw = (row.get(vc) or "").strip()
                if raw == "":
                    continue
                try:
                    data[vc].setdefault(city, []).append(float(raw))
                except ValueError:
                    pass
    return {"data": data, "n_cities": len(cities), "cities": sorted(cities)}


def analyze(panel: dict, cfg: dict) -> dict:
    th = cfg["thresholds"]
    n_clusters = panel["n_cities"]
    results, unhealthy_key = [], 0
    n_key = 0
    for v in cfg["f_variables"]:
        vc, key = v["col"], v["key"]
        groups = list(panel["data"].get(vc, {}).values())
        stat = oneway_anova(groups)
        row = {"col": vc, "label": v["label"], "role": v["role"], "key": key, **stat}
        if stat.get("ok"):
            weak_between = stat["p_between"] >= th["between_city_f_alpha"]
            icc_high = math.isfinite(stat["icc1"]) and stat["icc1"] > th["icc_high"]
            low_within = math.isfinite(stat["within_cv_mean"]) and stat["within_cv_mean"] < th["min_within_cv"]
            row["unhealthy"] = bool(weak_between or icc_high or low_within)
            row["flags"] = ",".join(fl for fl, c in
                                    [("组间F不显著", weak_between), ("ICC过高", icc_high), ("组内CV过低", low_within)] if c) or "健康"
        else:
            row["unhealthy"] = None
            row["flags"] = stat.get("reason", "无法计算")
        if key:
            n_key += 1
            if row["unhealthy"]:
                unhealthy_key += 1
        results.append(row)

    vr = cfg["verdict_rule"]
    ratio = (unhealthy_key / n_key) if n_key else 0.0
    if n_clusters < vr["expand_if_clusters_below"]:
        verdict = "EXPAND"
        reason = f"城市数={n_clusters}<{vr['expand_if_clusters_below']}，少聚类推断为主因（对应框架'聚类升至30+'）"
    elif ratio > vr["expand_if_key_vars_unhealthy_ratio_above"]:
        verdict = "EXPAND"
        reason = f"关键F变量变异不健康比例={ratio:.0%}>50%，省内变异不足以识别"
    else:
        verdict = "FUJIAN_OK"
        reason = f"城市数={n_clusters}，关键变量不健康比例={ratio:.0%}；省内可行"
        if n_clusters < th["min_clusters_comfortable"]:
            reason += f"（但<{th['min_clusters_comfortable']}，须报告 wild bootstrap Webb 少聚类稳健性）"
    return {"n_clusters": n_clusters, "results": results,
            "unhealthy_key_ratio": ratio, "verdict": verdict, "reason": reason}


def write_report(panel: dict, analysis: dict, cfg: dict, run_id: str, input_path: Path):
    out = AUDIT_DIR / run_id
    out.mkdir(parents=True, exist_ok=True)
    # stats CSV
    stats_csv = out / f"wp0_fvar_stats_{run_id}.csv"
    with open(stats_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["变量", "角色", "key", "城市数G", "观测N", "组间F", "组间p",
                    "ICC(1)", "组内CV均值", "整体CV", "是否不健康", "标记"])
        for r in analysis["results"]:
            w.writerow([r["label"], r["role"], r["key"], r.get("G", ""), r.get("N", ""),
                        f"{r.get('f_stat', float('nan')):.3f}" if r.get("ok") else "",
                        f"{r.get('p_between', float('nan')):.4f}" if r.get("ok") else "",
                        f"{r.get('icc1', float('nan')):.3f}" if r.get("ok") else "",
                        f"{r.get('within_cv_mean', float('nan')):.3f}" if r.get("ok") else "",
                        f"{r.get('overall_cv', float('nan')):.3f}" if r.get("ok") else "",
                        r["unhealthy"], r["flags"]])
    # report MD
    rep = out / f"wp0_fvar_precheck_report_{run_id}.md"
    lines = [f"# WP0 F端变异度预检报告 — {run_id}", "",
             f"- 输入面板：`{input_path}`", f"- 城市数（聚类数）：**{panel['n_cities']}**",
             f"- 关键F变量不健康比例：{analysis['unhealthy_key_ratio']:.0%}", "",
             f"## 建议：**{analysis['verdict']}**", "", f"> {analysis['reason']}", "",
             "判定为脚本建议，最终样本边界由研究者签字（config.decision_owner=researcher）。", "",
             "## 逐变量诊断", "",
             "| 变量 | 角色 | key | G | N | 组间F | 组间p | ICC(1) | 组内CV | 标记 |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in analysis["results"]:
        if r.get("ok"):
            lines.append(f"| {r['label']} | {r['role']} | {r['key']} | {r['G']} | {r['N']} | "
                         f"{r['f_stat']:.2f} | {r['p_between']:.4f} | {r['icc1']:.3f} | "
                         f"{r['within_cv_mean']:.3f} | {r['flags']} |")
        else:
            lines.append(f"| {r['label']} | {r['role']} | {r['key']} | - | - | - | - | - | - | {r['flags']} |")
    lines += ["", "## 读法",
              "- **组间p≥0.05**：城市间该变量无显著差异→横截面对比弱。",
              "- **ICC(1)>0.85**：变异几乎全来自城市间、城市内几乎不随时间动→两向FE后弱识别。",
              "- **组内CV过低**：两向固定效应实际利用的时序变异不足。",
              "- 三者任一即标记该变量不健康；过半关键变量不健康或城市数<20→建议扩样。", "",
              "⛔ 本预检仅服务论文B识别功率与少聚类推断；论文A不依赖此结果。"]
    rep.write_text("\n".join(lines), encoding="utf-8")
    # manifest
    manifest = {"run_id": run_id, "generated_at": datetime.now().isoformat(),
                "task": "WP0 F端变异度预检", "input": str(input_path),
                "n_clusters": panel["n_cities"], "verdict": analysis["verdict"],
                "outputs": [str(stats_csv), str(rep)]}
    (out / f"wp0_manifest_{run_id}.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    # latest_ 入口
    for src in (stats_csv, rep):
        (AUDIT_DIR / f"latest_{src.name.replace('_' + run_id, '')}").write_text(
            src.read_text(encoding="utf-8"), encoding="utf-8")
    return rep


def self_test(cfg: dict):
    """合成两种数据证明统计内核：(A)城市间强差异+组内有时序动→健康；(B)城市间几乎无差异→不健康。"""
    import random
    random.seed(42)
    print("== 自检：合成数据验证统计内核 ==")
    # 场景A：9市，城市基线差异大、组内逐年小幅波动
    groupsA = [[10 + 5 * i + random.gauss(0, 0.8) for _ in range(10)] for i in range(9)]
    a = oneway_anova(groupsA)
    print(f"[A 强城市间差异] 组间F={a['f_stat']:.1f} p={a['p_between']:.2e} "
          f"ICC={a['icc1']:.3f} 组内CV={a['within_cv_mean']:.3f}  "
          f"→ 预期 p极小、ICC高但有组内动")
    # 场景B：9市，城市间几乎无差异（同均值），纯噪声
    groupsB = [[10 + random.gauss(0, 1.0) for _ in range(10)] for _ in range(9)]
    b = oneway_anova(groupsB)
    print(f"[B 无城市间差异] 组间F={b['f_stat']:.2f} p={b['p_between']:.3f} "
          f"ICC={b['icc1']:.3f}  → 预期 p不显著、ICC≈0")
    # F分布 p 值健全性：F=1 时 p 应接近大值；已知 F(2,20)=3.49 临界≈0.05
    p_crit = f_sf(3.4928, 2, 20)
    print(f"[F分布校验] P(F(2,20)>3.4928)={p_crit:.4f}（理论≈0.0500）")
    ok = a["p_between"] < 0.01 and b["p_between"] > 0.05 and abs(p_crit - 0.05) < 0.002
    print("自检", "通过 ✓" if ok else "失败 ✗")
    return ok


def main():
    ap = argparse.ArgumentParser(description="WP0 F端变异度预检")
    ap.add_argument("--input", help="F变量面板CSV（city,year,<f_vars>）")
    ap.add_argument("--make-template", action="store_true", help="生成空白输入模板")
    ap.add_argument("--self-test", action="store_true", help="合成数据自检统计内核")
    args = ap.parse_args()
    cfg = load_cfg()

    if args.self_test:
        raise SystemExit(0 if self_test(cfg) else 1)

    run_id = run_id_now()
    if args.make_template:
        path = make_template(cfg, run_id)
        print(f"已生成空白模板：{path}\n填入年鉴 F 变量后用 --input 跑预检。")
        return
    if not args.input:
        ap.error("需 --input <panel.csv> 或 --make-template 或 --self-test")
    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"输入不存在：{input_path}")
    panel = read_panel(input_path, cfg)
    analysis = analyze(panel, cfg)
    rep = write_report(panel, analysis, cfg, run_id, input_path)
    print(f"建议：{analysis['verdict']} — {analysis['reason']}")
    print(f"报告：{rep}")


if __name__ == "__main__":
    main()
