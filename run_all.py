from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent

STEPS = [
    "scripts/01_crawl_xiamen_public_basic_papers.py",
    "scripts/02_extract_public_basic_math.py",
    "scripts/03_analyze_trends_and_quantitative_comparison.py",
    "scripts/07_analyze_detailed_knowledge_ols.py",
    "scripts/04_predict_exam_trends.py",
    "scripts/05_generate_mock_paper.py",
    "scripts/06_generate_final_report.py",
]


def main() -> int:
    print("2026年起福建省中职公共基础数学命题趋势分析与模拟卷生成系统")
    print(f"Project root: {ROOT}")
    for idx, script in enumerate(STEPS, 1):
        print(f"\n[{idx}/{len(STEPS)}] Running {script}")
        result = subprocess.run([sys.executable, str(ROOT / script)], cwd=str(ROOT))
        if result.returncode != 0:
            print(f"Step failed: {script}", file=sys.stderr)
            return result.returncode
    print("\nAll steps completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
