#!/usr/bin/env python3
"""驱动：批量解析窗口年招生计划册 → 合并候选行 → 供给规模面板 + 闸门。

- 2020–2024（窗口年）本科各批次 物理/理工 科目组 PDF：parse_enrollment_pdf.run。
- 2019：理工类招生计划（Word，藏 RAR）→ bsdtar 解压 → parse_enrollment_2019_docx.run。
- 2025 超窗、各年高职专科批不纳入（pipeline 亦按批次剔除）。
合并候选行 → e_supply_scale_pipeline.run 出面板 + 闸门。

用法：python3 scripts/build_e_supply_scale.py --data-dir "<e-基本口径data 路径>"
"""
from __future__ import annotations
import argparse, csv, importlib.util, subprocess, tempfile, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


# 2019 理工类招生计划（Word，藏于 RAR）。bsdtar 解到临时目录后用 docx 解析器。
RAR_2019 = ["20190622201513_379.rar", "20190622201901_210.rar"]
DIR_2019_LIGONG = "2019年福建省理工类招生计划"

# 窗口年本科各批次 物理/理工 科目组 PDF（相对 data-dir；不含高职专科、不含历史）
YEAR_PDFS = {
    2020: ["200728.计划-理工类.pdf"],
    2021: ["物理组.pdf"],
    2022: ["2022年福建省普通高校招生计划（普通类物理科目组）.pdf"],
    2023: ["2023年福建省普通高校招生计划-物理科目组/2023年福建省普通高校招生计划物理科目组-本科批.pdf",
           "2023年福建省普通高校招生计划-物理科目组/2023年福建省普通高校招生计划物理科目组-本科提前批+高校农村专项+地方农村专项.pdf"],
    2024: ["20240626195004_31/2.2024年福建省普通高校招生计划物理科目组-本科批.pdf",
           "20240626195004_31/1.2024年福建省普通高校招生计划物理科目组-本科提前批+高校农村专项+地方农村专项.pdf"],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    args = ap.parse_args()
    D = Path(args.data_dir)
    parser = _load("parse_enrollment_pdf")
    p2019 = _load("parse_enrollment_2019_docx")
    pipe = _load("e_supply_scale_pipeline")

    combined = ROOT / "data" / "interim" / "e_supply_scale" / "all_years_candidates.csv"
    combined.parent.mkdir(parents=True, exist_ok=True)
    header = ["year", "school", "city", "owner", "major", "major_code", "plan", "batch", "page"]
    total = 0
    interim = combined.parent
    with open(combined, "w", newline="", encoding="utf-8-sig") as cf:
        w = csv.DictWriter(cf, fieldnames=header); w.writeheader()

        def merge(tmp):
            nonlocal total
            for r in csv.DictReader(open(tmp, encoding="utf-8-sig")):
                w.writerow({k: r.get(k, "") for k in header}); total += 1

        # 2019：解 RAR → docx 解析
        for rar in RAR_2019:
            if (D / rar).exists():
                with tempfile.TemporaryDirectory() as td:
                    subprocess.run(["bsdtar", "-xf", str(D / rar)], cwd=td, check=False)
                    lg = next(Path(td).rglob(DIR_2019_LIGONG), None)
                    if lg:
                        tmp = interim / "_y2019.csv"
                        print(f"解析 2019: {DIR_2019_LIGONG}（Word）…", flush=True)
                        p2019.run(str(lg), str(tmp)); merge(tmp); tmp.unlink(missing_ok=True)
                        break
        # 2020–2024：PDF
        for year, files in YEAR_PDFS.items():
            for rel in files:
                pdf = D / rel
                if not pdf.exists():
                    print(f"⚠ 缺文件，跳过：{rel}"); continue
                tmp = interim / f"_y{year}_{abs(hash(rel))%9999}.csv"
                print(f"解析 {year}: {Path(rel).name} …", flush=True)
                parser.run(str(pdf), year, str(tmp)); merge(tmp); tmp.unlink(missing_ok=True)
    print(f"\n合并候选行 {total} → {combined.relative_to(ROOT)}")
    print("=== 跑供给规模归一管道 ===")
    pipe.run(str(combined))
    print("\n完成。2025(超窗)未纳入；面板 population 待补；须人工抽查（2020 两栏年分校精度偏弱，见 audit 跳变）。")


if __name__ == "__main__":
    main()
