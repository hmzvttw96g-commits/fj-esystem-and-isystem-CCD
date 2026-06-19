#!/usr/bin/env python3
"""从 CnOpenData「中国工商注册企业全生命周期统计数据」整包，过滤出产业承接(B口径)面板。

口径(冻结文档 i_caliber_firm B口径 = 行业大类 64/65)：
  - 省份编码=35(福建) × 大类编码∈{64,65} × 会计年度∈2019–2024 × 企业性质剔"个体户"
  - 产业承接存量 = `在业企业数量`(在业=存续/存量)；同一城市×年跨"注册资本范围×注册年份范围×大类"子行加总
  - 输出填入 data/panel/functional_chain/i_carrier_panel.csv 的 caliber=B 行(value=在业数；population 待你从年鉴补)
  - C/X 口径需经营范围关键词(微观明细),本表给不了 → 标 pending_microdata，留空

纯标准库，流式读(整包很大也只留福建64/65子集)。CnOpenData 列名以实测为准，
脚本对常见别名做了容错；遇未知表头会报出供核对。

用法：
  python3 scripts/cnopendata_carrier_filter.py --self-test
  python3 scripts/cnopendata_carrier_filter.py --input <整包csv或解压目录>
"""
from __future__ import annotations
import argparse, csv, glob, sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "panel" / "functional_chain" / "i_carrier_panel.csv"
AUDIT = ROOT / "data" / "audit" / "cnopendata_carrier"
FUJIAN_9 = ["福州", "厦门", "泉州", "漳州", "莆田", "三明", "南平", "龙岩", "宁德"]
B_DALEI = {"64", "65"}           # 互联网和相关服务 / 软件和信息技术服务业
YEARS = set(range(2019, 2025))
PROV_FUJIAN = "35"

# 列名容错（实测主名 + 可能别名）
COLS = {
    "year": ["会计年度", "年份", "year"],
    "prov_code": ["省份编码", "省份代码", "省代码"],
    "city": ["城市", "城市名称"],
    "nature": ["企业性质", "登记注册类型"],
    "dalei_code": ["大类编码", "大类代码", "行业大类代码"],
    "active": ["在业企业数量", "在营企业数量", "存续企业数量"],
    "cancel": ["注销企业数量"],
}


def _pick(header, keys):
    for k in keys:
        if k in header:
            return k
    return None


def _norm_city(s):
    s = (s or "").strip()
    return s[:-1] if s.endswith("市") else s


def _open(path):
    for enc in ("utf-8-sig", "gb18030", "utf-8"):
        try:
            f = open(path, encoding=enc, newline="")
            f.readline(); f.seek(0)
            return f
        except (UnicodeDecodeError, LookupError):
            continue
    return open(path, encoding="utf-8", errors="ignore", newline="")


def process_file(path, agg):
    f = _open(path)
    rd = csv.DictReader(f)
    header = rd.fieldnames or []
    cols = {k: _pick(header, names) for k, names in COLS.items()}
    missing = [k for k in ("year", "city", "dalei_code", "active") if not cols[k]]
    if missing:
        print(f"  ⚠ {Path(path).name} 缺关键列 {missing}；实际表头：{header[:14]}…")
        f.close(); return 0
    kept = 0
    for r in rd:
        if cols["prov_code"] and (r.get(cols["prov_code"]) or "").strip() != PROV_FUJIAN:
            continue
        dl = (r.get(cols["dalei_code"]) or "").strip()
        if dl not in B_DALEI:
            continue
        try:
            y = int(float(r.get(cols["year"]) or ""))
        except ValueError:
            continue
        if y not in YEARS:
            continue
        nat = r.get(cols["nature"]) if cols["nature"] else ""
        if nat and "个体" in nat:          # 剔个体工商户，保留企业(法人)
            continue
        city = _norm_city(r.get(cols["city"]))
        if city not in FUJIAN_9:
            continue
        try:
            active = int(float(r.get(cols["active"]) or 0))
        except ValueError:
            active = 0
        cancel = 0
        if cols["cancel"]:
            try:
                cancel = int(float(r.get(cols["cancel"]) or 0))
            except ValueError:
                cancel = 0
        agg[(city, y)]["active"] += active
        agg[(city, y)]["cancel"] += cancel
        agg[(city, y)]["by_dalei"][dl] += active
        kept += 1
    f.close()
    return kept


def write_panel(agg):
    # 更新 i_carrier_panel.csv 的 caliber=B 行（value=在业数；其它列保留）
    if not PANEL.exists():
        print(f"⚠ 面板模板不存在：{PANEL}\n  先跑 functional_chain_ccd_pipeline.py --make-templates")
        return
    rows = list(csv.DictReader(open(PANEL, encoding="utf-8-sig")))
    for r in rows:
        if r["caliber"] == "B":
            key = (r["city"].strip(), int(r["year"]))
            if key in agg:
                r["value"] = agg[key]["active"]
                r["data_status"] = "calculated"
            else:
                r["data_status"] = "missing"
        elif r["caliber"] in ("C", "X") and not (r.get("data_status") or "").strip():
            r["data_status"] = "pending_microdata"   # C/X 需经营范围关键词，本表给不了
    with open(PANEL, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["city", "year", "caliber", "value", "population", "data_status"])
        w.writeheader(); w.writerows(rows)
    print(f"已更新 {PANEL.relative_to(ROOT)} 的 B 口径 value（population 待你从年鉴补）。")


def write_audit(agg, run_id, inputs):
    out = AUDIT / run_id
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"carrier_breakdown_{run_id}.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["city", "year", "在业_64", "在业_65", "在业_B合计", "注销_B合计"])
        for (city, y) in sorted(agg):
            d = agg[(city, y)]
            w.writerow([city, y, d["by_dalei"].get("64", 0), d["by_dalei"].get("65", 0),
                        d["active"], d["cancel"]])
    (AUDIT / "latest_carrier_breakdown.csv").write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"明细审计：{path.relative_to(ROOT)}")


def run(input_path):
    p = Path(input_path)
    files = []
    if p.is_dir():
        files = sorted(glob.glob(str(p / "**" / "*.csv"), recursive=True))
    elif p.suffix.lower() == ".csv":
        files = [str(p)]
    else:
        print("请传 CSV 文件或解压后的目录（含 csv）。"); return
    if not files:
        print(f"未找到 CSV：{input_path}"); return
    agg = defaultdict(lambda: {"active": 0, "cancel": 0, "by_dalei": defaultdict(int)})
    total = 0
    for fp in files:
        k = process_file(fp, agg)
        print(f"  {Path(fp).name}: 命中福建64/65企业行 {k}")
        total += k
    if total == 0:
        print("未命中任何福建 64/65 企业行——核对整包是否含福建、列名是否匹配。"); return
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    write_audit(agg, run_id, files)
    write_panel(agg)
    print(f"\n完成。覆盖城市年单元 {len(agg)}（应≤54=9市×6年；缺的为该市该年无64/65在业企业，属真零须人工确认）。")


def self_test():
    import tempfile, os
    print("== 过滤脚本自检（合成整包）==")
    rows = [
        # 福建·软件(65)·企业·2020 两个资本档 → 应加总 10+5=15
        ["2020", "35", "福州市", "工商-企业", "65", "10", "1"],
        ["2020", "35", "福州市", "工商-企业", "65", "5", "0"],
        # 福建·互联网(64)·企业·2020 → 3，与上面65合并B=18
        ["2020", "35", "福州市", "工商-企业", "64", "3", "0"],
        # 个体户应剔除
        ["2020", "35", "福州市", "工商-个体户", "65", "99", "0"],
        # 非福建应剔除
        ["2020", "11", "北京市", "工商-企业", "65", "88", "0"],
        # 非64/65应剔除
        ["2020", "35", "厦门市", "工商-企业", "13", "77", "0"],
        # 厦门软件2021 → 7
        ["2021", "35", "厦门市", "工商-企业", "65", "7", "2"],
    ]
    fd, tmp = tempfile.mkstemp(suffix=".csv"); os.close(fd)
    with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["会计年度", "省份编码", "城市", "企业性质", "大类编码", "在业企业数量", "注销企业数量"])
        w.writerows(rows)
    agg = defaultdict(lambda: {"active": 0, "cancel": 0, "by_dalei": defaultdict(int)})
    process_file(tmp, agg)
    os.unlink(tmp)
    fz = agg.get(("福州", 2020), {}).get("active")
    xm = agg.get(("厦门", 2021), {}).get("active")
    bj = ("北京", 2020) in agg
    ok = fz == 18 and xm == 7 and not bj and ("厦门", 2020) not in agg
    print(f"  福州2020在业B={fz}(应18, 含64+65、剔个体户)  厦门2021={xm}(应7)  剔非闽/非64-65/个体户:{not bj}")
    print("自检", "通过 ✓" if ok else "失败 ✗")
    return ok


def main():
    ap = argparse.ArgumentParser(description="CnOpenData 全生命周期 → 产业承接B口径")
    ap.add_argument("--input", help="整包 CSV 文件或解压目录")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        raise SystemExit(0 if self_test() else 1)
    if not args.input:
        ap.error("需 --input <csv或目录> 或 --self-test")
    run(args.input)


if __name__ == "__main__":
    main()
