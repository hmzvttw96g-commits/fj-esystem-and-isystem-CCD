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

v3（2026-06）：新增 2020/2021 两栏格式分支（detect_two_col → parse_page_2col）：
  字符映射(渊（冤）袁，窑·尧、)、x305 分栏+右栏-243、剔左侧竖排标签、2020 列带、校名两行结构。
  2020 实测：福建校、量级合理（集美785/福师大297/厦大185）。

⚠ 仍待（输出仍须人工抽查后方可冻结）：
  1. 2020/2021 精度待核：①"独立学院"等类别标题被当校名（下游参照名单过滤会丢，不污染面板）
     ②福州大学等个别校疑似漏抽（农村专项段计划列缺失那个坑）③福建医科大学等 expect_B=no
     校出现命中疑误配。须抽查这些校分专业计划 vs 原 PDF。
  2. 高职分类招考（面向中职生·本科批，职业本科渠道）、2019 老版式（RAR）未适配。
  3. 华侨大学跨校区：下游标 needs_campus，待校区核验归市。
  4. 最终须抽查 3—5 校分专业计划合计 vs 原 PDF，再进面板。

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


# ---- 2020/2021 两栏格式 ----
TR = str.maketrans({"渊": "（", "冤": "）", "袁": "，", "窑": "·", "尧": "、"})
SPLIT_X = 305          # 左右栏分界
RIGHT_OFFSET = 243     # 右栏减此偏移后与左栏共用列带
C2_CODE = (74, 93)     # 专业代号（数据行）
C2_MAJOR = (92, 238)   # 专业名称（名称行）/ 校名
C2_PLAN = (236, 252)   # 计划人数（数据行）
C2_XUEZHI = (250, 264) # 学制（名称行）


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


def detect_two_col(pdf):
    """采样前若干页：乱码字（渊/冤）多 → 2020/2021 两栏格式。"""
    g = 0
    for p in pdf.pages[:8]:
        t = p.extract_text() or ""
        g += t.count("渊") + t.count("冤")
    return g > 40


def parse_half(half_words, year, page_no, school_ctx, batch):
    """解析单栏（左栏原坐标 / 右栏已减偏移）。school_ctx 跨调用保留校名。"""
    rows = group_rows(half_words)
    out = []
    pending_name = None
    for t in sorted(rows):
        line = rows[t]
        txt = "".join(w["text"] for w in line)
        # 含中文且在校名/专业带 → 记为候选校名（校名行常在公办行上一行）
        chinese_major = "".join(w["text"] for w in line if in_col(w["x0"], C2_MAJOR) and re.search(r"[一-鿿]", w["text"]))
        if any(o in txt for o in OWNER):
            nm = pending_name or chinese_major
            nm = re.split(r"[（(]", nm)[0].strip()
            if nm and re.search(r"(大学|学院|学校)", nm):
                school_ctx["school"] = nm
                mcity = re.search(r"([一-鿿]{2,4}市)", txt)
                school_ctx["city"] = mcity.group(1) if mcity else school_ctx.get("city")
                school_ctx["owner"] = "公办" if "公办" in txt else "民办"
            pending_name = None
            continue
        # 记候选校名（带4位院校代号+中文名的行）
        if re.search(r"(大学|学院|学校)", chinese_major) and "专业组" not in chinese_major:
            pending_name = re.split(r"[（(]", chinese_major)[0].strip()
        # 专业名称行：境外剔除
        if "马来西亚" in txt or "林吉特" in txt:
            continue
        major = re.split(r"(大学|学院|分校)", chinese_major)[0].strip()
        if major and major not in OWNER and "专业组" not in major and len(major) >= 2 \
                and not re.search(r"(大学|学院|学校|招生|网址|学费|收费|学年|说明)", major):
            # 找下方数据行的计划数（C2_PLAN 带）
            plan = code = None
            for tt in sorted(rows):
                if t < tt <= t + PAIR_TOL:
                    pl = "".join(w["text"] for w in rows[tt] if in_col(w["x0"], C2_PLAN))
                    if re.fullmatch(r"\d{1,4}", pl):
                        plan = pl
                        code = "".join(w["text"] for w in rows[tt] if in_col(w["x0"], C2_CODE))
                        break
            if plan and school_ctx.get("school"):
                out.append({"year": year, "school": school_ctx["school"], "city": school_ctx.get("city", ""),
                            "owner": school_ctx.get("owner", ""), "major": major, "major_code": code or "",
                            "plan": plan, "batch": batch, "page": page_no})
    return out


def parse_page_2col(page, year, page_no, state):
    clean = page.filter(lambda o: o.get("size", 0) < WM_SIZE if o["object_type"] == "char" else True)
    words = []
    for w in clean.extract_words():
        w["text"] = w["text"].translate(TR)
        if w["x0"] < 50 and len(w["text"]) <= 1:   # 剔左侧竖排批次标签单字
            continue
        words.append(w)
    # 批次：竖排标签（x<50 单字按 y 拼）或页文本
    vlabel = "".join(c["text"].translate(TR) for c in sorted(
        [c for c in clean.chars if c["x0"] < 50], key=lambda c: c["top"]))
    ptxt = vlabel + (clean.extract_text() or "").translate(TR)
    for b in BATCHES:
        if b in ptxt:
            state["batch"] = b
    batch = state.get("batch", "")
    left = [w for w in words if w["x0"] < SPLIT_X]
    right = [dict(w, x0=w["x0"] - RIGHT_OFFSET, x1=w.get("x1", w["x0"]) - RIGHT_OFFSET)
             for w in words if w["x0"] >= SPLIT_X]
    out = []
    for half in (left, right):
        out += parse_half(half, year, page_no, state.setdefault("ctx", {}), batch)
    return out


def run(pdf_path, year, out_path):
    rows = []
    state = {}
    with pdfplumber.open(pdf_path) as pdf:
        two_col = detect_two_col(pdf)
        print(f"  版式：{'两栏(2020/2021)' if two_col else '单栏(2022-2025)'}")
        parser = parse_page_2col if two_col else parse_page
        n = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            rows.extend(parser(page, year, i + 1, state))
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
