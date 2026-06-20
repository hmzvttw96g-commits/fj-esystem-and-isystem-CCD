#!/usr/bin/env python3
"""功能链②供给质量 归并管道：一流本科专业建设点(主) + 硕博学位授权点(增量) → 复合质量面板。

设计依据 config/e_caliber_quality.yml（v1.0-draft）：
  复合 = first_class_major(0.6) + degree_point(0.4)；一流专业为主成分。
  一流专业 tier 权重 国家级1.0/省级0.5；学位点 level 权重 博1.0/硕0.6/专硕0.5。
  **非人口人均化**（项目点计数类）；本管道内对两成分各自 min-max 后按 0.6/0.4 复合。
  该环节近乎时间不变——贡献横截面水平、几乎不贡献趋势。

口径分类：
  一流专业 按 **专业名** → C/B/X（复用 e_caliber_majors，home_caliber）。
  学位点   按 **学科名** → C/B/X（e_caliber_quality.discipline_caliber_map，学科≠本科专业）。
  二者均 C⊂B⊂X 嵌套；某口径 k 的值 = 该口径及更窄口径项目点的加权累计。

累计语义：一流专业/学位点一经设立长期有效 → 按 designation_year/active_from_year 起**累计**到各年。

数据须人工采集（公开名单，**不得杜撰**）：
  python3 scripts/e_supply_quality_pipeline.py --make-templates   # 出两张空模板(预列福建校)
  人工填好后：
  python3 scripts/e_supply_quality_pipeline.py --first-class <fcm.csv> --degree <deg.csv>
  自测：python3 scripts/e_supply_quality_pipeline.py --self-test
"""
from __future__ import annotations
import argparse, csv, importlib.util
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG_QUAL = ROOT / "config" / "e_caliber_quality.yml"
PANEL = ROOT / "data" / "panel" / "functional_chain" / "e_supply_quality_panel.csv"
TEMPLATE_DIR = ROOT / "data" / "external" / "e_supply_quality"   # 原料(gitignore)，人工填

CITIES = ["福州", "厦门", "泉州", "漳州", "莆田", "三明", "南平", "龙岩", "宁德"]
YEARS = list(range(2019, 2025))
CALIBERS = ["C", "B", "X"]
RANK = {"C": 0, "B": 1, "X": 2}

FCM_COLS = ["school", "city", "major_standard", "tier", "designation_year"]
DEG_COLS = ["school", "city", "discipline", "discipline_code", "level", "active_from_year"]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def load_qual_cfg():
    import yaml
    q = yaml.safe_load(open(CFG_QUAL, encoding="utf-8"))
    w = q.get("composite_weights") or q["meta"].get("composite_weights", {"first_class_major": 0.6, "degree_point": 0.4})
    tier_w = q["first_class_major"]["tier_weights"]
    lvl_w = q["degree_point"]["level_weights"]
    # 学科 → C/B/X 映射（嵌套展开）
    dmap = q["degree_point"]["discipline_caliber_map"]
    disc2cal = {}
    cset = [d["discipline"] for d in dmap["C_conservative"]]
    bset = cset + [d["discipline"] for d in dmap["B_basic"]["additional"]]
    xset = bset + [d["discipline"] for d in dmap["X_expanded"]["additional"]]
    for d in cset: disc2cal[d] = "C"
    for d in dmap["B_basic"]["additional"]: disc2cal[d["discipline"]] = "B"
    for d in dmap["X_expanded"]["additional"]: disc2cal[d["discipline"]] = "X"
    return w, tier_w, lvl_w, disc2cal


def wlookup(wmap, key):
    """容差权重查：精确→子串（兼容 博士/博士点、专业学位/专业学位点、国家级一流/国家级）。"""
    key = (key or "").strip()
    if key in wmap:
        return wmap[key]
    for k, v in wmap.items():
        if key and (key in k or k in key):
            return v
    return 0.0


def discipline_caliber(name, disc2cal):
    """学科名 → C/B/X（子串兜底，因学位点常带方向后缀，如'电子信息(人工智能方向)'）。"""
    if name in disc2cal:
        return disc2cal[name]
    for d, cal in disc2cal.items():
        if d in name or name in d:
            return cal
    return None


def minmax(vals):
    xs = [v for v in vals if v is not None]
    if not xs:
        return {}
    lo, hi = min(xs), max(xs)
    if hi == lo:
        return {i: (0.0 if hi == 0 else 1.0) for i, v in enumerate(vals)}
    return {i: (v - lo) / (hi - lo) if v is not None else None for i, v in enumerate(vals)}


def aggregate(fcm_rows, deg_rows, scale_pipe, qual_cfg):
    """→ {(city,year,caliber): {'fcm':加权累计, 'deg':加权累计}}（嵌套）。

    **升级感知**：同一专业点(同城同校同专业)可能多次认定(省级→国家级)。某年该点的有效权重
    = 该年及之前**最新一次**认定的 tier 权重（取代、非累加），避免升级被重复计数。不同专业点求和。
    城市归属：优先用录入文件给定的 city（已 campus 级归市，如华侨大学厦门/泉州分校），
    其不在福建9市时再回退 name2city。"""
    C, Badd, Xadd, broad, _ = scale_pipe.load_calibers()
    name2city, former2cur, _ = scale_pipe.load_schools()
    _, tier_w, lvl_w, disc2cal = qual_cfg
    cell = defaultdict(lambda: {"fcm": 0.0, "deg": 0.0})

    def city_of(school, given):
        if given in CITIES:                       # 录入文件 campus 级归市优先（华侨大学分校）
            return given
        return name2city.get(former2cur.get(school, school))

    def accumulate(rows, comp, cal_fn, wmap, year_key):
        # 先按"专业点"分组收集 (认定年, tier/level)，再按年取最新认定 → 升级感知
        points = defaultdict(list)   # (city, cal, school, item) -> [(year, label)]
        for r in rows:
            item = r.get("major_standard") or r.get("discipline") or ""
            cal = cal_fn(item)
            if cal is None:
                continue
            city = city_of(r["school"], r.get("city"))
            if city not in CITIES:
                continue
            try:
                ry = int(r[year_key])
            except (ValueError, TypeError, KeyError):
                continue
            label = (r.get("tier") or r.get("level") or "").strip()
            points[(city, cal, r["school"], item)].append((ry, label))
        for (city, cal, _sch, _it), evs in points.items():
            evs.sort()
            for y in YEARS:
                active = [lab for (ry, lab) in evs if ry <= y]
                if not active:
                    continue
                w = wlookup(wmap, active[-1])     # 该年最新一次认定的 tier/level
                for k in CALIBERS:
                    if RANK[cal] <= RANK[k]:
                        cell[(city, y, k)][comp] += w

    accumulate(fcm_rows, "fcm",
               lambda m: scale_pipe.home_caliber(m, C, Badd, Xadd, broad),
               tier_w, "designation_year")
    accumulate(deg_rows, "deg",
               lambda d: discipline_caliber(d, disc2cal),
               lvl_w, "active_from_year")
    return cell


def build_panel(cell, qual_cfg):
    """两成分各自 min-max（按口径分组）→ 复合 0.6/0.4 → panel 行。"""
    w, *_ = qual_cfg
    wf, wd = w["first_class_major"], w["degree_point"]
    rows_out = []
    for k in CALIBERS:
        keys = [(c, y) for c in CITIES for y in YEARS]
        fcm = [cell.get((c, y, k), {}).get("fcm", 0.0) for (c, y) in keys]
        deg = [cell.get((c, y, k), {}).get("deg", 0.0) for (c, y) in keys]
        fmm, dmm = minmax(fcm), minmax(deg)
        for i, (c, y) in enumerate(keys):
            has = (c, y, k) in cell
            comp = wf * (fmm.get(i) or 0.0) + wd * (dmm.get(i) or 0.0)
            rows_out.append({"city": c, "year": y, "caliber": k,
                             "value": f"{comp:.4f}" if has else "",
                             "population": "", "data_status": "calculated" if has else "missing"})
    rows_out.sort(key=lambda r: (CITIES.index(r["city"]), r["year"], CALIBERS.index(r["caliber"])))
    return rows_out


def write_panel(rows_out):
    PANEL.parent.mkdir(parents=True, exist_ok=True)
    with open(PANEL, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["city", "year", "caliber", "value", "population", "data_status"])
        w.writeheader(); w.writerows(rows_out)


def make_templates():
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    scale_pipe = _load("e_supply_scale_pipeline")
    name2city, _, _ = scale_pipe.load_schools()
    fcm_p = TEMPLATE_DIR / "first_class_major_points.csv"
    deg_p = TEMPLATE_DIR / "degree_points.csv"
    with open(fcm_p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(FCM_COLS)
        w.writerow(["# 示例(删):福州大学", "福州", "计算机科学与技术", "国家级", "2019"])
        for sch, city in sorted(name2city.items(), key=lambda x: (CITIES.index(x[1]) if x[1] in CITIES else 9, x[0])):
            if city in CITIES:
                w.writerow([sch, city, "", "", ""])
    with open(deg_p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(DEG_COLS)
        w.writerow(["# 示例(删):厦门大学", "厦门", "计算机科学与技术", "0812", "博士", "2018"])
        for sch, city in sorted(name2city.items(), key=lambda x: (CITIES.index(x[1]) if x[1] in CITIES else 9, x[0])):
            if city in CITIES:
                w.writerow([sch, city, "", "", "", ""])
    print(f"已生成模板（人工填官方名单，勿杜撰）：\n  {fcm_p.relative_to(ROOT)}\n  {deg_p.relative_to(ROOT)}")
    print(f"  tier 填 国家级/省级；level 填 博士/硕士/专业学位；year 填批次/设立年。")
    print(f"  填好后：python3 scripts/e_supply_quality_pipeline.py --first-class {fcm_p.relative_to(ROOT)} --degree {deg_p.relative_to(ROOT)}")


def read_rows(path, cols):
    out = []
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        if (r.get("school") or "").lstrip().startswith("#"):
            continue
        if not (r.get("school") or "").strip():
            continue
        out.append({c: (r.get(c) or "").strip() for c in cols})
    return out


def run(fcm_path, degree_path):
    scale_pipe = _load("e_supply_scale_pipeline")
    qual_cfg = load_qual_cfg()
    fcm = read_rows(fcm_path, FCM_COLS) if fcm_path else []
    deg = read_rows(degree_path, DEG_COLS) if degree_path else []
    print(f"读入：一流专业点 {len(fcm)} 条；学位点 {len(deg)} 条。")
    cell = aggregate(fcm, deg, scale_pipe, qual_cfg)
    rows_out = build_panel(cell, qual_cfg)
    # 学位点缺省时标注：当前复合仅含一流专业成分(0.6权重，CCD自身min-max对此尺度不变)
    if not any(v["deg"] for v in cell.values()):
        for r in rows_out:
            if r["data_status"] == "calculated":
                r["data_status"] = "first_class_only(degree_pending)"
    write_panel(rows_out)
    filled = sum(1 for r in rows_out if r["value"])
    print(f"已填 {PANEL.relative_to(ROOT)}：{filled}/{len(rows_out)} 单元（复合质量 0–1）。")
    # 预览 B 口径
    print("B口径复合质量(预览)：")
    for c in CITIES:
        line = f"  {c:<4}"
        for y in YEARS:
            v = next((r["value"] for r in rows_out if r["city"] == c and r["year"] == y and r["caliber"] == "B"), "")
            line += f"{(v or '·'):>8}"
        print(line)


def self_test():
    """合成数据验证：复合、嵌套、累计、min-max 全链路。"""
    scale_pipe = _load("e_supply_scale_pipeline")
    qual_cfg = load_qual_cfg()
    fcm = [
        {"school": "福州大学", "city": "福州", "major_standard": "人工智能", "tier": "国家级", "designation_year": "2020"},
        {"school": "福州大学", "city": "福州", "major_standard": "软件工程", "tier": "省级", "designation_year": "2019"},
        {"school": "厦门大学", "city": "厦门", "major_standard": "计算机科学与技术", "tier": "国家级", "designation_year": "2019"},
        # 升级事件：泉州师院 计算机 省级2019 → 国家级2021（同一点，须取最新非累加）
        {"school": "泉州师范学院", "city": "泉州", "major_standard": "计算机科学与技术", "tier": "省级", "designation_year": "2019"},
        {"school": "泉州师范学院", "city": "泉州", "major_standard": "计算机科学与技术", "tier": "国家级", "designation_year": "2021"},
    ]
    deg = [
        {"school": "厦门大学", "city": "厦门", "discipline": "计算机科学与技术", "discipline_code": "0812", "level": "博士", "active_from_year": "2018"},
    ]
    cell = aggregate(fcm, deg, scale_pipe, qual_cfg)
    # 断言1：福州C口径 2019 fcm=0（人工智能2020才设），2020 起 fcm=1.0(国家级)
    assert abs(cell[("福州", 2019, "C")]["fcm"] - 0.0) < 1e-9, cell[("福州", 2019, "C")]
    assert abs(cell[("福州", 2020, "C")]["fcm"] - 1.0) < 1e-9, cell[("福州", 2020, "C")]
    # 断言2：福州B口径 2019 含软件工程省级0.5；2020 含 +人工智能国家级1.0 = 1.5
    assert abs(cell[("福州", 2019, "B")]["fcm"] - 0.5) < 1e-9, cell[("福州", 2019, "B")]
    assert abs(cell[("福州", 2020, "B")]["fcm"] - 1.5) < 1e-9, cell[("福州", 2020, "B")]
    # 断言3：嵌套——软件工程(B)不进C口径
    assert abs(cell[("福州", 2019, "C")]["fcm"] - 0.0) < 1e-9
    # 断言4：厦门B口径 deg 含博士1.0
    assert abs(cell[("厦门", 2019, "B")]["deg"] - 1.0) < 1e-9, cell[("厦门", 2019, "B")]
    # 断言5：升级感知——泉州计算机 2019/2020 取省级0.5，2021 起取国家级1.0（非 0.5+1.0=1.5）
    assert abs(cell[("泉州", 2020, "B")]["fcm"] - 0.5) < 1e-9, cell[("泉州", 2020, "B")]
    assert abs(cell[("泉州", 2021, "B")]["fcm"] - 1.0) < 1e-9, cell[("泉州", 2021, "B")]
    # 断言6：复合面板值 ∈[0,1]
    rows_out = build_panel(cell, qual_cfg)
    for r in rows_out:
        if r["value"]:
            assert 0.0 <= float(r["value"]) <= 1.0, r
    print("自测通过：累计/嵌套/tier&level加权/min-max复合 全部正确。")


def main():
    ap = argparse.ArgumentParser(description="功能链②供给质量 归并管道")
    ap.add_argument("--make-templates", action="store_true")
    ap.add_argument("--first-class", default=None)
    ap.add_argument("--degree", default=None)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
    elif args.make_templates:
        make_templates()
    elif args.first_class or args.degree:
        run(args.first_class, args.degree)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
