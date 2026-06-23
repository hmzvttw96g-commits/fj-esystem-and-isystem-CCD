#!/usr/bin/env python3
"""论文A 扩展③：厦漳泉都市圈协同的三市组合穷举置换检验（B口径，零新数据）。

把"厦漳泉是否抱团"转为可检验命题：9市任选3市的全部 C(9,3)=84 组合中，厦门—漳州—泉州的
区域协同表现是否高于多数随机组合？区域聚合用**人口加权**（对人均环节恰等于"三市合并后人均"，
数学一致；标准化沿用9市原基准 → D_组 与单市 D_i 同尺度可比）。

三指标：
  D_组   = ccd(E_组, I_组)                     区域整体协调度
  RSP    = D_组 − mean(D_i)                    区域协同溢价（组团是否优于单市平均）
  BI     = mean(|E_i−I_i|) − |E_组−I_组|        均衡改善度（组团是否使供需更均衡）→ 协同互补主指标

用法：python3 scripts/permutation_test_synergy.py [--year 2024] [--csv]
"""
from __future__ import annotations
import argparse, csv, math, itertools
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "data" / "audit" / "paper_a_functional_chain" / "latest_functional_chain_ccd_results.csv"
CARR = ROOT / "data" / "panel" / "functional_chain" / "i_carrier_panel.csv"
AUDIT = ROOT / "data" / "audit" / "paper_a_functional_chain"
CITIES = ["福州", "厦门", "泉州", "漳州", "莆田", "三明", "南平", "龙岩", "宁德"]
TARGET = {"厦门", "漳州", "泉州"}


def ccd(E, I):
    if E <= 0 or I <= 0:
        return 0.0
    C = 2 * math.sqrt(E * I) / (E + I); T = (E + I) / 2
    return math.sqrt(C * T)


def load(year, caliber="B"):
    EI = {}
    for x in csv.DictReader(open(RES, encoding="utf-8-sig")):
        if x["caliber"] == caliber and int(x["year"]) == year and x["E_index"] and x["I_index"]:
            EI[x["city"]] = (float(x["E_index"]), float(x["I_index"]), float(x["D"]))
    pop = {}
    for x in csv.DictReader(open(CARR, encoding="utf-8-sig")):
        if x["caliber"] == caliber and int(x["year"]) == year and x["population"]:
            pop[x["city"]] = float(x["population"])
    return EI, pop


def run(year=2024, save_csv=False):
    EI, pop = load(year)
    rows = []
    for combo in itertools.combinations(CITIES, 3):
        if not all(c in EI and c in pop for c in combo):
            continue
        Es = [EI[c][0] for c in combo]; Is = [EI[c][1] for c in combo]
        Ds = [EI[c][2] for c in combo]; ps = [pop[c] for c in combo]
        P = sum(ps)
        Eg = sum(p * e for p, e in zip(ps, Es)) / P
        Ig = sum(p * i for p, i in zip(ps, Is)) / P
        Dg = ccd(Eg, Ig)
        RSP = Dg - sum(Ds) / 3
        BI = sum(abs(e - i) for e, i in zip(Es, Is)) / 3 - abs(Eg - Ig)
        rows.append({"combo": combo, "Dg": Dg, "RSP": RSP, "BI": BI})
    n = len(rows)
    print(f"组合总数 C(9,3)={n}（{year}年 B口径）")
    out = {}
    for key in ["Dg", "RSP", "BI"]:
        sl = sorted(rows, key=lambda x: -x[key])
        rk = next(i for i, r in enumerate(sl, 1) if set(r["combo"]) == TARGET)
        val = next(r[key] for r in rows if set(r["combo"]) == TARGET)
        out[key] = (rk, val)
        print(f"  厦漳泉 {key:<4} 排名 {rk}/{n}（前{rk/n*100:.0f}%）值={val:+.4f}")
    top = sorted(rows, key=lambda x: -x["BI"])[:max(1, n // 10)]
    freq = Counter(c for r in top for c in r["combo"])
    print(f"  进入 BI 前{len(top)}（前10%）高均衡组合的城市频次：{freq.most_common()}")
    if save_csv:
        AUDIT.mkdir(parents=True, exist_ok=True)
        with open(AUDIT / "permutation_synergy.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f); w.writerow(["combo", "Dg", "RSP", "BI", "is_xzq"])
            for r in sorted(rows, key=lambda x: -x["BI"]):
                w.writerow(["·".join(r["combo"]), round(r["Dg"], 4), round(r["RSP"], 4),
                            round(r["BI"], 4), int(set(r["combo"]) == TARGET)])
        print(f"  已落审计：{AUDIT}/permutation_synergy.csv")
    return rows, out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2024)
    ap.add_argument("--csv", action="store_true")
    a = ap.parse_args()
    run(a.year, a.csv)
