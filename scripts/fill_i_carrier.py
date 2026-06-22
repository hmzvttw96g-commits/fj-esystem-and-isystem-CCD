#!/usr/bin/env python3
"""功能链③产业承接 录入 → 广播进 i_carrier_panel（C/B/X 同值）+ 校验。

指标（config/functional_chain.yml I_system.产业承接）：
  **信息传输、软件和信息技术服务业** 城镇单位从业人员数（中国城市统计年鉴/EPS，门类 I），单位万人。
  `caliber_invariant`：年鉴行业层无 C/B/X 细分 → 同一值填入 C/B/X 三行（B 主口径用之，C/X 并列同值）。
  下游 per_capita：进指数前除以常住人口（population 列由 fill_population 广播）。

口径要求（与 E 端/F 端一致）：**全市**·**城镇单位**从业人员（非全社会、非私营单独）·**年末/年均按年鉴口径统一**。

用法：
  python3 scripts/fill_i_carrier.py --make-template       # 9市×6年空表
  人工照 EPS 导出填 info_soft_emp_10k + source 后：
  python3 scripts/fill_i_carrier.py --input <填好的.csv>  # 广播进 i_carrier_panel + 校验
  python3 scripts/fill_i_carrier.py --self-test
"""
from __future__ import annotations
import argparse, csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "panel" / "functional_chain" / "i_carrier_panel.csv"
INPUT_DIR = ROOT / "data" / "external" / "i_carrier"
TEMPLATE = INPUT_DIR / "fujian_info_soft_employment.csv"

CITIES = ["福州", "厦门", "泉州", "漳州", "莆田", "三明", "南平", "龙岩", "宁德"]
YEARS = list(range(2019, 2025))
CALIBERS = ["C", "B", "X"]
COLS = ["city", "year", "info_soft_emp_10k", "source"]
MAG_LO, MAG_HI = 0.05, 80.0     # 信息传输软件业城镇单位从业(万人)合理量级（福厦高、小市低）
YOY_FLAG = 0.6                  # 数字产业增速可较快，>±60% 才提示（区别于人口的±5%）


def make_template():
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(TEMPLATE, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(COLS)
        w.writerow(["# 信息传输软件和信息技术服务业(门类I)城镇单位从业人员,万人,全市口径", "", "", ""])
        for c in CITIES:
            for y in YEARS:
                w.writerow([c, y, "", ""])
    print(f"已生成空表：{TEMPLATE.relative_to(ROOT)}（{len(CITIES)*len(YEARS)} 行）")
    print("  只填两列：info_soft_emp_10k（万人）、source（EPS库/年鉴卷次）。")


def read_input(path):
    val = {}
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        c = (r.get("city") or "").strip()
        if c.startswith("#") or c not in CITIES:
            continue
        try:
            y = int(r["year"]); v = (r.get("info_soft_emp_10k") or "").strip()
        except (ValueError, KeyError):
            continue
        if v == "":
            continue
        val[(c, y)] = (float(v), (r.get("source") or "").strip())
    return val


def validate(val):
    flags = []
    for (c, y), (v, _) in sorted(val.items()):
        if not (MAG_LO <= v <= MAG_HI):
            hint = "疑单位错(应万人?)" if v > 500 else "超合理量级"
            flags.append(f"⚠ 量级 {c}{y}={v} {hint}（万人应在{MAG_LO}-{MAG_HI}）")
    for c in CITIES:
        seq = [(y, val[(c, y)][0]) for y in YEARS if (c, y) in val]
        for (y0, v0), (y1, v1) in zip(seq, seq[1:]):
            if v0 and abs(v1 - v0) / v0 > YOY_FLAG:
                flags.append(f"⚠ 跳变 {c} {y0}→{y1}: {v0}→{v1}（{(v1-v0)/v0:+.0%}，核对是否口径变化）")
    return flags


def broadcast(val):
    rows = list(csv.DictReader(open(PANEL, encoding="utf-8-sig")))
    fields = list(rows[0].keys()) if rows else ["city", "year", "caliber", "value", "population", "data_status"]
    n = 0
    for r in rows:
        key = (r["city"], int(r["year"]))
        if key in val and r["caliber"] in CALIBERS:
            r["value"] = f"{val[key][0]:g}"           # C/B/X 同值（caliber_invariant）
            r["data_status"] = "calculated"
            n += 1
    with open(PANEL, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    return n


def run(input_path):
    val = read_input(input_path)
    print(f"读入产业承接 {len(val)}/{len(CITIES)*len(YEARS)} 个城市-年。")
    flags = validate(val)
    if flags:
        print(f"\n校验提示 {len(flags)} 条（人工核对）：")
        for fl in flags:
            print("  " + fl)
    else:
        print("校验通过：量级/单位/年际跳变 均无异常。")
    missing = [(c, y) for c in CITIES for y in YEARS if (c, y) not in val]
    if missing:
        from collections import defaultdict
        byc = defaultdict(list)
        for c, y in missing:
            byc[c].append(y)
        print(f"\n缺 {len(missing)} 单元（管道缺则跳过）：")
        for c, ys in byc.items():
            print(f"  {c}: {ys}")
    n = broadcast(val)
    print(f"\n完成：广播进 i_carrier_panel 的 C/B/X 三口径，共 {n} 行。population 由 fill_population 提供。")


def self_test():
    import tempfile, os
    rows = [COLS, ["福州", 2020, 12.5, "EPS城市统计年鉴"], ["福州", 2021, 14.0, "x"],
            ["厦门", 2020, 250000, "误填(人)"]]      # 单位错
    fd, p = tempfile.mkstemp(suffix=".csv"); os.close(fd)
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerows(rows)
    val = read_input(p)
    assert val[("福州", 2020)][0] == 12.5
    flags = validate(val)
    assert any("单位" in x for x in flags), "应抓厦门单位错"
    assert not any("福州" in x for x in flags), "福州正常不报"
    os.unlink(p)
    print("自测通过：读入/量级单位/跳变校验 正确。")


def main():
    ap = argparse.ArgumentParser(description="产业承接(信息传输软件业从业)录入广播")
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
