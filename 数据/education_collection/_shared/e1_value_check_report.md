# E1 value 字段检查与修复报告

检查时间：2026-05-18 00:14:29

## 结论

- 原始 collected_data.csv 当前被其他进程占用，无法直接覆盖。
- 已生成修复版：C:\金融专硕\论文\硕士毕业论文_Obsidian_MD统一整理_20260512\数据\education_collection\E1_conservative\collected_data_value_filled.csv
- 修复版将自动采集程序已核验的 E1 数值回填：2018 年为 0，2020 年为 3。
- 2019、2021-2025 年仍为空，因为目前 PDF 解析未形成完整可核验结构化结果，不能编造。

## 修复版 E1 value 汇总
- E1_AI_MAJOR_COUNT / 2018: value=0, unit=个, confidence=A, manual=否
- E1_AI_MAJOR_COUNT / 2019: value=, unit=个, confidence=待核验, manual=是
- E1_AI_MAJOR_COUNT / 2020: value=3, unit=个, confidence=A, manual=否
- E1_AI_MAJOR_COUNT / 2021: value=, unit=个, confidence=待核验, manual=是
- E1_AI_MAJOR_COUNT / 2022: value=, unit=个, confidence=待核验, manual=是
- E1_AI_MAJOR_COUNT / 2023: value=, unit=个, confidence=待核验, manual=是
- E1_AI_MAJOR_COUNT / 2024: value=, unit=个, confidence=待核验, manual=是
- E1_AI_MAJOR_COUNT / 2025: value=, unit=个, confidence=待核验, manual=是
- E1_AI_SCHOOL_COUNT / 2018: value=0, unit=所, confidence=A, manual=否
- E1_AI_SCHOOL_COUNT / 2019: value=, unit=所, confidence=待核验, manual=是
- E1_AI_SCHOOL_COUNT / 2020: value=3, unit=所, confidence=A, manual=否
- E1_AI_SCHOOL_COUNT / 2021: value=, unit=所, confidence=待核验, manual=是
- E1_AI_SCHOOL_COUNT / 2022: value=, unit=所, confidence=待核验, manual=是
- E1_AI_SCHOOL_COUNT / 2023: value=, unit=所, confidence=待核验, manual=是
- E1_AI_SCHOOL_COUNT / 2024: value=, unit=所, confidence=待核验, manual=是
- E1_AI_SCHOOL_COUNT / 2025: value=, unit=所, confidence=待核验, manual=是
- E1_AI_INSTITUTE_COUNT / 2018-2025: value=, unit=个, confidence=待核验, manual=是
- E1_AI_GRAD_POINT / 2018-2025: value=, unit=个, confidence=待核验, manual=是
