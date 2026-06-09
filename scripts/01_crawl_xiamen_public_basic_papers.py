from __future__ import annotations

import html
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List

from common import LOGS_DIR, PROCESSED_DIR, RAW_DIR, setup_logger, write_xlsx


logger = setup_logger("crawl_xiamen_public_basic_papers", LOGS_DIR / "crawl_xiamen_public_basic_papers.log")

YEARS = ["2022", "2023", "2024", "2025", "2026"]
DOWNLOAD_DIR = RAW_DIR / "crawled_xiamen_public_basic"

KEYWORDS = [
    "厦门市中等职业学校学业水平考试 公共基础",
    "公共基础知识综合卷",
    "中职学考公共基础数学",
    "厦门 中职 公共基础 模拟卷 数学",
    "厦门市 中职 学考 公共基础知识 模拟试卷",
]

CURATED_SEEDS = [
    {
        "year": "2024",
        "title": "福建省教育厅关于公布福建省中等职业学校学业水平考试《公共基础知识》考试大纲的通知",
        "source_url": "https://jyt.fj.gov.cn/xxgk/zywj/202401/t20240118_6382673.htm",
        "source_platform": "福建省教育厅",
        "publish_date": "2024-01-15",
        "file_type": "html/pdf",
        "file_path": "",
        "is_downloaded": False,
        "is_full_paper": False,
        "math_part_found": True,
        "material_type": "考纲",
        "region": "福建",
        "relevance_score": 0.90,
        "evidence_level": "A-政府官网",
        "notes": "2025年起执行的公共基础知识考试大纲，含数学命题范围，已由用户本地PDF提供。",
    },
    {
        "year": "2025",
        "title": "福建省中等职业学校学业水平考试《中职数学》科目考试说明",
        "source_url": "local:user_uploaded_docx",
        "source_platform": "用户上传材料",
        "publish_date": "",
        "file_type": "docx",
        "file_path": "data/raw/syllabus/2025/福建省中等职业学校学业水平考试《中职数学》科目考试说明.docx",
        "is_downloaded": True,
        "is_full_paper": False,
        "math_part_found": True,
        "material_type": "考试说明",
        "region": "福建",
        "relevance_score": 0.92,
        "evidence_level": "A-本地原始材料",
        "notes": "用于提取数学部分知识点与能力要求。",
    },
    {
        "year": "2025",
        "title": "2025年福建省中等职业学校学业水平考试真题 数学卷",
        "source_url": "local:user_uploaded_pdf",
        "source_platform": "用户上传材料",
        "publish_date": "2025-06-14",
        "file_type": "pdf",
        "file_path": "data/raw/real_papers/2025/2025年福建省中等职业学校学业水平考试真题 数学卷20250614.pdf",
        "is_downloaded": True,
        "is_full_paper": True,
        "math_part_found": True,
        "material_type": "真题数学部分",
        "region": "福建",
        "relevance_score": 0.95,
        "evidence_level": "A-本地原始材料",
        "notes": "本地真题作为公共基础数学部分历史样本使用。",
    },
    {
        "year": "2023",
        "title": "2023年福建省中职学业水平考试数学真题",
        "source_url": "local:user_uploaded_pdf",
        "source_platform": "用户上传材料",
        "publish_date": "",
        "file_type": "pdf",
        "file_path": "data/raw/real_papers/2023/2023年福建省中职学业水平考试 数学真题.pdf",
        "is_downloaded": True,
        "is_full_paper": True,
        "math_part_found": True,
        "material_type": "真题数学部分",
        "region": "福建",
        "relevance_score": 0.95,
        "evidence_level": "A-本地原始材料",
        "notes": "本地真题作为公共基础数学部分历史样本使用。",
    },
    {
        "year": "2023",
        "title": "2023年厦门市中职学考公共基础合格性考试（试卷）",
        "source_url": "local:user_uploaded_pdf",
        "source_platform": "用户上传材料",
        "publish_date": "",
        "file_type": "pdf",
        "file_path": "data/raw/crawled_xiamen_public_basic/2023/2023年厦门市中职学考公共基础合格性考试（试卷）.pdf",
        "is_downloaded": True,
        "is_full_paper": True,
        "math_part_found": True,
        "material_type": "厦门公共基础综合卷I模拟/考试卷",
        "region": "厦门",
        "relevance_score": 0.98,
        "evidence_level": "A-用户提供本地原始材料",
        "notes": "公共基础合格性综合卷，含数学60分部分。",
    },
    {
        "year": "2024",
        "title": "2024年厦门市中等职业学校学生学业水平考试公共基础课综合卷I",
        "source_url": "local:user_uploaded_pdf",
        "source_platform": "用户上传材料",
        "publish_date": "",
        "file_type": "pdf",
        "file_path": "data/raw/crawled_xiamen_public_basic/2024/2024 年厦门市中等职业学校学生学业水平考试公共基础课综合卷I.pdf",
        "is_downloaded": True,
        "is_full_paper": True,
        "math_part_found": True,
        "material_type": "厦门公共基础综合卷I模拟/考试卷",
        "region": "厦门",
        "relevance_score": 0.98,
        "evidence_level": "A-用户提供本地原始材料",
        "notes": "公共基础合格性综合卷，含数学60分部分。",
    },
    {
        "year": "2024",
        "title": "2024公共基础课综合卷II",
        "source_url": "local:user_uploaded_pdf",
        "source_platform": "用户上传材料",
        "publish_date": "",
        "file_type": "pdf",
        "file_path": "data/raw/crawled_xiamen_public_basic/2024/2024公共基础课综合卷II.pdf",
        "is_downloaded": True,
        "is_full_paper": True,
        "math_part_found": True,
        "material_type": "厦门公共基础综合卷II模拟/考试卷",
        "region": "厦门",
        "relevance_score": 0.96,
        "evidence_level": "A-用户提供本地原始材料",
        "notes": "公共基础等级性综合卷，含数学30分部分。",
    },
    {
        "year": "2026",
        "title": "2026年福建厦门市中等职业学校学业水平模拟测试数学试卷",
        "source_url": "local:user_uploaded_docx",
        "source_platform": "用户上传材料",
        "publish_date": "",
        "file_type": "docx",
        "file_path": "data/raw/crawled_xiamen_public_basic/2026/【试卷】2026年福建厦门市中等职业学校学业水平模拟测试数学试卷.docx",
        "is_downloaded": True,
        "is_full_paper": True,
        "math_part_found": True,
        "material_type": "厦门数学模拟测试卷",
        "region": "厦门",
        "relevance_score": 0.99,
        "evidence_level": "A-用户提供本地原始材料",
        "notes": "2026年厦门数学模拟测试卷，当前原卷满分100分；本轮生成卷按用户最新指定的15选、5填、4解结构执行。",
    },
]


def fetch_url(url: str, timeout: int = 15) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Codex educational research crawler)",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(3_000_000)


def strip_tags(text: str) -> str:
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def duckduckgo_search(query: str) -> List[Dict[str, str]]:
    url = "https://duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    raw = fetch_url(url)
    page = raw.decode("utf-8", errors="replace")
    out = []
    for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page, flags=re.S):
        href = html.unescape(m.group(1))
        title = strip_tags(m.group(2))
        parsed = urllib.parse.urlparse(href)
        qs = urllib.parse.parse_qs(parsed.query)
        if "uddg" in qs:
            href = qs["uddg"][0]
        out.append({"title": title, "url": href})
    return out[:10]


def platform_from_url(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower()
    if "xm" in host and ("gov" in host or "edu" in host):
        return "厦门政府/教育机构"
    if "fj" in host and "gov" in host:
        return "福建政府/教育机构"
    if "wenku.baidu" in host:
        return "百度文库"
    if "doc88" in host:
        return "道客巴巴"
    if "docin" in host:
        return "豆丁"
    if host:
        return host
    return "未知"


def evidence_level(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower()
    if "gov.cn" in host or "edu.cn" in host:
        return "A-政府/教育官网"
    if any(x in host for x in ["wenku.baidu", "doc88", "docin"]):
        return "C-公开文库平台"
    return "C-公开网页线索"


def score_result(title: str, url: str, year: str) -> float:
    text = f"{title} {url}".lower()
    score = 0.0
    for key in ["厦门", "中职", "中等职业", "学业水平", "公共基础", "数学", "综合卷", "模拟"]:
        if key.lower() in text:
            score += 0.08
    if year in text:
        score += 0.10
    if any(ext in urllib.parse.urlparse(url).path.lower() for ext in [".pdf", ".doc", ".docx", ".xls", ".xlsx"]):
        score += 0.12
    if "gov.cn" in url or "edu.cn" in url:
        score += 0.10
    return round(min(score, 1.0), 2)


def maybe_download(url: str, title: str, year: str) -> tuple[str, bool, str]:
    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
    if suffix not in [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".html", ".htm"]:
        return "", False, "html"
    out_dir = DOWNLOAD_DIR / year
    out_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", title)[:90] or "downloaded_material"
    out = out_dir / f"{safe}{suffix}"
    try:
        out.write_bytes(fetch_url(url, timeout=20))
        rel = out.relative_to(DOWNLOAD_DIR.parents[1])
        logger.info("Downloaded %s -> %s", url, out)
        return str(rel), True, suffix.lstrip(".")
    except Exception as exc:
        logger.warning("Download failed %s: %s", url, exc)
        return "", False, suffix.lstrip(".") or "html"


def main() -> None:
    logger.info("Start crawling Xiamen public basic papers")
    rows: List[Dict[str, object]] = [dict(x) for x in CURATED_SEEDS]
    seen = {r["source_url"] for r in rows}
    for year in YEARS:
        for keyword in KEYWORDS:
            query = f"{year} {keyword}"
            logger.info("Search query: %s", query)
            try:
                results = duckduckgo_search(query)
            except Exception as exc:
                logger.warning("Search failed %s: %s", query, exc)
                continue
            for item in results:
                url = item["url"]
                if url in seen:
                    continue
                seen.add(url)
                score = score_result(item["title"], url, year)
                if score < 0.30:
                    continue
                file_path, downloaded, file_type = maybe_download(url, item["title"], year)
                rows.append(
                    {
                        "year": year,
                        "title": item["title"],
                        "source_url": url,
                        "source_platform": platform_from_url(url),
                        "publish_date": "",
                        "file_type": file_type,
                        "file_path": file_path,
                        "is_downloaded": downloaded,
                        "is_full_paper": "卷" in item["title"] or "试卷" in item["title"],
                        "math_part_found": "数学" in item["title"],
                        "material_type": "厦门公共基础模拟卷线索" if "厦门" in item["title"] else "公共基础材料线索",
                        "region": "厦门" if "厦门" in item["title"] or "xiamen" in url.lower() else "福建/其他",
                        "relevance_score": score,
                        "evidence_level": evidence_level(url),
                        "notes": "自动检索结果；需人工复核是否为公共基础综合卷且含数学部分。",
                    }
                )
            time.sleep(0.35)
    out = PROCESSED_DIR / "xiamen_public_basic_sources.xlsx"
    write_xlsx({"sources": rows}, out)
    logger.info("Output %s with %s rows", out, len(rows))
    if not any(r.get("is_downloaded") and r.get("region") == "厦门" for r in rows):
        logger.warning("No downloaded Xiamen public basic mock paper was verified in this run.")


if __name__ == "__main__":
    main()
