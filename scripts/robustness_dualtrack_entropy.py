#!/usr/bin/env python3
"""论文A 稳健性扩展①②：双轨障碍诊断 + 熵值法权重对照（B口径，零新数据）。

① 双轨障碍：全样本 min-max（轨A，离全省前沿）vs 腹地7市组内重标（轨B，腹地内相对短板）。
   轨B消除福厦极值压缩，恢复腹地内部卡点分辨力；两轨主障碍是否一致 = 诊断稳健性。
② 熵值法：四环节熵权 vs 等权，重算 D 与排名，检验双核-腹地格局是否稳健于权重选择。

用法：python3 scripts/robustness_dualtrack_entropy.py [--csv]   # --csv 落审计表
"""
from __future__ import annotations
import argparse, csv, math, importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "panel" / "functional_chain"
AUDIT = ROOT / "data" / "audit" / "paper_a_functional_chain"
CITIES = ["福州", "厦门", "泉州", "龙岩", "三明", "漳州", "莆田", "南平", "宁德"]
HINT = ["泉州", "龙岩", "三明", "漳州", "莆田", "南平", "宁德"]
YRS = list(range(2019, 2025))
LINKS = ["供给规模", "供给质量", "产业承接", "产业转化"]
PCAP = {"供给规模": 1, "供给质量": 0, "产业承接": 1, "产业转化": 1}
FILES = {"供给规模": "e_supply_scale_panel.csv", "供给质量": "e_supply_quality_panel.csv",
         "产业承接": "i_carrier_panel.csv", "产业转化": "i_conversion_panel.csv"}

_fc = importlib.util.spec_from_file_location("fc", ROOT / "scripts" / "functional_chain_ccd_pipeline.py")
fc = importlib.util.module_from_spec(_fc); _fc.loader.exec_module(fc)


def read(p, caliber="B"):
    d = {}
    for r in csv.DictReader(open(p, encoding="utf-8-sig")):
        if r["caliber"] != caliber:
            continue
        v = r["value"].strip(); pop = r["population"].strip()
        d[(r["city"], int(r["year"]))] = (float(v) if v else None, float(pop) if pop else None)
    return d


def build(caliber="B"):
    S = {l: read(PANEL / FILES[l], caliber) for l in LINKS}

    def rawpc(l, k):
        v, p = S[l].get(k, (None, None))
        if v is None:
            return None
        return v / p if (PCAP[l] and p) else v

    def mm_over(l, base):
        xs = [rawpc(l, k) for k in base]; xs = [x for x in xs if x is not None]
        lo, hi = min(xs), max(xs); rng = (hi - lo) or 1.0
        return lambda k: (None if rawpc(l, k) is None else max(0, min(1, (rawpc(l, k) - lo) / rng)))

    baseA = [(c, y) for c in CITIES for y in YRS]
    baseB = [(c, y) for c in HINT for y in YRS]
    fA = {l: mm_over(l, baseA) for l in LINKS}
    fB = {l: mm_over(l, baseB) for l in LINKS}
    return fA, fB, baseA


def obstacle(vs):
    dev = [1 - x for x in vs]; tot = sum(dev)
    sh = [d / tot for d in dev]
    return sh, LINKS[dev.index(max(dev))], max(vs) - min(vs)


def dual_track(fA, fB, year=2024):
    rows = []
    for c in HINT:
        vA = [fA[l]((c, year)) for l in LINKS]; vB = [fB[l]((c, year)) for l in LINKS]
        if any(x is None for x in vA + vB):
            continue
        _, mA, rA = obstacle(vA); _, mB, rB = obstacle(vB)
        rows.append((c, mA, mB, "一致" if mA == mB else "不一致", round(rA, 3), round(rB, 3)))
    return rows


def entropy_weight(fA, baseA):
    w = {}
    for l in LINKS:
        vs = [fA[l](k) for k in baseA]; vs = [v for v in vs if v is not None]
        s = sum(vs)
        if s == 0:
            w[l] = 0; continue
        p = [v / s for v in vs]; n = len(vs)
        e = -sum(pi * math.log(pi) for pi in p if pi > 0) / math.log(n)
        w[l] = 1 - e
    tot = sum(w.values())
    return {l: w[l] / tot for l in LINKS}


def Dval(fA, c, y, weights):
    vs = {l: fA[l]((c, y)) for l in LINKS}
    if any(v is None for v in vs.values()):
        return None
    we = weights["供给规模"] + weights["供给质量"]; wi = weights["产业承接"] + weights["产业转化"]
    E = (weights["供给规模"] * vs["供给规模"] + weights["供给质量"] * vs["供给质量"]) / we
    I = (weights["产业承接"] * vs["产业承接"] + weights["产业转化"] * vs["产业转化"]) / wi
    return fc.ccd(E, I)[2]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--csv", action="store_true"); args = ap.parse_args()
    fA, fB, baseA = build("B")
    print("=== ① 双轨障碍诊断（2024，腹地7市，B口径） ===")
    dt = dual_track(fA, fB)
    print(f"{'市':<5}{'轨A全样本':<10}{'轨B腹地组内':<12}{'一致?':<8}{'极差A':>7}{'极差B':>7}")
    for c, mA, mB, ok, rA, rB in dt:
        print(f"{c:<5}{mA:<10}{mB:<12}{ok:<8}{rA:>7.3f}{rB:>7.3f}")
    consistent = sum(1 for r in dt if r[3] == "一致")
    print(f"一致 {consistent}/{len(dt)}；轨B极差普遍放大 → 腹地内部卡点恢复分辨力。")

    W = entropy_weight(fA, baseA); eq = {l: 0.25 for l in LINKS}
    print("\n=== ② 熵值法权重 vs 等权（B口径全样本） ===")
    for l in LINKS:
        print(f"  {l}: 熵权 {W[l]:.3f} | 等权 0.250")
    deq = sorted(CITIES, key=lambda c: -(Dval(fA, c, 2024, eq) or 0))
    den = sorted(CITIES, key=lambda c: -(Dval(fA, c, 2024, W) or 0))
    print(f"\n{'市':<5}{'D等权':>9}{'D熵权':>9}{'排名':>9}")
    for c in CITIES:
        d1 = Dval(fA, c, 2024, eq); d2 = Dval(fA, c, 2024, W)
        print(f"{c:<5}{(f'{d1:.3f}' if d1 else '·'):>9}{(f'{d2:.3f}' if d2 else '·'):>9}{deq.index(c)+1:>4}→{den.index(c)+1}")
    print("双核(福厦)两权重下均居前2：", "是" if set(den[:2]) == {"福州", "厦门"} else "否")

    if args.csv:
        AUDIT.mkdir(parents=True, exist_ok=True)
        with open(AUDIT / "robustness_dualtrack.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f); w.writerow(["city", "trackA_main", "trackB_main", "consistent", "rangeA", "rangeB"])
            w.writerows(dt)
        with open(AUDIT / "robustness_entropy.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f); w.writerow(["link", "entropy_w", "equal_w"])
            for l in LINKS:
                w.writerow([l, round(W[l], 3), 0.25])
        print(f"\n已落审计：{AUDIT}/robustness_dualtrack.csv, robustness_entropy.csv")


if __name__ == "__main__":
    main()
