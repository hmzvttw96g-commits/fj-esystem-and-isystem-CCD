#!/usr/bin/env python3
"""四环节功能链 CCD 与障碍度管道。

读 config/functional_chain.yml，从四个环节面板构造 E_index/I_index，
计算 CCD(E,I)、C、T、障碍度四环节分解，导出城市类型/路径/瓶颈读数。
参数全读 config，禁止硬编码城市/年份；run_id/manifest/latest_ 纪律。

四环节面板（data/panel/functional_chain/*.csv）列：
  city, year, caliber(C/B/X), value, population
  - per_capita 环节：进指数前 value/population；capacity 环节（供给质量）：直接用 value。
  - 标准化按 caliber 分别做（C/B/X 不同尺度）。任一指数为 0 → CCD 不可计算。

用法：
  python3 scripts/functional_chain_ccd_pipeline.py --self-test       # 内核自检（纯标准库）
  python3 scripts/functional_chain_ccd_pipeline.py --make-templates  # 生成4个空白面板模板（9市×年×C/B/X）
  python3 scripts/functional_chain_ccd_pipeline.py --run             # 读真实面板出结果
"""
from __future__ import annotations
import argparse, csv, json, math, statistics
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("需要 pyyaml：pip3 install --user pyyaml")

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "functional_chain.yml"
PANEL_DIR = ROOT / "data" / "panel" / "functional_chain"
OUT_DIR = ROOT / "data" / "audit" / "paper_a_functional_chain"
CALIBERS = ["C", "B", "X"]
FUJIAN_9 = ["福州", "厦门", "泉州", "漳州", "莆田", "三明", "南平", "龙岩", "宁德"]
YEARS = list(range(2019, 2025))
CCD_BINS = [(0.1, "极度失调"), (0.2, "严重失调"), (0.3, "中度失调"), (0.4, "轻度失调"),
            (0.5, "濒临失调"), (0.6, "勉强协调"), (0.7, "初级协调"), (0.8, "中级协调"),
            (0.9, "良好协调"), (1.01, "优质协调")]


# ---------------- 统计内核（纯标准库，可自检） ----------------
def minmax(values, lo=None, hi=None):
    """全样本固定基准 min-max；锚点可外部传入（经审计签字）。"""
    xs = [v for v in values if v is not None]
    if not xs:
        return [None] * len(values), None, None
    lo = min(xs) if lo is None else lo
    hi = max(xs) if hi is None else hi
    rng = (hi - lo) or 1.0
    return [None if v is None else max(0.0, min(1.0, (v - lo) / rng)) for v in values], lo, hi


def equal_weight(*cols):
    """等权合成已标准化的环节列；任一为 None → 该单元 None（不可计算）。"""
    return [None if any(v is None for v in row) else sum(row) / len(row) for row in zip(*cols)]


def ccd(e, i):
    """耦合协调度，返回 (C, T, D)。C=2√(EI)/(E+I)，T=(E+I)/2，D=√(C·T)。
    任一为 0/None → (None,None,None)（零值退化标记不可计算）。"""
    if e is None or i is None or e <= 0 or i <= 0:
        return None, None, None
    C = 2 * math.sqrt(e * i) / (e + i)
    T = (e + i) / 2
    return C, T, math.sqrt(C * T)


def ccd_level(d):
    if d is None:
        return "不可计算"
    for hi, label in CCD_BINS:
        if d < hi:
            return label
    return "优质协调"


def obstacle_degree(unit_links, ideal=1.0):
    """障碍度：因子贡献度(等权)×指标偏离度(1-标准化值)，归一化。
    返回 {环节: 份额}。全环节达理想(无障碍)→全 0（份额无定义，返回0而非1）。"""
    contrib = {k: (1.0 / len(unit_links)) * (ideal - v) for k, v in unit_links.items() if v is not None}
    total = sum(contrib.values())
    if total <= 1e-12:
        return {k: 0.0 for k in contrib}, 0.0
    return {k: c / total for k, c in contrib.items()}, total


def city_type(obstacle, d, e_links, i_links, d_threshold=0.5):
    e_share = sum(obstacle.get(k, 0) for k in e_links)
    i_share = sum(obstacle.get(k, 0) for k in i_links)
    high = d is not None and d >= d_threshold
    if abs(e_share - i_share) < 0.15:
        return "双高协调" if high else "双低失调"
    return "产业领先·教育滞后" if e_share > i_share else "教育领先·产业滞后"


def path_type(d_series):
    """由 D 的多年轨迹（斜率+波动+跳变）分路径。d_series: 按年排序的 D（可含 None）。"""
    ds = [d for d in d_series if d is not None]
    if len(ds) < 3:
        return "数据不足"
    change = ds[-1] - ds[0]
    steps = [ds[i + 1] - ds[i] for i in range(len(ds) - 1)]
    max_jump = max(steps)
    vol = statistics.pstdev(steps) if len(steps) > 1 else 0.0
    mean_d = statistics.fmean(ds)
    if max_jump >= 0.25 and change > 0:
        return "跃迁协调型"
    if change > 0.02 and vol < 0.1:
        return "稳定提升型"
    return "低位波动型"


# ---------------- 自检 ----------------
def self_test(cfg):
    print("== 四环节功能链管道 · 内核自检 ==")
    e_scale = {"A": [10, 12, 14], "B": [5, 6, 7], "C": [2, 2, 3]}
    e_qual = {"A": [8, 8, 9], "B": [4, 4, 4], "C": [1, 1, 1]}
    i_carr = {"A": [3, 5, 9], "B": [6, 7, 8], "C": [1, 1, 2]}
    i_conv = {"A": [2, 4, 7], "B": [5, 6, 7], "C": [0, 1, 1]}
    cities, years = ["A", "B", "C"], [0, 1, 2]
    flat = lambda d: [d[c][t] for c in cities for t in years]
    s_scale, _, _ = minmax(flat(e_scale)); s_qual, _, _ = minmax(flat(e_qual))
    s_carr, _, _ = minmax(flat(i_carr)); s_conv, _, _ = minmax(flat(i_conv))
    E = equal_weight(s_scale, s_qual); I = equal_weight(s_carr, s_conv)
    D = [ccd(e, i)[2] for e, i in zip(E, I)]
    print(f"  E样例 {[round(x,3) if x else None for x in E[:3]]}  "
          f"I样例 {[round(x,3) if x else None for x in I[:3]]}  "
          f"D样例 {[round(x,3) if x else None for x in D[:3]]}")
    # 障碍度①：C市末年（低值=真障碍）→ 份额和应=1
    idxC = cities.index("C") * len(years) + 2
    obC, totC = obstacle_degree({"供给规模": s_scale[idxC], "供给质量": s_qual[idxC],
                                 "产业承接": s_carr[idxC], "产业转化": s_conv[idxC]})
    sum_ok = abs(sum(obC.values()) - 1.0) < 1e-9
    # 障碍度②（边界）：全理想 → 全 0（修复原 bug：不再强求和=1）
    obIdeal, totIdeal = obstacle_degree({"a": 1.0, "b": 1.0, "c": 1.0, "d": 1.0})
    ideal_ok = totIdeal == 0.0 and sum(obIdeal.values()) == 0.0
    # 路径分类
    p_ok = path_type([0.3, 0.32, 0.35]) == "稳定提升型" and path_type([0.2, 0.6, 0.65]) == "跃迁协调型"
    print(f"  C市末年障碍度 { {k: round(v,2) for k,v in obC.items()} } 和={sum(obC.values()):.3f}")
    print(f"  全理想边界: 总偏离={totIdeal} 份额全0={ideal_ok}")
    print(f"  障碍度和=1:{sum_ok}  全理想=0:{ideal_ok}  路径分类:{p_ok}")
    ok = sum_ok and ideal_ok and p_ok and D[idxC] is not None
    print("自检", "通过 ✓" if ok else "失败 ✗")
    return ok


# ---------------- 模板与真实运行 ----------------
def make_templates():
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    files = ["e_supply_scale_panel.csv", "e_supply_quality_panel.csv",
             "i_carrier_panel.csv", "i_conversion_panel.csv"]
    for fn in files:
        path = PANEL_DIR / fn
        if path.exists():
            print(f"已存在，跳过：{path}")
            continue
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["city", "year", "caliber", "value", "population", "data_status"])
            for c in FUJIAN_9:
                for y in YEARS:
                    for cal in CALIBERS:
                        w.writerow([c, y, cal, "", "", ""])
        print(f"已生成模板：{path}")
    print("\n填表说明：value=原始量；population=城市常住人口(供给质量capacity环节可留空)；"
          "data_status 用 calculated/missing/calculated_zero 标注。")


def _read_panel(path):
    """→ {caliber: {(city,year): (value, population)}}"""
    data = {c: {} for c in CALIBERS}
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            cal = (r.get("caliber") or "").strip()
            if cal not in CALIBERS:
                continue
            try:
                v = float(r["value"]) if (r.get("value") or "").strip() != "" else None
            except ValueError:
                v = None
            pop = (r.get("population") or "").strip()
            pop = float(pop) if pop else None
            data[cal][(r["city"].strip(), int(r["year"]))] = (v, pop)
    return data


def run_real(cfg):
    links = []
    for sys_key, side in (("E_system", "E"), ("I_system", "I")):
        for link in cfg[sys_key]["links"]:
            links.append({"id": link["id"], "side": side, "panel": ROOT / link["panel"],
                          "norm": link.get("normalization", "per_capita")})
    missing = [str(l["panel"].relative_to(ROOT)) for l in links if not l["panel"].exists()]
    if missing:
        print("以下环节面板尚未采集，无法运行真实管道（先 --make-templates 生成、采集填入）：")
        for m in missing:
            print("  -", m)
        return

    raw = {l["id"]: _read_panel(l["panel"]) for l in links}
    any_data = any(v is not None for lid in raw for cal in CALIBERS
                   for (v, _) in raw[lid][cal].values())
    if not any_data:
        print("四环节面板已存在但尚未填入数据（value 全空）。请采集填入后再 --run；"
              "现可用 --make-templates 的模板填数。")
        return
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    e_ids = [l["id"] for l in links if l["side"] == "E"]
    i_ids = [l["id"] for l in links if l["side"] == "I"]
    norm = {l["id"]: l["norm"] for l in links}
    rows = []
    for cal in CALIBERS:
        grid = sorted({k for lid in raw for k in raw[lid][cal]})  # (city,year)
        # 各环节：人均化 → 标准化
        std = {}
        for lid in raw:
            vals = []
            for (city, year) in grid:
                v, pop = raw[lid][cal].get((city, year), (None, None))
                if v is not None and norm[lid] == "per_capita":
                    v = v / pop if pop else None
                vals.append(v)
            std[lid], _, _ = minmax(vals)
        # 逐单元 E/I/CCD/障碍度/类型
        E = equal_weight(*[std[x] for x in e_ids])
        I = equal_weight(*[std[x] for x in i_ids])
        d_by_city = {}
        for n, (city, year) in enumerate(grid):
            C, T, D = ccd(E[n], I[n])
            ob, tot = obstacle_degree({lid: std[lid][n] for lid in raw})
            bottleneck = max(ob, key=ob.get) if tot > 0 else "无（均达理想或不可计算）"
            ct = city_type(ob, D, e_ids, i_ids) if D is not None else "不可计算"
            d_by_city.setdefault(city, []).append((year, D))
            rows.append({"caliber": cal, "city": city, "year": year,
                         "E_index": E[n], "I_index": I[n], "C": C, "T": T, "D": D,
                         "CCD_level": ccd_level(D), **{f"障碍_{lid}": ob.get(lid) for lid in raw},
                         "主障碍环节": bottleneck, "城市类型": ct})
        # 路径（按城市，仅本 caliber）
        ptype = {city: path_type([d for _, d in sorted(s)]) for city, s in d_by_city.items()}
        for row in rows:
            if row["caliber"] == cal:
                row["演化路径"] = ptype.get(row["city"], "")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{run_id}"
    out.mkdir(exist_ok=True)
    res = out / f"functional_chain_ccd_results_{run_id}.csv"
    fields = ["caliber", "city", "year", "E_index", "I_index", "C", "T", "D", "CCD_level",
              *[f"障碍_{lid}" for lid in raw], "主障碍环节", "城市类型", "演化路径"]
    with open(res, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()})
    manifest = {"run_id": run_id, "generated_at": datetime.now().isoformat(),
                "task": "论文A四环节功能链 CCD 与障碍度", "n_rows": len(rows),
                "calibers": CALIBERS, "output": str(res.relative_to(ROOT))}
    (out / f"manifest_{run_id}.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "latest_functional_chain_ccd_results.csv").write_text(res.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"完成：{res}\n共 {len(rows)} 行（{len(CALIBERS)}口径 × 城市年）。latest 入口已更新。")


def main():
    ap = argparse.ArgumentParser(description="四环节功能链 CCD 管道")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--make-templates", action="store_true")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(CFG, encoding="utf-8"))
    if args.self_test:
        raise SystemExit(0 if self_test(cfg) else 1)
    if args.make_templates:
        make_templates(); return
    if args.run:
        run_real(cfg); return
    ap.error("需 --self-test / --make-templates / --run")


if __name__ == "__main__":
    main()
