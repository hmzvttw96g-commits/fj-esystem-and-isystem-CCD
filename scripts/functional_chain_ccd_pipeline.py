#!/usr/bin/env python3
"""四环节功能链 CCD 与障碍度管道（骨架）。

读取 config/functional_chain.yml，从四个环节面板构造 E_index / I_index，
计算 CCD(E,I) 与障碍度四环节分解，导出城市类型/路径/瓶颈迁移读数。
参数全读 config，禁止硬编码城市/年份；沿用 run_id/manifest/latest_ 纪律。

状态：骨架 v0.1。统计内核（标准化、CCD、障碍度）已实现并可单元自检；
四环节真实面板（data/panel/functional_chain/*.csv）尚待采集填入——
未填时以 --self-test 用合成面板验证内核。纯标准库，不依赖 pandas。

用法：
  python3 scripts/functional_chain_ccd_pipeline.py --self-test     # 合成面板验证内核
  python3 scripts/functional_chain_ccd_pipeline.py --run           # 读真实面板（待数据齐）
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


# ---------------- 统计内核（纯标准库，可自检） ----------------
def minmax(values, lo=None, hi=None):
    """全样本固定基准 min-max；锚点可外部传入（经审计签字）。"""
    xs = [v for v in values if v is not None]
    lo = min(xs) if lo is None else lo
    hi = max(xs) if hi is None else hi
    rng = (hi - lo) or 1.0
    return [None if v is None else max(0.0, min(1.0, (v - lo) / rng)) for v in values], lo, hi


def equal_weight(*cols):
    """等权合成多个已标准化的环节列（任一为 None 则该单元为 None=不可计算）。"""
    out = []
    for row in zip(*cols):
        out.append(None if any(v is None for v in row) else sum(row) / len(row))
    return out


def ccd(e, i):
    """标准耦合协调度：C=2√(EI)/(E+I)，T=(E+I)/2，D=√(C·T)。零值→不可计算。"""
    if e is None or i is None or e <= 0 or i <= 0:
        return None
    C = 2 * math.sqrt(e * i) / (e + i)
    T = (e + i) / 2
    return math.sqrt(C * T)


def obstacle_degree(unit_links, ideal=1.0):
    """障碍度：因子贡献度(等权) × 指标偏离度(1-标准化值)，归一化。
    unit_links: {环节名: 标准化值}。返回 {环节名: 障碍度份额}。"""
    contrib = {k: (1.0 / len(unit_links)) * (ideal - v) for k, v in unit_links.items() if v is not None}
    total = sum(contrib.values())
    if total <= 0:
        return {k: 0.0 for k in contrib}
    return {k: c / total for k, c in contrib.items()}


def city_type(obstacle, d, e_links, i_links, d_threshold=0.5):
    """由障碍度两侧份额 × D 水平导出四类城市。"""
    e_share = sum(obstacle.get(k, 0) for k in e_links)
    i_share = sum(obstacle.get(k, 0) for k in i_links)
    high = d is not None and d >= d_threshold
    if abs(e_share - i_share) < 0.15:
        return "双高协调" if high else "双低失调"
    return "产业领先·教育滞后" if e_share > i_share else "教育领先·产业滞后"


# ---------------- 自检 ----------------
def self_test(cfg):
    print("== 四环节功能链管道 · 内核自检（合成面板） ==")
    # 合成 3 市 × 2 环节，城市间有差异
    e_scale = {"A": [10, 12, 14], "B": [5, 6, 7], "C": [2, 2, 3]}
    e_qual = {"A": [8, 8, 9], "B": [4, 4, 4], "C": [1, 1, 1]}
    i_carr = {"A": [3, 5, 9], "B": [6, 7, 8], "C": [1, 1, 2]}
    i_conv = {"A": [2, 4, 7], "B": [5, 6, 7], "C": [0, 1, 1]}
    cities, years = ["A", "B", "C"], [0, 1, 2]
    flat = lambda d: [d[c][t] for c in cities for t in years]
    s_scale, _, _ = minmax(flat(e_scale))
    s_qual, _, _ = minmax(flat(e_qual))
    s_carr, _, _ = minmax(flat(i_carr))
    s_conv, _, _ = minmax(flat(i_conv))
    E = equal_weight(s_scale, s_qual)
    I = equal_weight(s_carr, s_conv)
    D = [ccd(e, i) for e, i in zip(E, I)]
    print(f"  E_index 样例: {[round(x,3) if x else None for x in E[:3]]}")
    print(f"  I_index 样例: {[round(x,3) if x else None for x in I[:3]]}")
    print(f"  CCD 样例:     {[round(x,3) if x else None for x in D[:3]]}")
    # 障碍度 + 类型（取A市末年）
    idx = cities.index("A") * len(years) + 2
    links = {"供给规模": s_scale[idx], "供给质量": s_qual[idx],
             "产业承接": s_carr[idx], "产业转化": s_conv[idx]}
    ob = obstacle_degree(links)
    ct = city_type(ob, D[idx], ["供给规模", "供给质量"], ["产业承接", "产业转化"])
    print(f"  A市末年障碍度: { {k: round(v,2) for k,v in ob.items()} }")
    print(f"  A市末年类型:   {ct}")
    ok = D[idx] is not None and abs(sum(ob.values()) - 1.0) < 1e-9
    print("自检", "通过 ✓" if ok else "失败 ✗")
    return ok


def run_real(cfg):
    """读真实四环节面板并出全样本结果。待四环节面板采集填入后启用。"""
    missing = []
    for sys_key in ("E_system", "I_system"):
        for link in cfg[sys_key]["links"]:
            p = ROOT / link["panel"]
            if not p.exists():
                missing.append(str(link["panel"]))
    if missing:
        print("以下环节面板尚未采集，无法运行真实管道（先完成 WP2/WP3 采集）：")
        for m in missing:
            print("  -", m)
        print("\n可先用 --self-test 验证内核。")
        return
    # TODO: 面板齐后实现——读四面板→人均化→标准化(审计锚点)→等权E/I→CCD→障碍度→读数→run_id落盘
    print("四环节面板齐备，真实管道实现待补（标 TODO）。")


def main():
    ap = argparse.ArgumentParser(description="四环节功能链 CCD 管道（骨架）")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(CFG, encoding="utf-8"))
    if args.self_test:
        raise SystemExit(0 if self_test(cfg) else 1)
    if args.run:
        run_real(cfg)
        return
    ap.error("需 --self-test 或 --run")


if __name__ == "__main__":
    main()
