#!/usr/bin/env python3
"""论文A 扩展②：功能链局部耦合协调检验（Link-level CCD，B口径，零新数据）。

整体 E-I CCD 可能掩盖链节断裂。对四环节两两构造局部 CCD，识别"哪两环节之间错配"：
  D12=CCD(供给规模,供给质量)  教育内部     D34=CCD(产业承接,产业转化)  产业内部
  D13=CCD(供给规模,产业承接)  数量供需     D24=CCD(供给质量,产业转化)  质量转化
（D14、D23 理论意义弱，入附录，不在主文。）公式同整体 CCD：D=√(K·T)，K=2√(ab)/(a+b)、T=(a+b)/2。
按"整体 D × 局部 D"关系分型：全链协调 / 总体协调但局部断裂 / 局部优势总体低位 / 全链低位。
⚠ 局部 CCD 同吃 min-max 压缩（腹地被水平 T 主导而普遍偏低）+ 零值（某环节标准化=0 → CCD=0，
   如莆田/宁德供给质量=0 致 D12/D24=0，表"质量链节断裂"）；故提供腹地组内双轨作稳健。

用法：python3 scripts/local_link_ccd.py [--year 2024] [--csv] [--self-test]
"""
from __future__ import annotations
import argparse, csv, math, importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "panel" / "functional_chain"
RES = ROOT / "data" / "audit" / "paper_a_functional_chain" / "latest_functional_chain_ccd_results.csv"
AUDIT = ROOT / "data" / "audit" / "paper_a_functional_chain"
CITIES = ["福州", "厦门", "泉州", "龙岩", "三明", "漳州", "莆田", "南平", "宁德"]
HINT = CITIES[2:]
YRS = list(range(2019, 2025))
PCAP = {"供给规模": 1, "供给质量": 0, "产业承接": 1, "产业转化": 1}
FILES = {"供给规模": "e_supply_scale_panel", "供给质量": "e_supply_quality_panel",
         "产业承接": "i_carrier_panel", "产业转化": "i_conversion_panel"}
PAIRS = [("D12", "供给规模", "供给质量", "教育内部"), ("D34", "产业承接", "产业转化", "产业内部"),
         ("D13", "供给规模", "产业承接", "数量供需"), ("D24", "供给质量", "产业转化", "质量转化")]


def CCD(a, b):
    if a is None or b is None or a <= 0 or b <= 0:
        return 0.0
    K = 2 * math.sqrt(a * b) / (a + b); T = (a + b) / 2
    return math.sqrt(K * T)


def _read(name):
    d = {}
    for r in csv.DictReader(open(PANEL / f"{name}.csv", encoding="utf-8-sig")):
        if r["caliber"] != "B":
            continue
        v = r["value"].strip(); pop = r["population"].strip()
        d[(r["city"], int(r["year"]))] = (float(v) if v else None, float(pop) if pop else None)
    return d


def _standardizers(base):
    S = {k: _read(v) for k, v in FILES.items()}

    def pc(l, k):
        v, p = S[l].get(k, (None, None))
        return None if v is None else (v / p if (PCAP[l] and p) else v)

    def mm(l):
        xs = [pc(l, k) for k in base]; xs = [x for x in xs if x is not None]
        lo, hi = min(xs), max(xs); rng = (hi - lo) or 1.0
        return lambda k: (None if pc(l, k) is None else max(0, min(1, (pc(l, k) - lo) / rng)))
    return {l: mm(l) for l in FILES}


def local_ccds(city, year, f):
    v = {l: f[l]((city, year)) for l in FILES}
    return {code: CCD(v[a], v[b]) for code, a, b, _ in PAIRS}


def classify(overall, locs, hi=0.5):
    vals = list(locs.values()); mn, mx = min(vals), max(vals)
    if overall >= hi:
        return "全链协调型" if mn >= hi else f"总体协调但局部断裂（{min(locs, key=locs.get)}低）"
    return f"局部优势总体低位（{max(locs, key=locs.get)}高）" if mx >= hi else "全链低位型"


def run(year=2024, save=False):
    fA = _standardizers([(c, y) for c in CITIES for y in YRS])
    overall = {x["city"]: float(x["D"]) for x in csv.DictReader(open(RES, encoding="utf-8-sig"))
               if x["caliber"] == "B" and int(x["year"]) == year and x["D"]}
    print(f"=== 功能链局部 CCD（{year} B口径，全样本标准化）===")
    print(f"{'市':<5}{'整体D':>7}{'D12教育内':>9}{'D34产业内':>9}{'D13数量供需':>11}{'D24质量转化':>11}  分型")
    rows = []
    for c in CITIES:
        locs = local_ccds(c, year, fA); D = overall.get(c, 0)
        t = classify(D, locs)
        rows.append({"city": c, "D": D, **locs, "type": t})
        print(f"{c:<5}{D:>7.3f}{locs['D12']:>9.3f}{locs['D34']:>9.3f}{locs['D13']:>11.3f}{locs['D24']:>11.3f}  {t}")
    # 腹地组内双轨(对腹地市)
    fB = _standardizers([(c, y) for c in HINT for y in YRS])
    print("\n腹地组内双轨(剔福厦重标，看腹地内部链节结构)：")
    print(f"{'市':<5}{'D12':>7}{'D34':>7}{'D13':>7}{'D24':>7}  组内最弱链节")
    for c in HINT:
        locs = local_ccds(c, year, fB)
        print(f"{c:<5}{locs['D12']:>7.3f}{locs['D34']:>7.3f}{locs['D13']:>7.3f}{locs['D24']:>7.3f}  {min(locs, key=locs.get)}")
    if save:
        AUDIT.mkdir(parents=True, exist_ok=True)
        with open(AUDIT / "local_link_ccd.csv", "w", newline="", encoding="utf-8-sig") as fp:
            w = csv.writer(fp); w.writerow(["city", "overall_D", "D12_教育内部", "D34_产业内部", "D13_数量供需", "D24_质量转化", "type"])
            for r in rows:
                w.writerow([r["city"], round(r["D"], 4), round(r["D12"], 4), round(r["D34"], 4),
                            round(r["D13"], 4), round(r["D24"], 4), r["type"]])
        print(f"\n已落审计：{AUDIT}/local_link_ccd.csv")
    return rows


def self_test():
    assert abs(CCD(1.0, 1.0) - 1.0) < 1e-9, "完全均衡且满分→1"
    assert CCD(0.0, 0.5) == 0.0, "零值→0"
    assert CCD(0.5, 0.5) < CCD(1.0, 1.0), "同均衡低水平 D 更低（T 主导）"
    # 均衡但低 vs 不均衡：K 测均衡
    assert CCD(0.4, 0.4) > CCD(0.4, 0.1), "同水平下越均衡 D 越高"
    print("自测通过：CCD 公式（满分/零值/水平主导/均衡）正确。")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2024); ap.add_argument("--csv", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        self_test()
    else:
        run(a.year, a.csv)


if __name__ == "__main__":
    main()
