#!/usr/bin/env python3
"""福建省普通高校招生计划 PDF → 候选行 CSV（普通类物理/理工科目组格式）。

破两大障碍：
  ①水印"福建省教育考试院"是超大字号(>30)，过滤字号即除；正文 ~8pt。
  ②列按 x 坐标排（院校代号<100｜专业代号100-130｜专业名称130-280｜学制280-300｜
    计划人数300-330｜收费330-360｜备注>360）；一个专业=名称行+紧邻下方"代号 计划 收费"行配对。

跟踪：校名/城市/办学性质（"公办/民办"行）、批次（页头"本科提前批/本科批/…"）。
输出候选行 CSV（year,school,major,plan,batch,page），喂 e_supply_scale_pipeline.py。
本脚本只抽"候选行"（全专业），AI 口径筛选与归一交给后者。

⚠ 适配"普通类物理科目组"版式（2020/2022/2023 等）。其它版式（高职分类、文史、2019 doc）
  列边界可能不同，需另调 COLS 或单独适配。

已修（v2，2026-06）：
  ✓ 境外校区剔除：窗口扫描"林吉特/马来西亚/办学地点在马来西亚"整段剔除（厦大马来西亚分校已干净）；
    中外合作在闽办学保留。专业名校名污染截断（残留 0）。真重复去重。
  ✓ 莆田软件306 等大值经原 PDF 核验为真实计划（配对正确），非误配总计。
  ✓ 下游 e_supply_scale_pipeline 去重键含专业代号+计划+页 → 多专业组同专业**求和**。

⚠ 仍待（输出仍须人工抽查后方可冻结）：
  1. 仅适配"普通类物理科目组"版式（2020/2022/2023）。**高职分类招考（面向中职生·本科批）、
     文史/历史科目组、2019 doc** 版式未适配——职业本科招生走高职分类渠道，须单独解析后合并。
  2. 华侨大学等跨校区：下游标 needs_campus，待按校区核验协议归市。
  3. 最终须抽查 3—5 校分专业计划合计 vs 原 PDF 人工读数，再进面板。

用法：
  python3 scripts/parse_enrollment_pdf.py --pdf <计划册.pdf> --year 2022 [--out cand.csv]
"""
from __future__ import annotations
import argparse, csv, re
from collections import defaultdict
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    raise SystemExit("需要 pdfplumber：pip3 install --user pdfplumber")

# 列 x 边界（普通类物理科目组实测）
COL_SCHOOL = (0, 100)      # 院校代号/校名
COL_MAJORCODE = (100, 130) # 专业代号
COL_MAJOR = (130, 280)     # 专业名称
COL_XUEZHI = (280, 300)    # 学制
COL_PLAN = (300, 330)      # 计划人数
COL_FEE = (330, 362)       # 收费
WM_SIZE = 30               # 字号≥此为水印
BATCHES = ["本科提前批", "本科批", "本科一批", "本科二批", "高校农村专项",
           "地方农村专项", "高职专科批", "高职(专科)批", "高职（专科）批"]
OWNER = ["公办", "民办"]
ROW_TOL = 3.0              # 行聚类容差
PAIR_TOL = 14.0           # 名称行→数据行配对的最大向下距离


def in_col(x, col):
    return col[0] <= x < col[1]


def group_rows(words):
    rows = defaultdict(list)
    for w in words:
        rows[round(w["top"] / ROW_TOL) * ROW_TOL].append(w)
    return {t: sorted(ws, key=lambda w: w["x0"]) for t, ws in sorted(rows.items())}


def col_text(line, col):
    return "".join(w["text"] for w in line if in_col(w["x0"], col)).strip()


def find_plan_row(rows, name_top):
    """名称行下方 PAIR_TOL 内、含计划人数列数字的最近行。"""
    best = None
    for t, line in rows.items():
        if name_top < t <= name_top + PAIR_TOL:
            plan = col_text(line, COL_PLAN)
            if re.fullmatch(r"\d{1,4}", plan):
                code = col_text(line, COL_MAJORCODE)
                if best is None or t < best[0]:
                    best = (t, plan, code)
    return best


def parse_page(page, year, page_no, batch_state):
    clean = page.filter(lambda o: o.get("size", 0) < WM_SIZE if o["object_type"] == "char" else True)
    txt = clean.extract_text() or ""
    for b in BATCHES:
        if b in txt:
            batch_state["batch"] = b   # 页头批次，沿用到下页直到变化
    words = clean.extract_words()
    rows = group_rows(words)
    row_txt = {t: "".join(w["text"] for w in ln) for t, ln in rows.items()}
    sorted_tops = sorted(rows)

    def window_text(t0):
        # 该专业行附近窗口（含数据行/续行）的全文，用于识别境外校区
        return "".join(row_txt[t] for t in sorted_tops if t0 - 4 <= t <= t0 + PAIR_TOL + 4)

    out = []
    school = batch_state.get("school"); city = batch_state.get("city"); owner = batch_state.get("owner")
    for t, line in rows.items():
        # 校名行：含 公办/民办，且左列有中文校名
        line_txt = "".join(w["text"] for w in line)
        if any(o in line_txt for o in OWNER):
            left = [w["text"] for w in line if in_col(w["x0"], (0, 140)) and re.search(r"[一-鿿]", w["text"])]
            nm = "".join(left)
            nm = re.split(r"[（(]", nm)[0].strip()   # 去掉(校区,性别)
            if nm and re.search(r"(大学|学院|学校|大学城)", nm):
                school = nm
                mcity = re.search(r"([一-鿿]{2,4}市)", line_txt)
                city = mcity.group(1) if mcity else city
                owner = "公办" if "公办" in row_txt else "民办"
                batch_state.update(school=school, city=city, owner=owner)
            continue
        # 专业名称行：专业名称列有中文 且 学制列是 三/四/五 或 学制行
        raw_major = col_text(line, COL_MAJOR)
        # 境外校区剔除（窗口含"林吉特/马来西亚/境外"等）；中外合作在闽办学，保留
        if any(k in window_text(t) for k in ("林吉特", "马来西亚", "境外办学", "办学地点在马来西亚")):
            continue
        # 截断混入的校名污染（专业名不含"大学/学院"，故安全）
        major = raw_major.split(school)[0].strip() if (school and school in raw_major) else raw_major
        major = re.split(r"(大学|学院|分校)", major)[0].strip()
        xz = col_text(line, COL_XUEZHI)
        if major and re.search(r"[一-鿿]", major) and ("专业组" not in major) and (xz in ("三", "四", "五", "二") or major):
            pr = find_plan_row(rows, t)
            if pr and school:
                _, plan, code = pr
                out.append({"year": year, "school": school, "city": city or "",
                            "owner": owner or "", "major": major, "major_code": code,
                            "plan": plan, "batch": batch_state.get("batch", ""), "page": page_no})
    return out


def run(pdf_path, year, out_path):
    rows = []
    state = {}
    with pdfplumber.open(pdf_path) as pdf:
        n = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            rows.extend(parse_page(page, year, i + 1, state))
            if (i + 1) % 100 == 0:
                print(f"  …已处理 {i+1}/{n} 页，累计候选行 {len(rows)}")
    # 去重：同页同校同专业同代号同计划=真重复（抽取重影）
    seen, uniq = set(), []
    for r in rows:
        k = (r["page"], r["school"], r["major"], r["major_code"], r["plan"])
        if k in seen:
            continue
        seen.add(k); uniq.append(r)
    print(f"  去重：{len(rows)} → {len(uniq)}")
    rows = uniq
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["year", "school", "city", "owner", "major",
                                          "major_code", "plan", "batch", "page"])
        w.writeheader(); w.writerows(rows)
    print(f"\n完成：{out_path}（候选行 {len(rows)}）。")
    # AI 口径粗筛预览（仅供 sanity check，正式筛选在 e_supply_scale_pipeline）
    AI = ["人工智能", "智能科学与技术", "数据科学与大数据技术", "计算机科学与技术", "软件工程",
          "网络工程", "信息安全", "物联网工程", "网络空间安全", "计算机类"]
    hits = [r for r in rows if any(a in r["major"] for a in AI)]
    bysch = defaultdict(int)
    for r in hits:
        bysch[r["school"]] += int(r["plan"]) if r["plan"].isdigit() else 0
    print(f"AI口径粗命中 {len(hits)} 条；分校计划合计(预览):")
    for s, p in sorted(bysch.items(), key=lambda x: -x[1])[:15]:
        print(f"  {s}: {p}")


def main():
    ap = argparse.ArgumentParser(description="招生计划 PDF → 候选行")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--year", required=True, type=int)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = args.out or f"/tmp/enrollment_candidates_{args.year}.csv"
    run(args.pdf, args.year, out)


if __name__ == "__main__":
    main()
