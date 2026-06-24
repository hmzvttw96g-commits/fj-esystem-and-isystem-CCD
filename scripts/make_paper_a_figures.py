#!/usr/bin/env python3
"""论文A 五图数据驱动生成（读已落审计 CSV → fig1-5），任何数据修订后重跑即自动更新。
输出至 /tmp 与 manuscripts/figures/。用法：python3 scripts/make_paper_a_figures.py
"""
import csv, math
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
AUD = ROOT / "data" / "audit" / "paper_a_functional_chain"
FP = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
fm.fontManager.addfont(FP); CJK = fm.FontProperties(fname=FP).get_name()
plt.rcParams.update({"font.family": CJK, "axes.unicode_minus": False, "figure.dpi": 150})
def F(sz): return fm.FontProperties(fname=FP, size=sz)
CITIES = ["福州", "厦门", "泉州", "漳州", "莆田", "三明", "南平", "龙岩", "宁德"]
YRS = list(range(2019, 2025))


def res():
    return list(csv.DictReader(open(AUD / "latest_functional_chain_ccd_results.csv", encoding="utf-8-sig")))


def save(fig, name):
    for d in ("/tmp", str(ROOT / "manuscripts" / "figures")):
        fig.savefig(f"{d}/{name}.png", bbox_inches="tight")
    plt.close(fig)


def fig1():
    R = res(); D = {c: {y: None for y in YRS} for c in CITIES}
    for x in R:
        if x["caliber"] == "B" and x["D"]:
            D[x["city"]][int(x["year"])] = float(x["D"])
    order = sorted(CITIES, key=lambda c: -(D[c][2024] or 0))
    M = np.array([[np.nan if D[c][y] is None else D[c][y] for y in YRS] for c in order])
    fig, ax = plt.subplots(figsize=(7, 4.3)); im = ax.imshow(M, cmap="YlGnBu", vmin=0.1, vmax=0.95, aspect="auto")
    ax.set_xticks(range(6)); ax.set_xticklabels(YRS); ax.set_yticks(range(9)); ax.set_yticklabels(order)
    for i, c in enumerate(order):
        for j, y in enumerate(YRS):
            v = D[c][y]
            ax.text(j, i, "·" if v is None else f"{v:.2f}", ha="center", va="center", fontsize=9,
                    color="#aaa" if v is None else ("white" if v > 0.55 else "#1a3a4a"))
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02); cb.set_label("耦合协调度 D", fontproperties=F(10))
    ax.set_title("图1  福建9市教育—产业耦合协调度热力图（B口径，2019—2024）", fontproperties=F(12), pad=10)
    for s in ax.spines.values(): s.set_visible(False)
    fig.tight_layout(); save(fig, "fig1_heatmap")


def fig2():
    R = {x["city"]: x for x in res() if x["caliber"] == "B" and x["year"] == "2024" and x["E_index"]}
    E = {c: float(R[c]["E_index"]) for c in CITIES}; I = {c: float(R[c]["I_index"]) for c in CITIES}
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    ax.plot([0, 1.02], [0, 1.02], "--", color="#bbb", lw=1, zorder=1)
    ax.text(0.96, 0.99, "均衡线 E=I", color="#999", fontsize=9, ha="right")
    ax.text(0.22, 0.9, "产业领先 (I>E)", color="#185FA5", fontsize=10)
    ax.text(0.62, 0.18, "教育领先 (E>I)", color="#993C1D", fontsize=10)
    hub = {"福州": "#1D9E75", "厦门": "#378ADD"}
    for c in CITIES:
        core = c in hub; ax.scatter(E[c], I[c], s=130 if core else 60, color=hub.get(c, "#D85A30"),
                                    zorder=3, edgecolor="white", linewidth=0.8)
        if core:
            ax.annotate(f"{c}\nD={float(R[c]['D']):.2f}", (E[c], I[c]), fontsize=10, fontweight="bold",
                        xytext=(-8, -6 if c == "福州" else 8), textcoords="offset points",
                        ha="right" if c == "福州" else "left", color=hub[c])
    ax.add_patch(plt.Rectangle((-0.01, -0.01), 0.30, 0.16, fill=False, ls="--", ec="#bbb", lw=1))
    ax.text(0.005, 0.17, "腹地7市·双低失调", fontsize=9, color="#888")
    for c in ["泉州", "龙岩", "宁德"]:
        ax.annotate(c, (E[c], I[c]), fontsize=8.5, color="#666", xytext=(5, 2), textcoords="offset points")
    ax.set_xlim(-0.03, 1.05); ax.set_ylim(-0.03, 1.05)
    ax.set_xlabel("教育供给指数 E（人均化·标准化）"); ax.set_ylabel("产业需求指数 I")
    ax.set_title("图2  E-I 结构与双核镜像（B口径，2024）", fontproperties=F(12), pad=10)
    fig.tight_layout(); save(fig, "fig2_scatter")


def fig3():
    R = {x["city"]: x for x in res() if x["caliber"] == "B" and x["year"] == "2024"}
    links = ["供给规模", "供给质量", "产业承接", "产业转化"]; cols = ["#378ADD", "#1D9E75", "#EF9F27", "#D85A30"]
    dk = ["#042C53", "#04342C", "#412402", "#4A1B0C"]
    order = CITIES[:]  # 同热力图序：按D
    order = sorted(CITIES, key=lambda c: -float(R[c]["D"]) if R[c]["D"] else 0)
    fig, ax = plt.subplots(figsize=(7.2, 4.3)); y = np.arange(9); left = np.zeros(9)
    rows = order[::-1]
    for li, lk in enumerate(links):
        vals = np.array([float(R[c].get(f"障碍_{lk}") or 0) * 100 for c in rows])
        ax.barh(y, vals, left=left, color=cols[li], label=lk, height=0.66)
        for i, (v, l) in enumerate(zip(vals, left)):
            if v >= 11: ax.text(l + v / 2, i, f"{round(v)}", ha="center", va="center", color="white", fontsize=8.5)
        left += vals
    ax.set_yticks(y); ax.set_yticklabels(rows); ax.set_xlim(0, 100); ax.set_xlabel("障碍度份额 (%)")
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.12), frameon=False, prop=F(9.5))
    ax.set_title("图3  障碍度四环节构成（B口径，2024）", fontproperties=F(12), pad=24)
    for s in ["top", "right"]: ax.spines[s].set_visible(False)
    fig.tight_layout(); save(fig, "fig3_obstacle")


def fig4():
    rows = list(csv.DictReader(open(AUD / "permutation_synergy.csv", encoding="utf-8-sig")))
    rows.sort(key=lambda r: -float(r["BI"])); BI = [float(r["BI"]) for r in rows]; n = len(BI)
    xi = next(i for i, r in enumerate(rows) if r["is_xzq"] == "1")
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    colors = ["#D85A30" if r["is_xzq"] == "1" else "#9FC7E8" for r in rows]
    ax.bar(range(1, n + 1), BI, color=colors, width=0.9)
    ax.axvline(n * 0.1 + 0.5, ls="--", color="#888", lw=0.8); ax.text(n * 0.1 + 1.5, max(BI) * 0.92, "前10%", fontsize=9, color="#666")
    pct = round((xi + 1) / n * 100)
    ax.annotate(f"厦门·漳州·泉州\n第{xi+1}名/{n} (前{pct}%)  BI={BI[xi]:+.3f}", xy=(xi + 1, BI[xi]),
                xytext=(xi + 14, BI[xi] + 0.03), fontsize=10, color="#993C1D", fontweight="bold",
                arrowprops=dict(arrowstyle="->", color="#D85A30", lw=1.3))
    ax.set_xlabel("84 个三市组合（按均衡改善度 BI 降序）"); ax.set_ylabel("均衡改善度 BI")
    ax.set_title("图4  厦漳泉在 84 组三市组合中的均衡改善度排位（B口径，2024）", fontproperties=F(11.5), pad=8)
    for s in ["top", "right"]: ax.spines[s].set_visible(False)
    fig.tight_layout(); save(fig, "fig4_permutation")


def fig5():
    rows = list(csv.DictReader(open(AUD / "local_link_ccd.csv", encoding="utf-8-sig")))
    rows.sort(key=lambda r: -float(r["overall_D"]))
    cols = ["overall_D", "D12_教育内部", "D34_产业内部", "D13_数量供需", "D24_质量转化"]
    labels = ["整体 D", "D₁₂\n教育内部", "D₃₄\n产业内部", "D₁₃\n数量供需", "D₂₄\n质量转化"]
    M = np.array([[float(r[c]) for c in cols] for r in rows])
    fig, ax = plt.subplots(figsize=(6.8, 4.4)); im = ax.imshow(M, cmap="YlGnBu", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(5)); ax.set_xticklabels(labels, fontsize=9.5)
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([r["city"] for r in rows])
    for i in range(len(rows)):
        for j in range(5):
            v = M[i, j]; ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8.5, color="white" if v > 0.55 else "#1a3a4a")
    ax.axvline(0.5, color="#444", lw=1.4)
    cb = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.02); cb.set_label("耦合协调度", fontproperties=F(9.5))
    ax.set_title("图5  整体 CCD 与四组功能链局部 CCD（B口径，2024）", fontproperties=F(12), pad=10)
    for s in ax.spines.values(): s.set_visible(False)
    fig.tight_layout(); save(fig, "fig5_localccd")


if __name__ == "__main__":
    for f in (fig1, fig2, fig3, fig4, fig5):
        f(); print("✓", f.__name__)
