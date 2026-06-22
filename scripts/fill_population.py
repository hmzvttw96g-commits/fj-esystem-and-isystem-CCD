#!/usr/bin/env python3
"""常住人口录入 → 广播进功能链各面板 population 列 + 校验。

人均化分母（A 域 E/I 共用）。口径要求（务必统一，见 docs/wp0_eps_取数清单_v1.md §六）：
  **全市**（非市辖区）· **常住**（非户籍）· **年末**人口，单位 **万人**。
来源策略（见对话裁定）：以能打开的**最新一卷《福建统计年鉴》为唯一主源**（七普后回溯修订、
  内部自洽、无七普断点）；缺年**往新卷退、绝不回 2020 卷以前**；2019 实在缺则 CCD 从 2020 开窗。

用法：
  python3 scripts/fill_population.py --make-template        # 出 9市×6年 空表
  人工照年鉴填 permanent_pop_10k + source 后：
  python3 scripts/fill_population.py --input <填好的.csv>   # 广播进面板 + 校验报告
  python3 scripts/fill_population.py --self-test
"""
from __future__ import annotations
import argparse, csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANELS = [ROOT / "data" / "panel" / "functional_chain" / "e_supply_scale_panel.csv",
          ROOT / "data" / "panel" / "functional_chain" / "e_supply_quality_panel.csv"]
INPUT_DIR = ROOT / "data" / "external" / "population"
TEMPLATE = INPUT_DIR / "fujian_city_population.csv"

CITIES = ["福州", "厦门", "泉州", "漳州", "莆田", "三明", "南平", "龙岩", "宁德"]
YEARS = list(range(2019, 2025))
COLS = ["city", "year", "permanent_pop_10k", "source"]

# 七普(2020)常住人口（万人）——**近似锚点，仅作软校验，请以官方年鉴为准**。
# 用途：填表后核 2020 行是否落在锚点±15%内，抓"误抄户籍/单位错"等粗错，非数据本身。
CENSUS2020_ANCHOR = {"福州": 829, "厦门": 516, "泉州": 878, "漳州": 505, "莆田": 321,
                     "三明": 249, "南平": 268, "龙岩": 272, "宁德": 315}
# 全省常住总人口（万人）——《福建统计年鉴2025》表3-1（七普后修订序列；2020=4161≈七普4154）。
# 用途：某年九市全齐时，Σ九市 应 ≈ 全省，抓"漏某市/抄错口径"。软校验，阈值2%。
PROVINCE_TOTAL = {2019: 4137, 2020: 4161, 2021: 4187, 2022: 4188, 2023: 4183, 2024: 4193}
PROV_TOL = 0.02                 # Σ九市 偏离全省 >2% 提示
MAG_LO, MAG_HI = 100, 1200      # 福建地级市常住人口合理量级（万人）
YOY_FLAG = 0.05                 # 年际变动>±5% 提示（人口缓变，超此疑typo/口径混用）


def make_template():
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(TEMPLATE, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(COLS)
        w.writerow(["# 填 permanent_pop_10k(年末常住人口,万人,全市口径) 与 source(年鉴卷次/公报)。",
                    "", "", ""])
        w.writerow(["# 2020 行可对七普核：福州≈829 厦门≈516 泉州≈878(近似,以官方为准)。",
                    "", "", ""])
        for c in CITIES:
            for y in YEARS:
                w.writerow([c, y, "", ""])
    print(f"已生成空表：{TEMPLATE.relative_to(ROOT)}（{len(CITIES)}市 × {len(YEARS)}年 = {len(CITIES)*len(YEARS)} 行）")
    print("  要填的字段只有两列：permanent_pop_10k（数字）、source（来源卷次）。city/year 已预填。")


def read_input(path):
    pop = {}
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        c = (r.get("city") or "").strip()
        if c.startswith("#") or c not in CITIES:
            continue
        try:
            y = int(r["year"]); v = (r.get("permanent_pop_10k") or "").strip()
        except (ValueError, KeyError):
            continue
        if v == "":
            continue
        pop[(c, y)] = (float(v), (r.get("source") or "").strip())
    return pop


def validate(pop):
    flags = []
    # 量级 + 单位
    for (c, y), (v, _) in sorted(pop.items()):
        if not (MAG_LO <= v <= MAG_HI):
            hint = "疑单位错(应为万人?)" if v > 5000 or v < 20 else "超合理量级"
            flags.append(f"⚠ 量级 {c}{y}={v} {hint}（万人应在{MAG_LO}-{MAG_HI}）")
    # 七普2020软锚
    for c in CITIES:
        if (c, 2020) in pop:
            v = pop[(c, 2020)][0]; a = CENSUS2020_ANCHOR[c]
            if abs(v - a) / a > 0.15:
                flags.append(f"⚠ 七普核对 {c}2020={v} 偏离近似锚点{a} >15%（核对是否误抄户籍/口径）")
    # 年际跳变
    for c in CITIES:
        seq = [(y, pop[(c, y)][0]) for y in YEARS if (c, y) in pop]
        for (y0, v0), (y1, v1) in zip(seq, seq[1:]):
            if v0 and abs(v1 - v0) / v0 > YOY_FLAG:
                flags.append(f"⚠ 跳变 {c} {y0}→{y1}: {v0}→{v1}（{(v1-v0)/v0:+.0%}，人口缓变疑typo/口径混）")
    # Σ九市 ≈ 全省（仅九市全齐的年份；抓漏市/口径错）
    for y in YEARS:
        if all((c, y) in pop for c in CITIES) and y in PROVINCE_TOTAL:
            s = sum(pop[(c, y)][0] for c in CITIES); tot = PROVINCE_TOTAL[y]
            if abs(s - tot) / tot > PROV_TOL:
                flags.append(f"⚠ 加总核 {y}: Σ九市={s:g} vs 全省{tot}（{(s-tot)/tot:+.1%}，>2%疑漏市/口径错）")
    return flags


def broadcast(pop):
    """把 (city,year)→人口 广播进各面板 population 列（不动 value/data_status）。"""
    n_set = 0
    for panel in PANELS:
        if not panel.exists():
            print(f"  （跳过不存在的面板 {panel.name}）"); continue
        rows = list(csv.DictReader(open(panel, encoding="utf-8-sig")))
        fields = rows[0].keys() if rows else ["city", "year", "caliber", "value", "population", "data_status"]
        for r in rows:
            key = (r["city"], int(r["year"]))
            if key in pop:
                r["population"] = f"{pop[key][0]:g}"; n_set += 1
        with open(panel, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(fields)); w.writeheader(); w.writerows(rows)
        print(f"  广播进 {panel.name}")
    return n_set


def run(input_path):
    pop = read_input(input_path)
    print(f"读入人口 {len(pop)}/{len(CITIES)*len(YEARS)} 个城市-年单元。")
    flags = validate(pop)
    if flags:
        print(f"\n校验提示 {len(flags)} 条（人工核对，非硬错）：")
        for fl in flags:
            print("  " + fl)
    else:
        print("校验通过：量级/七普锚/年际跳变 均无异常。")
    missing = [(c, y) for c in CITIES for y in YEARS if (c, y) not in pop]
    if missing:
        from collections import defaultdict
        byc = defaultdict(list)
        for c, y in missing:
            byc[c].append(y)
        print(f"\n缺 {len(missing)} 单元（管道按缺则跳过；补到再跑）：")
        for c, ys in byc.items():
            print(f"  {c}: {ys}")
    n = broadcast(pop)
    print(f"\n完成：population 已写入 {n} 个面板行。可跑 functional_chain_ccd_pipeline。")


def self_test():
    import tempfile, os
    rows = [["city", "year", "permanent_pop_10k", "source"]]
    # 正常福州序列 + 一个跳变 + 一个单位错
    base = {"福州": [829, 832, 844, 850, 855, 860]}
    for i, y in enumerate(YEARS):
        rows.append(["福州", y, base["福州"][i], "福建统计年鉴2025"])
    rows.append(["厦门", 2020, 5160000, "误填(人)"])      # 单位错
    rows.append(["泉州", 2019, 878, "x"]); rows.append(["泉州", 2020, 700, "x"])  # 跳变-20%
    fd, p = tempfile.mkstemp(suffix=".csv"); os.close(fd)
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerows(rows)
    pop = read_input(p)
    assert (("福州", 2019) in pop) and pop[("福州", 2019)][0] == 829
    flags = validate(pop)
    assert any("单位" in x for x in flags), "应抓到厦门单位错"
    assert any("跳变" in x and "泉州" in x for x in flags), "应抓到泉州跳变"
    assert not any("福州" in x for x in flags), "福州正常不应报错"
    os.unlink(p)
    # 加总核：2024 九市全齐。正确总量≈4193 不报；漏一市/抄错则报
    good = {(c, 2024): (v, "") for c, v in zip(CITIES, [880, 535, 890, 510, 320, 250, 268, 272, 268])}  # Σ=4193
    assert not any("加总核" in x for x in validate(good)), "正确加总不应报错"
    bad = dict(good); bad[("福州", 2024)] = (500, "")  # 福州抄成500 → Σ偏低
    assert any("加总核" in x for x in validate(bad)), "漏抓加总偏差"
    print("自测通过：量级/单位/七普锚/跳变/Σ九市≈全省 校验 + 读入 全部正确。")


def main():
    ap = argparse.ArgumentParser(description="常住人口录入广播 + 校验")
    ap.add_argument("--make-template", action="store_true")
    ap.add_argument("--input", default=None)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
    elif args.make_template:
        make_template()
    elif args.input:
        run(args.input)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
