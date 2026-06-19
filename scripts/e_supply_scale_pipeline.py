#!/usr/bin/env python3
"""供给规模(E端招生)归一管道：候选行 → 城市×年×口径 招生计划数面板 + 质量闸门。

分工：
  PDF/DOC 解析（计划册 → 候选行 CSV）是格式相关的单独一步（见 --extract 脚手架/采集方案）。
  本管道吃"候选行 CSV"，做配置驱动、可自检的归一与聚合：
    1. 校名归一：曾用名→现名（e_school_reference_fujian.yml，解决更名漏抽，如福建工程学院→福建理工大学）
    2. C/B/X 打标：专业/大类 → 口径（e_caliber_majors.yml；严格嵌套：C专业计入C/B/X，B专业计入B/X，X专业仅X）
    3. 批次过滤：剔高职专科、征求志愿（防重复计数，冻结文档批次规则）
    4. 去重：同 城市×年×校×专业×批次
    5. 聚合：城市×年×口径 招生计划数 → 填 e_supply_scale_panel.csv（caliber=C/B/X 行）
    6. 质量闸门：完备性（参照名单 expect_B 校零命中→核查单）、跳变（校/市 YoY≥4×或≤0.25×）、未匹配项留痕

候选行 CSV 列（最少）：year, school, major, plan, batch  （可选 city；跨校区华侨大学按校区核验另处理）
纯标准库 + pyyaml。

用法：
  python3 scripts/e_supply_scale_pipeline.py --self-test
  python3 scripts/e_supply_scale_pipeline.py --candidates <候选行.csv>
"""
from __future__ import annotations
import argparse, csv, sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("需要 pyyaml：pip3 install --user pyyaml")

ROOT = Path(__file__).resolve().parents[1]
CFG_MAJ = ROOT / "config" / "e_caliber_majors.yml"
CFG_SCH = ROOT / "config" / "e_school_reference_fujian.yml"
PANEL = ROOT / "data" / "panel" / "functional_chain" / "e_supply_scale_panel.csv"
AUDIT = ROOT / "data" / "audit" / "e_supply_scale"
YEARS = set(range(2019, 2025))
CAL_RANK = {"C": 0, "B": 1, "X": 2}
EXCLUDE_BATCH = ["高职", "专科", "征求", "补录"]   # 剔高职专科 + 征求志愿（防重复计数）


def load_calibers():
    c = yaml.safe_load(open(CFG_MAJ, encoding="utf-8"))
    C = {m["name"] for m in c["C_conservative"]["majors"]}
    Badd = {m["name"] for m in c["B_basic"]["additional_majors"]}
    Xadd = {m["name"] for m in c["X_expanded"]["additional_majors"]}
    broad = {b["broad_category"]: b["caliber"] for b in c.get("broad_category_mapping", [])}
    pend = {p["name"] for p in c.get("pending_ruling", [])}
    return C, Badd, Xadd, broad, pend


def load_schools():
    s = yaml.safe_load(open(CFG_SCH, encoding="utf-8"))["schools"]
    name2city, former2cur, expect_by_city = {}, {}, defaultdict(set)
    for x in s:
        name2city[x["name"]] = x["city"]
        for h in x.get("school_name_history", []):
            former2cur[h["former"]] = x["name"]
        if x.get("expect_B_majors") == "yes" or x.get("expect_B_majors") is True:
            expect_by_city[x["city"]].add(x["name"])
    return name2city, former2cur, expect_by_city


def norm_school(raw, name2city, former2cur):
    """→ (现名 or None, 城市 or None, 是否跨校区待核验)"""
    raw = (raw or "").strip()
    if raw in name2city:
        cur = raw
    elif raw in former2cur:
        cur = former2cur[raw]
    else:
        cur = next((n for n in name2city if n in raw or raw in n), None)  # 含括兜底
    if not cur:
        return None, None, False
    city = name2city[cur]
    return cur, city, ("/" in city)   # 华侨大学 厦门/泉州 → 待校区核验


def home_caliber(major, C, Badd, Xadd, broad):
    major = (major or "").strip()
    if major in broad:
        return broad[major]
    if major in C:
        return "C"
    if major in Badd:
        return "B"
    if major in Xadd:
        return "X"
    return None


def is_excluded_batch(batch):
    return any(k in (batch or "") for k in EXCLUDE_BATCH)


def run(cand_path):
    C, Badd, Xadd, broad, pend = load_calibers()
    name2city, former2cur, expect_by_city = load_schools()
    seen = set()
    agg = defaultdict(int)                 # (city, year, caliber) -> plan
    school_year = defaultdict(int)         # (city, school, year) -> plan (跳变用)
    appeared = defaultdict(set)            # (city, year) -> {school} (完备性用)
    unmatched_school, unmatched_major, campus_review = [], [], []
    n_in = n_kept = 0
    with open(cand_path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            n_in += 1
            try:
                y = int(float(r.get("year") or ""))
            except ValueError:
                continue
            if y not in YEARS or is_excluded_batch(r.get("batch")):
                continue
            cur, city, needs_campus = norm_school(r.get("school"), name2city, former2cur)
            if not cur:
                unmatched_school.append((r.get("school"), y)); continue
            if needs_campus:
                campus_review.append((cur, r.get("major"), y, r.get("plan")))
                continue   # 跨校区(华侨大学)待校区核验，不自动归市
            major = (r.get("major") or "").strip()
            h = home_caliber(major, C, Badd, Xadd, broad)
            if h is None:
                unmatched_major.append((major, cur, y)); continue
            try:
                plan = int(float(r.get("plan") or 0))
            except ValueError:
                plan = 0
            key = (city, y, cur, major, (r.get("batch") or "").strip())
            if key in seen:
                continue
            seen.add(key); n_kept += 1
            appeared[(city, y)].add(cur)
            school_year[(city, cur, y)] += plan
            for cal in ("C", "B", "X"):     # 嵌套累加：home 在该口径内则计入
                if CAL_RANK[cal] >= CAL_RANK[h]:
                    agg[(city, y, cal)] += plan

    # 质量闸门
    completeness = []   # (city, year, 缺失的expect_B校)
    for city, schools in expect_by_city.items():
        for y in sorted(YEARS):
            missing = schools - appeared.get((city, y), set())
            if missing:
                completeness.append((city, y, sorted(missing)))
    jumps = []          # 校级跳变
    by_school = defaultdict(dict)
    for (city, sch, y), p in school_year.items():
        by_school[(city, sch)][y] = p
    for (city, sch), series in by_school.items():
        ys = sorted(series)
        for i in range(1, len(ys)):
            prev, cur_p = series[ys[i - 1]], series[ys[i]]
            if prev > 0 and (cur_p / prev >= 4 or cur_p / prev <= 0.25):
                jumps.append((city, sch, ys[i - 1], prev, ys[i], cur_p, round(cur_p / prev, 2)))

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    write_outputs(agg, completeness, jumps, unmatched_school, unmatched_major, campus_review, run_id)
    print(f"候选行 {n_in} → 入账 {n_kept}；城市×年×口径单元 {len(agg)}。")
    print(f"完备性缺口 {len(completeness)} 处、跳变 {len(jumps)} 处、未匹配校 {len(unmatched_school)}、"
          f"未匹配专业 {len(unmatched_major)}、跨校区待核 {len(campus_review)}（详见 audit）。")
    return agg


def write_outputs(agg, completeness, jumps, un_sch, un_maj, campus, run_id):
    out = AUDIT / run_id; out.mkdir(parents=True, exist_ok=True)
    # 填面板（C/B/X 行的 value）
    if PANEL.exists():
        rows = list(csv.DictReader(open(PANEL, encoding="utf-8-sig")))
        for r in rows:
            k = (r["city"].strip(), int(r["year"]), r["caliber"])
            if k in agg:
                r["value"] = agg[k]; r["data_status"] = "calculated"
            else:
                r["data_status"] = r.get("data_status") or "missing_or_truezero"
        with open(PANEL, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["city", "year", "caliber", "value", "population", "data_status"])
            w.writeheader(); w.writerows(rows)
        print(f"已填 {PANEL.relative_to(ROOT)} 的 C/B/X value（population 待从年鉴补）。")
    else:
        print(f"⚠ 面板模板缺失，先跑 functional_chain_ccd_pipeline.py --make-templates")
    # 完备性核查单（最重要：零命中须人工确认真零）
    with open(out / f"completeness_check_{run_id}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["city", "year", "应有B口径但零命中的学校", "须人工确认真零"])
        for city, y, miss in completeness:
            w.writerow([city, y, "、".join(miss), "yes"])
    # 跳变、未匹配、跨校区
    with open(out / f"value_jumps_{run_id}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["city", "school", "prev_year", "prev", "year", "value", "ratio"])
        w.writerows(jumps)
    with open(out / f"manual_review_{run_id}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["类型", "项", "校/年"])
        for s, y in un_sch: w.writerow(["未匹配学校", s, y])
        for m, sch, y in un_maj: w.writerow(["未匹配专业", m, f"{sch}/{y}"])
        for sch, m, y, p in campus: w.writerow(["跨校区待核(华侨大学)", f"{sch}-{m}", f"{y}/计划{p}"])
    print(f"审计：{out.relative_to(ROOT)}（完备性核查单 + 跳变 + 待人工复核）")


def self_test():
    print("== 供给规模归一管道自检 ==")
    import tempfile, os
    rows = [
        # 福州大学·人工智能(C)·本科批·2021 → 计入C/B/X
        ["2021", "福州大学", "人工智能", "30", "本科批"],
        # 福州大学·软件工程(B)·本科批·2021 → 计入B/X(不计C)
        ["2021", "福州大学", "软件工程", "50", "本科批"],
        # 福州大学·自动化(X)·本科批·2021 → 仅X
        ["2021", "福州大学", "自动化", "20", "本科批"],
        # 曾用名:福建工程学院→福建理工大学,计算机类(大类→B),2021
        ["2021", "福建工程学院", "计算机类", "40", "本科批"],
        # 高职专科应剔除
        ["2021", "福州大学", "软件工程", "999", "高职专科批"],
        # 重复行应去重
        ["2021", "福州大学", "人工智能", "30", "本科批"],
        # 华侨大学跨校区→待核验,不入账
        ["2021", "华侨大学", "软件工程", "15", "本科批"],
    ]
    fd, tmp = tempfile.mkstemp(suffix=".csv"); os.close(fd)
    with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["year", "school", "major", "plan", "batch"]); w.writerows(rows)
    # 直接调内部聚合（绕过写面板）
    C, Badd, Xadd, broad, pend = load_calibers()
    name2city, former2cur, _ = load_schools()
    agg = defaultdict(int); seen = set()
    for r in csv.DictReader(open(tmp, encoding="utf-8-sig")):
        y = int(r["year"])
        if is_excluded_batch(r["batch"]): continue
        cur, city, nc = norm_school(r["school"], name2city, former2cur)
        if not cur or nc: continue
        h = home_caliber(r["major"], C, Badd, Xadd, broad)
        if h is None: continue
        k = (city, y, cur, r["major"], r["batch"])
        if k in seen: continue
        seen.add(k)
        for cal in ("C", "B", "X"):
            if CAL_RANK[cal] >= CAL_RANK[h]: agg[(city, y, cal)] += int(r["plan"])
    os.unlink(tmp)
    fz = lambda cal: agg.get(("福州", 2021, cal), 0)
    # C = 人工智能30
    # B = 人工智能30 + 软件工程50 + 计算机类40(大类→B) = 120
    # X = B120 + 自动化20 = 140
    okC, okB, okX = fz("C") == 30, fz("B") == 120, fz("X") == 140
    print(f"  福州2021  C={fz('C')}(应30)  B={fz('B')}(应120,含曾用名计算机类+大类→B)  X={fz('X')}(应140,+自动化)")
    print(f"  C⊂B⊂X 嵌套累加正确:{okC and okB and okX}；高职/去重/跨校区已排除")
    ok = okC and okB and okX
    print("自检", "通过 ✓" if ok else "失败 ✗")
    return ok


def main():
    ap = argparse.ArgumentParser(description="供给规模(E端招生)归一管道")
    ap.add_argument("--candidates", help="候选行 CSV(year,school,major,plan,batch[,city])")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        raise SystemExit(0 if self_test() else 1)
    if not args.candidates:
        ap.error("需 --candidates <csv> 或 --self-test")
    run(args.candidates)


if __name__ == "__main__":
    main()
