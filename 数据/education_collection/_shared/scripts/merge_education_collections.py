from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(r"C:\金融专硕\论文\硕士毕业论文_Obsidian_MD统一整理_20260512\数据\education_collection")
OUTPUT = ROOT / "_shared"

DATA_COLUMNS = [
    "system",
    "indicator_code",
    "indicator_name",
    "scope_level",
    "province",
    "city",
    "school",
    "year",
    "value",
    "unit",
    "source_id",
    "collection_method",
    "confidence",
    "needs_manual_review",
    "notes",
]

SOURCE_COLUMNS = [
    "source_id",
    "source_title",
    "source_url",
    "publisher",
    "access_date",
    "source_type",
    "reliability_level",
    "raw_file_path",
    "notes",
]

AGENT_DIRS = [
    ROOT / "E1_conservative",
    ROOT / "E2_base",
    ROOT / "E3_broad",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [{k: (row.get(k, "") or "") for k in reader.fieldnames or []} for row in reader]


def normalize_rows(rows: list[dict[str, str]], columns: list[str], source_dir: Path) -> list[dict[str, str]]:
    normalized = []
    for row in rows:
        out = {col: row.get(col, "") for col in columns}
        out["_agent_dir"] = source_dir.name
        normalized.append(out)
    return normalized


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    data_rows: list[dict[str, str]] = []
    source_rows: list[dict[str, str]] = []
    report_lines = ["# 教育系统采集合并检查", ""]

    for agent_dir in AGENT_DIRS:
        data_path = agent_dir / "collected_data.csv"
        source_path = agent_dir / "source_register.csv"
        data = normalize_rows(read_csv(data_path), DATA_COLUMNS, agent_dir)
        sources = normalize_rows(read_csv(source_path), SOURCE_COLUMNS, agent_dir)
        data_rows.extend(data)
        source_rows.extend(sources)
        report_lines.append(f"- {agent_dir.name}: data_rows={len(data)}, source_rows={len(sources)}")

    write_csv(OUTPUT / "combined_education_collected_data.csv", data_rows, DATA_COLUMNS + ["_agent_dir"])
    write_csv(OUTPUT / "combined_source_register.csv", source_rows, SOURCE_COLUMNS + ["_agent_dir"])

    missing_source = [
        row for row in data_rows
        if row.get("source_id") and not any(src.get("source_id") == row.get("source_id") for src in source_rows)
    ]
    manual_review = [row for row in data_rows if row.get("needs_manual_review", "").strip().lower() in {"yes", "true", "1", "是"}]

    report_lines.extend([
        "",
        f"合并后数据行数：{len(data_rows)}",
        f"合并后来源行数：{len(source_rows)}",
        f"source_id 未在来源表中登记的数据行：{len(missing_source)}",
        f"标记需人工核验的数据行：{len(manual_review)}",
        "",
        "输出文件：",
        "- combined_education_collected_data.csv",
        "- combined_source_register.csv",
    ])

    (OUTPUT / "merge_report.md").write_text("\n".join(report_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
