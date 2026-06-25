#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""辩论真实计算（对抗式辩论用，零杜撰，全部从仓库数据实跑）。

复刻 functional_chain_ccd_pipeline 的测度口径：
  - 各环节按 caliber 在全样本(9市×6年)上做固定基准 min-max（per_capita 环节先除人口；供给质量为 capacity 不人均化）
  - E=mean(供给规模,供给质量)，I=mean(产业承接,产业转化)
  - CCD: C=2√(EI)/(E+I)，T=(E+I)/2，D=√(C·T)；任一为0→不可计算
  - 子集/组合聚合：人口加权聚合 E、I 后再算 D（与 permutation_test_synergy 一致）

输出五块：
  A. Shapley 协同分解（512 子集，v=组合BI 与 v=组合D_S 两种特征函数）
  B. 收敛性：σ-收敛（逐年 D 离散度）+ β-收敛（ΔD 对初始 D，N=9）
  C. 互补>邻近：84 组合 BI 对 跨极/含核心/规模/邻近度 的回归与分组
  D. O-ring 签名：四环节跨市相关矩阵 + D离散度 vs 单环节离散度（方差放大）+ 双峰性（核密度峰计数）
  E. 腹地阈值：纯腹地 vs 含核心 组的 D/BI 均值复核 + 核心接入阈值

用法：python3 scripts/debate_checks.py
依赖：纯标准库（不引第三方，避免环境问题）。
"""
from __future__ import annotations
import csv, math, itertools, statistics
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "panel" / "functional_chain"
RES = ROOT / "data" / "audit" / "paper_a_functional_chain" / "latest_functional_chain_ccd_results.csv"
OUT = ROOT / "data" / "audit" / "paper_a_functional_chain"
CITIES = ["福州", "厦门", "泉州", "漳州", "莆田", "三明", "南平", "龙岩", "宁德"]
CORE = {"福州", "厦门"}
LINKS = {  # link id -> (panel file, normalization)
    "供给规模": ("e_supply_scale_panel.csv", "per_capita"),
    "供给质量": ("e_supply_quality_panel.csv", "capacity"),
    "产业承接": ("i_carrier_panel.csv", "per_capita"),
    "产业转化": ("i_conversion_panel.csv", "per_capita"),
}
E_LINKS = ["供给规模", "供给质量"]
I_LINKS = ["产业承接", "产业转化"]


def ccd(E, I):
    if E is None or I is None or E <= 0 or I <= 0:
        return 0.0
    C = 2 * math.sqrt(E * I) / (E + I)
    T = (E + I) / 2
    return math.sqrt(C * T)


def read_panel(fn):
    """-> {(caliber,city,year):(value,pop)}"""
    d = {}
    with open(PANEL / fn, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            cal = (r.get("caliber") or "").strip()
            try:
                v = float(r["value"]) if (r.get("value") or "").strip() != "" else None
            except ValueError:
                v = None
            pop = (r.get("population") or "").strip()
            pop = float(pop) if pop else None
            d[(cal, r["city"].strip(), int(r["year"]))] = (v, pop)
    return d


def build_indices(caliber="B"):
    """复刻管道：返回 {(city,year): {link: std_val}}, E[(c,y)], I[(c,y)], pop[(c,y)]。
    min-max 在 caliber 全网格上做（per_capita 先除人口）。"""
    raw = {lid: read_panel(fn) for lid, (fn, _) in LINKS.items()}
    grid = sorted({(c, y) for lid in raw for (cal, c, y) in raw[lid] if cal == caliber})
    pop = {}
    for lid in raw:
        for (cal, c, y), (v, p) in raw[lid].items():
            if cal == caliber and p is not None:
                pop[(c, y)] = p
    std = {lid: {} for lid in raw}
    for lid, (_, norm) in LINKS.items():
        vals = []
        for (c, y) in grid:
            v, p = raw[lid].get((caliber, c, y), (None, None))
            if v is not None and norm == "per_capita":
                v = v / p if p else None
            vals.append(((c, y), v))
        xs = [v for _, v in vals if v is not None]
        lo, hi = (min(xs), max(xs)) if xs else (0, 1)
        rng = (hi - lo) or 1.0
        for (c, y), v in vals:
            std[lid][(c, y)] = None if v is None else max(0.0, min(1.0, (v - lo) / rng))
    E, I = {}, {}
    for (c, y) in grid:
        sv = [std[lid].get((c, y)) for lid in E_LINKS]
        iv = [std[lid].get((c, y)) for lid in I_LINKS]
        E[(c, y)] = None if any(x is None for x in sv) else sum(sv) / len(sv)
        I[(c, y)] = None if any(x is None for x in iv) else sum(iv) / len(iv)
    return std, E, I, pop, grid


def agg_EI(combo, year, E, I, pop):
    """人口加权聚合 E、I（与 permutation_test_synergy 一致）。"""
    es = [E[(c, year)] for c in combo]
    is_ = [I[(c, year)] for c in combo]
    ps = [pop[(c, year)] for c in combo]
    P = sum(ps)
    Eg = sum(p * e for p, e in zip(ps, es)) / P
    Ig = sum(p * i for p, i in zip(ps, is_)) / P
    return Eg, Ig


# ============================ A. SHAPLEY ============================
def shapley(year=2024, caliber="B"):
    print("\n" + "=" * 70)
    print(f"A. SHAPLEY 协同分解（{year} {caliber}口径，2^9={2**9} 子集）")
    print("=" * 70)
    _, E, I, pop, _ = build_indices(caliber)
    cities = [c for c in CITIES if E.get((c, year)) is not None and pop.get((c, year)) is not None]
    n = len(cities)
    print(f"可用城市 N={n}: {cities}")

    def v_BI(S):
        """组合均衡改善度 BI = mean|E_i-I_i| - |E_S-I_S|；空/单集合定义 0。"""
        if len(S) == 0:
            return 0.0
        if len(S) == 1:
            return 0.0  # 单市无组团，BI=0
        Eg, Ig = agg_EI(list(S), year, E, I, pop)
        meandev = sum(abs(E[(c, year)] - I[(c, year)]) for c in S) / len(S)
        return meandev - abs(Eg - Ig)

    def v_DS(S):
        """组合整体协调度 D_S = ccd(E_S,I_S)；空集 0，单市=该市 D。"""
        if len(S) == 0:
            return 0.0
        Eg, Ig = agg_EI(list(S), year, E, I, pop)
        return ccd(Eg, Ig)

    def compute_shapley(vfun):
        phi = {c: 0.0 for c in cities}
        # 预计算所有子集的 v，避免重复
        idx = {c: k for k, c in enumerate(cities)}
        from math import factorial
        vmemo = {}
        for r in range(n + 1):
            for S in itertools.combinations(cities, r):
                vmemo[frozenset(S)] = vfun(S)
        for c in cities:
            others = [x for x in cities if x != c]
            tot = 0.0
            for r in range(len(others) + 1):
                w = factorial(r) * factorial(n - r - 1) / factorial(n)
                for S in itertools.combinations(others, r):
                    fs = frozenset(S)
                    marg = vmemo[fs | {c}] - vmemo[fs]
                    tot += w * marg
            phi[c] = tot
        return phi, vmemo[frozenset(cities)]

    out = {}
    for label, vf in [("BI(均衡/互补)", v_BI), ("D_S(水平拉动)", v_DS)]:
        phi, grand = compute_shapley(vf)
        ssum = sum(phi.values())
        ranked = sorted(phi.items(), key=lambda kv: -kv[1])
        print(f"\n  特征函数 v(S)={label}：大联盟 v(全9市)={grand:.4f}，Shapley 和={ssum:.4f}（应≈大联盟，验证可加性）")
        for c, p in ranked:
            print(f"    {c:<3} φ={p:+.4f}  ({p/grand*100:+5.1f}% of grand)" if grand else f"    {c:<3} φ={p:+.4f}")
        out[label] = ranked
    return out


# ============================ B. 收敛性 ============================
def convergence(caliber="B"):
    print("\n" + "=" * 70)
    print(f"B. 收敛性检验（{caliber}口径，2019-2024）— 支撑 Ⅰ 的'不收敛'")
    print("=" * 70)
    _, E, I, pop, _ = build_indices(caliber)
    years = list(range(2019, 2025))
    # 逐年 D（只用可计算城市）
    D_by_year = {}
    for y in years:
        ds = {c: ccd(E.get((c, y)), I.get((c, y))) for c in CITIES
              if E.get((c, y)) is not None and I.get((c, y)) is not None}
        ds = {c: d for c, d in ds.items() if d > 0}  # 排除不可计算
        D_by_year[y] = ds
    print("\n  σ-收敛（每年 D 的标准差/变异系数；样本=当年可计算城市）：")
    print(f"  {'年':>4}{'N':>4}{'均值':>9}{'标准差':>10}{'变异系数':>11}")
    sig_series = []
    for y in years:
        ds = list(D_by_year[y].values())
        if len(ds) < 2:
            continue
        m = statistics.fmean(ds); sd = statistics.pstdev(ds); cv = sd / m
        sig_series.append((y, len(ds), m, sd, cv))
        print(f"  {y:>4}{len(ds):>4}{m:>9.4f}{sd:>10.4f}{cv:>11.4f}")
    # 平衡面板：仅取全6年可计算的城市，做严格 σ 比较
    balanced = [c for c in CITIES if all(D_by_year[y].get(c, 0) > 0 for y in years)]
    print(f"\n  平衡面板（全6年可计算）城市 N={len(balanced)}: {balanced}")
    print(f"  {'年':>4}{'均值':>9}{'标准差':>10}{'变异系数':>11}")
    bal_sd = []
    for y in years:
        ds = [D_by_year[y][c] for c in balanced]
        m = statistics.fmean(ds); sd = statistics.pstdev(ds); cv = sd / m
        bal_sd.append((y, sd, cv))
        print(f"  {y:>4}{m:>9.4f}{sd:>10.4f}{cv:>11.4f}")
    sd0, sdT = bal_sd[0][1], bal_sd[-1][1]
    cv0, cvT = bal_sd[0][2], bal_sd[-1][2]
    print(f"\n  σ-收敛结论：标准差 2019={sd0:.4f} → 2024={sdT:.4f} （{'扩大→发散' if sdT>sd0 else '缩小→收敛'}，Δ={sdT-sd0:+.4f}）")
    print(f"             变异系数 2019={cv0:.4f} → 2024={cvT:.4f} （{'下降' if cvT<cv0 else '上升'}，Δ={cvT-cv0:+.4f}）")

    # β-收敛：ΔD(2019→2024) 对 初始 D(2019) OLS，N=balanced（手算单变量OLS）
    xs = [D_by_year[2019][c] for c in balanced]
    ys = [D_by_year[2024][c] - D_by_year[2019][c] for c in balanced]
    nb = len(xs)
    mx = statistics.fmean(xs); my = statistics.fmean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    beta = sxy / sxx
    alpha = my - beta * mx
    yhat = [alpha + beta * x for x in xs]
    ss_res = sum((y - yh) ** 2 for y, yh in zip(ys, yhat))
    ss_tot = sum((y - my) ** 2 for y in ys)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    se_beta = math.sqrt((ss_res / (nb - 2)) / sxx) if nb > 2 else float("nan")
    t_beta = beta / se_beta if se_beta else float("nan")
    print(f"\n  β-收敛 OLS（ΔD = α + β·D₀，N={nb}，小样本警示）：")
    print(f"    β={beta:+.4f}  SE={se_beta:.4f}  t={t_beta:+.3f}  R²={r2:.3f}  α={alpha:+.4f}")
    print(f"    解读：β<0=收敛；此处 β={beta:+.4f} → {'负但需看显著性' if beta<0 else '正→发散'}；"
          f"|t|={abs(t_beta):.2f} {'>2 → 5%显著' if abs(t_beta)>2 else '<2 → 不显著(N=9无法可信推断)'}")
    return sig_series, (beta, t_beta, r2)


# ============================ C. 互补>邻近 ============================
# 福建9市地理相邻表（按陆地接壤；学生自编码，供核）
ADJ = {
    "福州": {"宁德", "南平", "三明", "莆田", "泉州"},
    "厦门": {"漳州", "泉州"},
    "泉州": {"福州", "莆田", "三明", "漳州", "厦门"},
    "漳州": {"厦门", "泉州", "龙岩"},
    "莆田": {"福州", "泉州"},
    "三明": {"福州", "泉州", "南平", "龙岩"},
    "南平": {"福州", "三明", "宁德"},
    "龙岩": {"漳州", "三明"},
    "宁德": {"福州", "南平"},
}


def complement_vs_adjacency(year=2024, caliber="B"):
    print("\n" + "=" * 70)
    print(f"C. 互补>邻近（{year} {caliber}口径，84 三市组合）")
    print("=" * 70)
    # 验证邻接表对称
    for a, nb in ADJ.items():
        for b in nb:
            assert a in ADJ[b], f"邻接表不对称: {a}-{b}"
    _, E, I, pop, _ = build_indices(caliber)
    cities = [c for c in CITIES if E.get((c, year)) is not None]
    rows = []
    for combo in itertools.combinations(cities, 3):
        Eg, Ig = agg_EI(list(combo), year, E, I, pop)
        BI = sum(abs(E[(c, year)] - I[(c, year)]) for c in combo) / 3 - abs(Eg - Ig)
        # 跨极哑变量：组内既含'教育领先'(E>I)又含'产业领先'(I>E)? 用 E-I 符号
        signs = [1 if E[(c, year)] > I[(c, year)] else -1 for c in combo]
        cross = 1 if (1 in signs and -1 in signs) else 0
        has_core = 1 if any(c in CORE for c in combo) else 0
        # 邻近度：组内 3 对中相邻对数 / 3
        pairs = list(itertools.combinations(combo, 2))
        adj_count = sum(1 for a, b in pairs if b in ADJ[a])
        adj_ratio = adj_count / 3
        # 组合规模(人口) 与 平均水平 T
        P = sum(pop[(c, year)] for c in combo)
        Tg = (Eg + Ig) / 2
        # 镜像互补指数：组内 max(E-I) - min(E-I)（结构跨度，越大越互补）
        diffs = [E[(c, year)] - I[(c, year)] for c in combo]
        mirror = max(diffs) - min(diffs)
        rows.append(dict(combo=combo, BI=BI, cross=cross, has_core=has_core,
                         adj_count=adj_count, adj_ratio=adj_ratio, pop=P, T=Tg, mirror=mirror))
    print(f"  组合数={len(rows)}")
    # 分组均值
    def grpmean(key, key2=None):
        g = {}
        for r in rows:
            k = r[key] if key2 is None else (r[key], r[key2])
            g.setdefault(k, []).append(r["BI"])
        return {k: (statistics.fmean(v), len(v)) for k, v in g.items()}

    print("\n  ① 分组：跨极 vs 不跨极 的平均 BI")
    for k, (m, c) in sorted(grpmean("cross").items()):
        print(f"     cross={k}: 均值BI={m:+.4f} (n={c})")
    print("\n  ② 分组：含核心 vs 不含核心")
    for k, (m, c) in sorted(grpmean("has_core").items()):
        print(f"     has_core={k}: 均值BI={m:+.4f} (n={c})")
    print("\n  ③ 分组：相邻对数(0/1/2/3) 的平均 BI")
    for k, (m, c) in sorted(grpmean("adj_count").items()):
        print(f"     相邻对数={k}: 均值BI={m:+.4f} (n={c})")
    print("\n  ④ 交叉：cross × has_core 平均 BI（隔离规模/水平）")
    for k, (m, c) in sorted(grpmean("cross", "has_core").items()):
        print(f"     cross={k[0]},has_core={k[1]}: 均值BI={m:+.4f} (n={c})")

    # 相关：BI vs mirror, BI vs adj_ratio, mirror vs adj
    def corr(a, b):
        ma, mb = statistics.fmean(a), statistics.fmean(b)
        num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
        return num / den if den else float("nan")
    BIs = [r["BI"] for r in rows]
    print("\n  ⑤ 相关系数（描述性，组合不独立→仅作描述）")
    print(f"     corr(BI, 镜像互补指数 mirror) = {corr(BIs, [r['mirror'] for r in rows]):+.4f}")
    print(f"     corr(BI, 邻近度 adj_ratio)    = {corr(BIs, [r['adj_ratio'] for r in rows]):+.4f}")
    print(f"     corr(BI, 含核心 has_core)     = {corr(BIs, [float(r['has_core']) for r in rows]):+.4f}")
    print(f"     corr(BI, 跨极 cross)          = {corr(BIs, [float(r['cross']) for r in rows]):+.4f}")
    print(f"     corr(BI, 组合人口 pop)        = {corr(BIs, [r['pop'] for r in rows]):+.4f}")
    print(f"     corr(BI, 平均水平 T)          = {corr(BIs, [r['T'] for r in rows]):+.4f}")

    # 多元 OLS：BI ~ mirror + adj_ratio + has_core + T  (手写正规方程，看互补 vs 邻近谁存活)
    import_ok = ols(rows, ["mirror", "adj_ratio", "has_core", "T"], "BI",
                    labels=["镜像互补", "邻近度", "含核心", "平均水平T"])
    return rows


def ols(rows, xcols, ycol, labels=None):
    """最小二乘（含截距），手写求解正规方程 (X'X)b=X'y，高斯消元。打印系数+R²。"""
    labels = labels or xcols
    X = [[1.0] + [r[c] for c in xcols] for r in rows]
    y = [r[ycol] for r in rows]
    k = len(xcols) + 1
    XtX = [[sum(X[m][i] * X[m][j] for m in range(len(X))) for j in range(k)] for i in range(k)]
    Xty = [sum(X[m][i] * y[m] for m in range(len(X))) for i in range(k)]
    # 高斯消元
    A = [row[:] + [Xty[i]] for i, row in enumerate(XtX)]
    for col in range(k):
        piv = max(range(col, k), key=lambda r: abs(A[r][col]))
        A[col], A[piv] = A[piv], A[col]
        if abs(A[col][col]) < 1e-12:
            print("    (共线性，无法求解OLS)"); return None
        for r in range(k):
            if r != col:
                f = A[r][col] / A[col][col]
                A[r] = [A[r][j] - f * A[col][j] for j in range(k + 1)]
    b = [A[i][k] / A[i][i] for i in range(k)]
    yhat = [sum(b[i] * X[m][i] for i in range(k)) for m in range(len(X))]
    my = statistics.fmean(y)
    ss_res = sum((y[m] - yhat[m]) ** 2 for m in range(len(y)))
    ss_tot = sum((v - my) ** 2 for v in y)
    r2 = 1 - ss_res / ss_tot
    print(f"\n  ⑥ 多元OLS：{ycol} ~ {' + '.join(labels)}（描述性，组合不独立，SE不可靠故不报t）")
    print(f"     截距={b[0]:+.4f}")
    for i, lab in enumerate(labels, 1):
        print(f"     {lab:<8}系数={b[i]:+.4f}")
    print(f"     R²={r2:.3f}")
    return b


# ============================ D. O-RING 签名 ============================
def oring_signature(year=2024, caliber="B"):
    print("\n" + "=" * 70)
    print(f"D. O-ring 签名（{caliber}口径）")
    print("=" * 70)
    std, E, I, pop, grid = build_indices(caliber)
    links = list(LINKS.keys())
    # D.1 四环节跨市相关矩阵（2024 截面，9市）
    cities = [c for c in CITIES if all(std[l].get((c, year)) is not None for l in links)]
    print(f"\n  D.1 四环节标准化值跨市相关矩阵（{year}，N={len(cities)} 市）：")
    vecs = {l: [std[l][(c, year)] for c in cities] for l in links}

    def corr(a, b):
        ma, mb = statistics.fmean(a), statistics.fmean(b)
        num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
        return num / den if den else float("nan")
    print("        " + "".join(f"{l[:2]:>9}" for l in links))
    cmat = []
    for l1 in links:
        row = [corr(vecs[l1], vecs[l2]) for l2 in links]
        cmat.append(row)
        print(f"  {l1:<6}" + "".join(f"{v:>9.3f}" for v in row))
    offdiag = [cmat[i][j] for i in range(4) for j in range(4) if i < j]
    print(f"     非对角平均相关={statistics.fmean(offdiag):+.4f}（O-ring预测：强正相关=环节共动/同配）")

    # D.2 方差放大：D 离散度 vs 单环节离散度（54 城市-年合并 与 2024 截面）
    print("\n  D.2 方差放大（产出方差 ≫ 投入方差？）")
    for scope, sel in [("2024截面(9市)", [(c, year) for c in cities]),
                       ("54城市-年合并(可计算)", [(c, y) for c in CITIES for y in range(2019, 2025)
                                              if E.get((c, y)) and I.get((c, y)) and ccd(E.get((c, y)), I.get((c, y))) > 0])]:
        Ds = [ccd(E[k], I[k]) for k in sel]
        link_cv = {}
        for l in links:
            xs = [std[l][k] for k in sel if std[l].get(k) is not None]
            if len(xs) > 1 and statistics.fmean(xs) > 0:
                link_cv[l] = statistics.pstdev(xs) / statistics.fmean(xs)
        D_cv = statistics.pstdev(Ds) / statistics.fmean(Ds)
        avg_link_cv = statistics.fmean(list(link_cv.values()))
        print(f"     {scope}: CV(D)={D_cv:.3f}  平均CV(单环节)={avg_link_cv:.3f}  "
              f"放大比={D_cv/avg_link_cv:.2f}×  "
              f"{'(D方差 < 投入方差，O-ring放大不成立)' if D_cv < avg_link_cv else '(D方差 > 投入)'}")
        print(f"        各环节CV: {', '.join(f'{l}={v:.2f}' for l,v in link_cv.items())}")

    # D.3 双峰性：54 城市-年 D 的核密度峰计数（高斯核，Silverman带宽）
    print("\n  D.3 双峰性（54 城市-年合并 D 的核密度峰计数 + 分组计数）")
    allD = [ccd(E.get((c, y)), I.get((c, y))) for c in CITIES for y in range(2019, 2025)]
    allD = [d for d in allD if d and d > 0]
    n = len(allD)
    sd = statistics.pstdev(allD)
    h = 0.9 * min(sd, (statistics.quantiles(allD, n=4)[2] - statistics.quantiles(allD, n=4)[0]) / 1.34) * n ** (-1 / 5)
    grid_x = [i / 200 for i in range(0, 201)]

    def kde(x):
        return sum(math.exp(-0.5 * ((x - d) / h) ** 2) for d in allD) / (n * h * math.sqrt(2 * math.pi))
    dens = [kde(x) for x in grid_x]
    peaks = [grid_x[i] for i in range(1, len(dens) - 1) if dens[i] > dens[i - 1] and dens[i] >= dens[i + 1]]
    print(f"     N={n}, 带宽h={h:.4f}, 检出峰位置={[round(p,3) for p in peaks]} → {len(peaks)} 峰")
    # 分组计数
    bins = [(0, 0.3, "失调<0.3"), (0.3, 0.5, "过渡0.3-0.5"), (0.5, 0.8, "中协调0.5-0.8"), (0.8, 1.01, "高协调>0.8")]
    print("     分组计数：" + "; ".join(f"{lab}={sum(1 for d in allD if lo<=d<hi)}" for lo, hi, lab in bins))
    print(f"     {'双峰(核心簇+腹地簇)，中间0.4-0.8稀疏 → 支持两极化' if len(peaks)>=2 else '单峰 → 两极化证据弱'}")
    return cmat


# ============================ E. 腹地阈值 ============================
def hinterland_threshold(year=2024, caliber="B"):
    print("\n" + "=" * 70)
    print(f"E. 腹地抱团 vs 核心接入阈值（{year} {caliber}口径）")
    print("=" * 70)
    _, E, I, pop, _ = build_indices(caliber)
    cities = [c for c in CITIES if E.get((c, year)) is not None]
    pure_BI, pure_D, withcore_BI, withcore_D = [], [], [], []
    for combo in itertools.combinations(cities, 3):
        Eg, Ig = agg_EI(list(combo), year, E, I, pop)
        Dg = ccd(Eg, Ig)
        BI = sum(abs(E[(c, year)] - I[(c, year)]) for c in combo) / 3 - abs(Eg - Ig)
        ncore = sum(1 for c in combo if c in CORE)
        if ncore == 0:
            pure_BI.append(BI); pure_D.append(Dg)
        else:
            withcore_BI.append(BI); withcore_D.append(Dg)
    print(f"  纯腹地组(n={len(pure_D)})：  均值 D={statistics.fmean(pure_D):.4f}  均值 BI={statistics.fmean(pure_BI):+.4f}  max D={max(pure_D):.4f}")
    print(f"  含核心组(n={len(withcore_D)})：均值 D={statistics.fmean(withcore_D):.4f}  均值 BI={statistics.fmean(withcore_BI):+.4f}")
    print(f"  含核心/纯腹地 D 倍数={statistics.fmean(withcore_D)/statistics.fmean(pure_D):.2f}×")
    # 核心接入阈值：含1个核心 vs 含2个核心
    for ncore in [1, 2]:
        ds, bis = [], []
        for combo in itertools.combinations(cities, 3):
            if sum(1 for c in combo if c in CORE) == ncore:
                Eg, Ig = agg_EI(list(combo), year, E, I, pop)
                ds.append(ccd(Eg, Ig))
                bis.append(sum(abs(E[(c, year)] - I[(c, year)]) for c in combo) / 3 - abs(Eg - Ig))
        print(f"  含{ncore}核心组(n={len(ds)})：均值 D={statistics.fmean(ds):.4f}  均值 BI={statistics.fmean(bis):+.4f}")


if __name__ == "__main__":
    shapley()
    convergence()
    complement_vs_adjacency()
    oring_signature()
    hinterland_threshold()
