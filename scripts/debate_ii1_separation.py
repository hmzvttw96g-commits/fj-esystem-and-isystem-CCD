# -*- coding: utf-8 -*-
"""Ⅱ.1「互补>邻近」严格分离分析（把"规模/机械同义/邻近"三种攻击逐一打掉）。
复用 debate_checks 的口径(build_indices/agg_EI/ccd/ADJ/CORE)，零新数据。
用法：python3 scripts/debate_ii1_separation.py
核心思路：
  - 诚实揭示"BI 与镜像互补 mirror 部分机械同义"(对城市标签置换不变 → 是度量性质,非地理发现)。
  - 真正非机械、可证伪的论点 = "互补与邻近在福建空间错位":corr(mirror, 邻近) 低/负。
    用"profile↔地理槽位"置换给出该错位的零分布与经验 p 值(这是合法的随机化推断对象)。
  - 规模攻击:偏相关 corr(BI,mirror|size) + 标准化 OLS + 剔除福厦子样本。
"""
import itertools, math, random, statistics, importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dc", ROOT / "scripts" / "debate_checks.py")
dc = importlib.util.module_from_spec(spec); spec.loader.exec_module(dc)
YEAR, CAL = 2024, "B"
_, E, I, pop, _ = dc.build_indices(CAL)
CITIES = [c for c in dc.CITIES if E.get((c, YEAR)) is not None and pop.get((c, YEAR)) is not None]
ADJ, CORE = dc.ADJ, dc.CORE


def corr(a, b):
    n = len(a); ma, mb = sum(a) / n, sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = math.sqrt(sum((x - ma) ** 2 for x in a)); vb = math.sqrt(sum((y - mb) ** 2 for y in b))
    return cov / (va * vb) if va and vb else 0.0


def partial_corr(x, y, z):
    """corr(x,y | z)"""
    rxy, rxz, ryz = corr(x, y), corr(x, z), corr(y, z)
    den = math.sqrt((1 - rxz ** 2) * (1 - ryz ** 2))
    return (rxy - rxz * ryz) / den if den else 0.0


def ols_std(y, Xcols):
    """标准化 OLS（z-score 所有变量），返回各列标准化 beta。纯 stdlib 正规方程。"""
    def z(v):
        m = sum(v) / len(v); s = math.sqrt(sum((x - m) ** 2 for x in v) / len(v)) or 1.0
        return [(x - m) / s for x in v]
    Y = z(y); Xs = [z(c) for c in Xcols]; n = len(Y); k = len(Xs)
    X = [[1.0] + [Xs[j][i] for j in range(k)] for i in range(n)]
    XtX = [[sum(X[r][a] * X[r][b] for r in range(n)) for b in range(k + 1)] for a in range(k + 1)]
    Xty = [sum(X[r][a] * Y[r] for r in range(n)) for a in range(k + 1)]
    # Gauss-Jordan 解 XtX beta = Xty
    M = [row[:] + [Xty[i]] for i, row in enumerate(XtX)]
    m = k + 1
    for col in range(m):
        piv = max(range(col, m), key=lambda r: abs(M[r][col])); M[col], M[piv] = M[piv], M[col]
        d = M[col][col] or 1e-12
        M[col] = [v / d for v in M[col]]
        for r in range(m):
            if r != col:
                f = M[r][col]; M[r] = [a - f * b for a, b in zip(M[r], M[col])]
    return [M[i][m] for i in range(1, m)]  # 去掉截距


d = {c: E[(c, YEAR)] - I[(c, YEAR)] for c in CITIES}  # 有符号失衡 E-I（>0教育领先,<0产业领先）

# ---------- 1. 配对层(36 对):互补与邻近是否错位 ----------
print("=" * 72)
print("Ⅱ.1 严格分离分析（2024 B口径）")
print("=" * 72)
print("\n【1】配对层（C(9,2)=36 对）：互补与邻近是否空间错位？（纯数据事实,非机械）")
pairs = list(itertools.combinations(CITIES, 2))
pm = [abs(d[a] - d[b]) for a, b in pairs]            # 配对镜像互补(结构跨度)
padj = [1.0 if b in ADJ[a] else 0.0 for a, b in pairs]
print(f"  corr(配对互补 mirror, 是否相邻) = {corr(pm, padj):+.4f}   (负/低=互补与邻近错位)")
order = sorted(range(len(pairs)), key=lambda i: -pm[i])
print("  互补度最高的 5 对（mirror 降序；adj=是否相邻）：")
for i in order[:5]:
    a, b = pairs[i]; print(f"     {a}-{b}: mirror={pm[i]:.3f}  相邻={'是' if padj[i] else '否'}")
fx = [i for i, (a, b) in enumerate(pairs) if {a, b} == {"福州", "厦门"}][0]
print(f"  → 福厦：mirror 排名 {sorted(range(len(pairs)),key=lambda i:-pm[i]).index(fx)+1}/36，相邻={'是' if padj[fx] else '否'}")

# ---------- 2. 组合层(84):BI vs mirror/邻近/规模/水平 ----------
print("\n【2】组合层（C(9,3)=84）：相关与偏相关")
rows = []
for combo in itertools.combinations(CITIES, 3):
    Eg, Ig = dc.agg_EI(list(combo), YEAR, E, I, pop)
    BI = sum(abs(d[c]) for c in combo) / 3 - abs(Eg - Ig)
    ds = [d[c] for c in combo]
    mirror = max(ds) - min(ds)
    pr = list(itertools.combinations(combo, 2))
    adj_ratio = sum(1 for a, b in pr if b in ADJ[a]) / 3
    size = sum(pop[(c, YEAR)] for c in combo)
    level = (Eg + Ig) / 2
    has_core = 1.0 if any(c in CORE for c in combo) else 0.0
    rows.append(dict(combo=combo, BI=BI, mirror=mirror, adj=adj_ratio, size=size, level=level, core=has_core))
BI = [r["BI"] for r in rows]; MIR = [r["mirror"] for r in rows]; ADJr = [r["adj"] for r in rows]
SZ = [r["size"] for r in rows]; LV = [r["level"] for r in rows]; CO = [r["core"] for r in rows]
print(f"  corr(BI, 互补 mirror) = {corr(BI, MIR):+.4f}   ⚠部分机械(见【4】)")
print(f"  corr(BI, 邻近 adj)    = {corr(BI, ADJr):+.4f}")
print(f"  corr(BI, 规模 size)   = {corr(BI, SZ):+.4f}")
print(f"  corr(BI, 水平 level)  = {corr(BI, LV):+.4f}")
print(f"  corr(互补 mirror, 规模 size) = {corr(MIR, SZ):+.4f}   corr(互补, 邻近)={corr(MIR, ADJr):+.4f}")
print(f"  偏相关 corr(BI, 互补 | 规模)  = {partial_corr(BI, MIR, SZ):+.4f}")
print(f"  偏相关 corr(BI, 互补 | 水平)  = {partial_corr(BI, MIR, LV):+.4f}")
print(f"  偏相关 corr(BI, 邻近 | 规模)  = {partial_corr(BI, ADJr, SZ):+.4f}")

# ---------- 3. 标准化 OLS：规模/邻近/水平同时进，互补是否存活 ----------
print("\n【3】标准化 OLS：BI ~ 互补 + 邻近 + 规模 + 水平（标准化 beta,可比）")
b = ols_std(BI, [MIR, ADJr, SZ, LV])
for name, beta in zip(["互补 mirror", "邻近 adj", "规模 size", "水平 level"], b):
    print(f"     beta[{name}] = {beta:+.4f}")

# ---------- 4. 机械性自检：剔除福厦后互补是否仍预测 BI ----------
print("\n【4】规模/双核攻击的两道防线")
pure = [r for r in rows if r["core"] == 0]
print(f"  ① 剔除福厦的纯腹地组合（n={len(pure)}）：corr(BI, 互补) = "
      f"{corr([r['BI'] for r in pure], [r['mirror'] for r in pure]):+.4f}  (仍正=非靠双核规模)")
print("  ② 诚实自检：BI 与 mirror 的相关对'城市标签置换'不变（84 组合是同 9 档案的全部 3-子集）,")
print("     故该相关是'度量+档案集'的性质、部分机械——所以本论点的硬核不在此相关,而在【1】【5】的'互补-邻近错位'。")

# ---------- 5. 置换推断：互补-邻近错位是否超出随机(合法随机化对象) ----------
print("\n【5】置换推断：把 9 个 E-I 档案随机分配到 9 个地理槽位，看'互补-邻近'关系的零分布")
random.seed(42)
obs_pair = corr(pm, padj)
obs_combo = corr(MIR, ADJr)
NP = 5000
null_pair, null_combo = [], []
slots = CITIES[:]
profiles = [d[c] for c in CITIES]
for _ in range(NP):
    perm = profiles[:]; random.shuffle(perm)
    dp = {slots[i]: perm[i] for i in range(len(slots))}
    npm = [abs(dp[a] - dp[b]) for a, b in pairs]
    null_pair.append(corr(npm, padj))
    nc = []
    for combo in itertools.combinations(CITIES, 3):
        ds = [dp[c] for c in combo]; nc.append(max(ds) - min(ds))
    null_combo.append(corr(nc, ADJr))
p_pair = sum(1 for x in null_pair if x <= obs_pair) / NP
p_combo = sum(1 for x in null_combo if x <= obs_combo) / NP
print(f"  配对层 corr(互补,邻近)={obs_pair:+.4f}；零分布均值={statistics.fmean(null_pair):+.4f}；"
      f"左尾经验 p(更负)={p_pair:.3f}")
print(f"  组合层 corr(互补,邻近)={obs_combo:+.4f}；零分布均值={statistics.fmean(null_combo):+.4f}；"
      f"左尾经验 p(更负)={p_combo:.3f}")
print("  解读：p 越小 = 观测到的'互补与邻近错位'越超出随机地理分配（即福建确实把互补对放远了）。")
print("=" * 72)
