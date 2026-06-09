from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

from common import (
    LOGS_DIR,
    PROCESSED_DIR,
    RAW_DIR,
    clean_text,
    parse_questions_from_text,
    read_supported_text,
    setup_logger,
    syllabus_points_from_text,
    write_xlsx,
)


logger = setup_logger("extract_public_basic_math", LOGS_DIR / "extract_public_basic_math.log")

PUBLIC_FIELDS = [
    "source_type",
    "region",
    "year",
    "file_name",
    "question_id",
    "question_type",
    "question_text",
    "options",
    "score",
    "answer",
    "solution",
    "knowledge_point",
    "detailed_knowledge_point",
    "chapter",
    "difficulty",
    "has_image",
    "has_formula",
    "is_math_question",
    "confidence",
    "needs_manual_review",
    "review_reason",
]


def infer_year(path: Path) -> str:
    m = re.search(r"(20\d{2})", str(path))
    return m.group(1) if m else ""


def source_meta(path: Path) -> Dict[str, str]:
    rel = path.relative_to(RAW_DIR)
    parts = rel.parts
    if parts[0] == "real_papers":
        return {"source_type": "real_paper_math_part", "region": "福建", "year": parts[1] if len(parts) > 1 else infer_year(path)}
    if parts[0] == "syllabus":
        return {"source_type": "syllabus_math_part", "region": "福建", "year": parts[1] if len(parts) > 1 else infer_year(path)}
    if parts[0] == "crawled_xiamen_public_basic":
        return {"source_type": "xiamen_public_basic_mock", "region": "厦门", "year": parts[1] if len(parts) > 1 else infer_year(path)}
    return {"source_type": "unknown", "region": "", "year": infer_year(path)}


def extract_math_section(text: str, source_type: str) -> Tuple[str, float, str]:
    text = clean_text(text)
    if not text:
        return "", 0.0, "no_text"
    if source_type in {"real_paper_math_part", "syllabus_math_part"}:
        return text, 0.95, "source_is_math_or_syllabus"
    math_hits = len(re.findall(r"数学|函数|集合|不等式|三角|数列|向量|圆|直线|概率|统计", text))
    # Public-basic comprehensive papers usually contain a score table near the
    # cover with "数学"; that is not the subject body. Prefer a standalone
    # subject heading followed by a question section.
    subject_candidates = []
    for m in re.finditer(r"(?m)^\s*数\s*学\s*$|数\s*学\s*\n\s*一[、.]", text):
        if m.start() > 400:
            subject_candidates.append(m.start())
    if subject_candidates:
        start = subject_candidates[0]
        tail = text[start + 20 :]
        end_candidates = []
        for pat in [r"(?m)^\s*英\s*语\s*$", r"英\s*语\s*\n\s*一[、.]", r"(?m)^\s*语\s*文\s*$", r"(?m)^\s*德\s*育\s*$"]:
            m = re.search(pat, tail)
            if m:
                end_candidates.append(start + 20 + m.start())
        end = min(end_candidates) if end_candidates else len(text)
        return text[start:end], min(0.95, 0.65 + math_hits * 0.02), "standalone_math_subject_heading_found"
    if math_hits >= 4:
        starts = [m.start() for m in re.finditer(r"(中职数学|数学部分|《数学》试卷|数学试卷)", text)]
        if starts:
            start = starts[0]
            end_candidates = []
            for pat in [r"语文", r"英语", r"思想政治", r"德育", r"公共基础知识.*结束"]:
                m = re.search(pat, text[start + 20 :])
                if m:
                    end_candidates.append(start + 20 + m.start())
            end = min(end_candidates) if end_candidates else len(text)
            section = text[start:end]
            return section, min(0.90, 0.45 + math_hits * 0.03), "math_heading_found"
        return text, min(0.78, 0.35 + math_hits * 0.025), "math_keywords_found"
    return text, min(0.35, math_hits * 0.05), "low_math_signal"


def enrich_question(row: Dict[str, object], confidence: float, reason: str) -> Dict[str, object]:
    q_text = str(row.get("question_text") or "")
    kp = str(row.get("knowledge_point") or "")
    detail = str(row.get("detailed_knowledge_point") or "")
    is_math = (
        kp not in {"其他", ""}
        or detail not in {"", "其他待人工复核"}
        or bool(re.search(r"函数|集合|不等式|三角|数列|向量|圆|直线|概率|统计|log|sin|cos|x|y|棱柱|棱锥|视图|斜率|方程", q_text, re.I))
    )
    needs_review = confidence < 0.55 or not is_math or len(q_text) < 12
    row["is_math_question"] = bool(is_math)
    row["confidence"] = round(confidence, 2)
    row["needs_manual_review"] = bool(needs_review)
    row["review_reason"] = "" if not needs_review else f"{reason}; math={is_math}; text_len={len(q_text)}"
    for field in PUBLIC_FIELDS:
        row.setdefault(field, "")
    return row


def main() -> None:
    logger.info("Start extracting public basic math")
    paths = sorted([p for p in RAW_DIR.rglob("*") if p.suffix.lower() in {".pdf", ".docx", ".txt", ".md", ".html", ".htm", ".xlsx", ".xlsm", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"}])
    rows: List[Dict[str, object]] = []
    manual: List[Dict[str, object]] = []
    file_status: List[Dict[str, object]] = []
    for path in paths:
        meta = source_meta(path)
        try:
            text, read_meta = read_supported_text(path)
            math_text, confidence, reason = extract_math_section(text, meta["source_type"])
            if meta["source_type"] == "syllabus_math_part":
                extracted = syllabus_points_from_text(math_text, year=meta["year"], file_name=path.name)
            else:
                extracted = parse_questions_from_text(
                    math_text,
                    source_type=meta["source_type"],
                    school="",
                    year=meta["year"],
                    file_name=path.name,
                )
            for r in extracted:
                r["source_type"] = meta["source_type"]
                r["region"] = meta["region"]
                r = enrich_question(r, confidence, reason)
                rows.append(r)
                if r["needs_manual_review"]:
                    manual.append(r)
            status = "ok" if extracted else "no_math_questions_extracted"
            if read_meta.get("ocr_failed"):
                status = "ocr_or_text_extraction_failed"
            file_status.append(
                {
                    "file_path": str(path.relative_to(RAW_DIR)),
                    "source_type": meta["source_type"],
                    "region": meta["region"],
                    "year": meta["year"],
                    "chars_extracted": len(text),
                    "math_chars": len(math_text),
                    "question_rows": len(extracted),
                    "confidence": round(confidence, 2),
                    "ocr_failed": bool(read_meta.get("ocr_failed")),
                    "status": status,
                    "notes": reason if not read_meta.get("ocr_failed") else f"{reason}; OCR引擎不可用或文本层为空，需人工OCR。",
                }
            )
            if status != "ok":
                manual.append(
                    {
                        "source_type": meta["source_type"],
                        "region": meta["region"],
                        "year": meta["year"],
                        "file_name": path.name,
                        "question_id": "",
                        "question_type": "",
                        "question_text": "",
                        "options": "",
                        "score": "",
                        "answer": "",
                        "solution": "",
                        "knowledge_point": "",
                        "chapter": "",
                        "difficulty": "",
                        "has_image": "",
                        "has_formula": "",
                        "is_math_question": False,
                        "confidence": round(confidence, 2),
                        "needs_manual_review": True,
                        "review_reason": status,
                    }
                )
            logger.info("Processed %s status=%s rows=%s", path, status, len(extracted))
        except Exception as exc:
            logger.exception("Failed %s: %s", path, exc)
            file_status.append(
                {
                    "file_path": str(path.relative_to(RAW_DIR)),
                    "source_type": meta["source_type"],
                    "region": meta["region"],
                    "year": meta["year"],
                    "chars_extracted": 0,
                    "math_chars": 0,
                    "question_rows": 0,
                    "confidence": 0,
                    "ocr_failed": True,
                    "status": "failed",
                    "notes": str(exc),
                }
            )
    out = PROCESSED_DIR / "all_public_basic_math_questions.xlsx"
    review = PROCESSED_DIR / "math_questions_need_manual_review.xlsx"
    write_xlsx({"questions": rows, "file_status": file_status}, out)
    write_xlsx({"manual_review": manual, "file_status": file_status}, review)
    logger.info("Output %s rows=%s and %s manual=%s", out, len(rows), review, len(manual))


if __name__ == "__main__":
    main()
