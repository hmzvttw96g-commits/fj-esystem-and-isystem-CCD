#!/usr/bin/env python3
"""2019 福建省理工类招生计划（Word .doc/.docx）→ 候选行 CSV。

2019 是独立版式族：非 PDF、非表格，而是 **Word 段落文本**（靠制表位排版）。
三类行（状态机逐段扫）：
  ① 校名行   ：`1054 福州大学             2351`  → 4 位院校代号 + 校名(+变体) + 总计划
  ② 城市/办学：`（福州市）（公办）`                → 设当前 city / owner
  ③ 专业行   ：`   21 软件工程        82 四  5460` → 2–3 位专业代号 + 专业名 + 计划 + 学制 + 收费
续行（`（含:计算机科学与技术…）` 等大类说明）忽略。校名带 4 位代号、专业带 2–3 位代号且有学制
（三/四/五），据此区分。校名去 （变体） 取基名 → 下游多专业组同校求和。

输出 schema 与 parse_enrollment_pdf 一致（year,school,city,owner,major,major_code,plan,batch,page），
喂 e_supply_scale_pipeline。批次由文件名定（高职专科批不纳入，本脚本只跑本科各批）。

目标文件（理工类，本科）：1提前批 / 4本科一批 / 5本科二批 / 2高校农村专项 / 3地方农村专项。
6高职专科批是老 OLE 二进制（且本就不纳入），跳过。

用法：python3 scripts/parse_enrollment_2019_docx.py --dir "<2019年福建省理工类招生计划目录>" [--out cand.csv]
"""
from __future__ import annotations
import argparse, csv, re, zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# 文件名 → 批次（仅本科各批；高职专科批不纳入）
BATCH_BY_FILE = {
    "1提前批": "本科提前批", "4本科一批": "本科一批", "5本科二批": "本科二批",
    "2高校农村专项": "高校农村专项", "3地方农村专项": "地方农村专项",
}
FJ_CITIES = {"福州市", "厦门市", "泉州市", "漳州市", "莆田市", "三明市", "南平市", "龙岩市", "宁德市"}


def docx_paragraphs(path):
    """读 .docx/.doc(2007+) 的段落文本（含制表符）。OLE 老二进制不支持，返回 None。"""
    try:
        z = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        return None
    if "word/document.xml" not in z.namelist():
        return None
    root = ET.fromstring(z.read("word/document.xml").decode("utf-8", "ignore"))
    paras = []
    for p in root.iter(W + "p"):
        parts = []
        for node in p.iter():
            if node.tag == W + "t":
                parts.append(node.text or "")
            elif node.tag == W + "tab":
                parts.append("\t")
        paras.append("".join(parts))
    return paras


def base_school(name):
    """去 （变体） 取基名（如 福州大学（闽台合作）→ 福州大学），便于同校多专业组求和。"""
    return re.split(r"[（(]", name)[0].strip()


# 校名行：行首 4 位院校代号 + 校名（含 大学/学院/学校）+ 余下（变体/总计划）
RE_SCHOOL = re.compile(r"^\s*(\d{4})\s+([一-鿿]{2,15}(?:大学|学院|学校)[^\d]*)")
# 城市/办学行：（××市）（公办/民办/…）
RE_CITY = re.compile(r"[（(]([一-鿿]{2,4}市)[）)]")
RE_OWNER = re.compile(r"[（(](公办|民办|独立学院|中外合作)[）)]")
# 专业行：2–3 位专业代号 + 专业名 + 计划数 + 学制(三/四/五/六) + 收费(数字/待定)
RE_MAJOR = re.compile(r"^\s*(\d{1,3})\s+(.+?)\s+(\d{1,4})\s+([二三四五六])\s+(\S+)")


def parse_file(path, batch, out):
    paras = docx_paragraphs(path)
    if paras is None:
        print(f"  ⚠ 非 docx（老 OLE 或损坏），跳过：{Path(path).name}")
        return 0
    school = city = owner = None
    n = 0
    for raw in paras:
        txt = raw.replace("\t", " ").rstrip()
        if not txt.strip():
            continue
        ms = RE_SCHOOL.match(txt)
        if ms:
            school = base_school(ms.group(2))
            # 校名行可能同段带 （市）（公办）
            mc = RE_CITY.search(txt); mo = RE_OWNER.search(txt)
            if mc:
                city = mc.group(1)
            if mo:
                owner = mo.group(1)
            continue
        # 城市/办学行（独立段）
        if RE_CITY.search(txt) or RE_OWNER.search(txt):
            mc = RE_CITY.search(txt); mo = RE_OWNER.search(txt)
            if mc:
                city = mc.group(1)
            if mo:
                owner = mo.group(1)
            # 该行不再当专业（避免把说明行误解析）
            if not RE_MAJOR.match(txt):
                continue
        mm = RE_MAJOR.match(txt)
        if mm and school:
            code, major, plan, xz, fee = mm.groups()
            major = major.strip()
            # 排除明显非专业（含 大学/学院 校名污染、说明字样）
            if re.search(r"(大学|学院|学校|网址|说明|章程)", major) or len(major) < 2:
                continue
            out.append({"year": 2019, "school": school, "city": city or "", "owner": owner or "",
                        "major": major, "major_code": code, "plan": plan, "batch": batch,
                        "page": ""})
            n += 1
    return n


def run(src_dir, out_path):
    src = Path(src_dir)
    rows = []
    files = sorted(src.glob("*.doc*"))
    for f in files:
        stem = f.stem
        key = next((k for k in BATCH_BY_FILE if stem.startswith(k)), None)
        if key is None:
            print(f"  – 跳过（非本科批/不在清单）：{f.name}")
            continue
        batch = BATCH_BY_FILE[key]
        cnt = parse_file(str(f), batch, rows)
        print(f"  解析 {f.name} → 批次「{batch}」候选行 {cnt}")
    # 去重（同校同专业同代号同计划同批 = 真重复）
    seen, uniq = set(), []
    for r in rows:
        k = (r["school"], r["major"], r["major_code"], r["plan"], r["batch"])
        if k in seen:
            continue
        seen.add(k); uniq.append(r)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["year", "school", "city", "owner", "major",
                                          "major_code", "plan", "batch", "page"])
        w.writeheader(); w.writerows(uniq)
    print(f"完成：{out_path}（候选行 {len(uniq)}，去重前 {len(rows)}）。")
    # AI 口径粗筛预览（仅 sanity check）
    AI = ["人工智能", "智能科学与技术", "数据科学与大数据技术", "计算机科学与技术", "软件工程",
          "网络工程", "信息安全", "物联网工程", "网络空间安全", "计算机类"]
    bysch = defaultdict(int)
    fj = [r for r in uniq if r["city"] in FJ_CITIES]
    for r in fj:
        if any(a in r["major"] for a in AI) and r["plan"].isdigit():
            bysch[r["school"]] += int(r["plan"])
    print(f"福建省内校 AI口径粗命中分校计划合计(预览，前15):")
    for s, p in sorted(bysch.items(), key=lambda x: -x[1])[:15]:
        print(f"  {s}: {p}")


def main():
    ap = argparse.ArgumentParser(description="2019 理工类招生计划 Word → 候选行")
    ap.add_argument("--dir", required=True, help="2019年福建省理工类招生计划 目录")
    ap.add_argument("--out", default="/tmp/enrollment_candidates_2019.csv")
    args = ap.parse_args()
    run(args.dir, args.out)


if __name__ == "__main__":
    main()
