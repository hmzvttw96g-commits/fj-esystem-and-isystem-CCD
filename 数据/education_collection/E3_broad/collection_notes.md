# E3 扩大口径数据采集阶段说明

生成日期：2026-05-17

## 当前阶段产出

- 已写出 `collected_data.csv`、`source_register.csv`、`collection_notes.md`。
- 已下载教育部 2018-2024 年度普通高等学校本科专业备案和审批结果原件到 `raw/`。
- 当前唯一完成结构化计数且可核验的记录为：2020 年福建省 E3_SUPPORT_MAJOR_COUNT = 2，来源为教育部 2020 年度本科专业备案和审批结果 xls。

## 最可靠的数据源

1. E3_SUPPORT_MAJOR_COUNT：教育部年度普通高等学校本科专业备案和审批结果，可靠性 A。
2. E3_AI_X_COURSE_COUNT：高校教务处、课程中心、培养方案 PDF/网页，可靠性通常为 A/B，但当前阶段未采集。
3. E3_AI_COMPETITION_BASE：省教育厅竞赛/基地公示、赛事官网、高校创新创业学院官网，可靠性 A/B，但当前阶段未采集。
4. E3_UNIV_AI_PUBLICATION：CNKI、Web of Science、Scopus 或高校科研统计导出；需要数据库权限或高校统计口径。
5. E3_UNIV_AI_PATENT：国家知识产权局、Incopat、智慧芽或高校知识产权平台；需要批量检索和申请人类型清洗。

## 可自动采集与不可自动采集判断

- 可自动采集：E3_SUPPORT_MAJOR_COUNT。教育部年度备案/审批文件可下载，但不同年份格式包括 docx、xls、pdf，2019 年 pdf 当前文本抽取效果不稳定，仍需 OCR 或人工表格化。
- 半自动采集：E3_AI_COMPETITION_BASE。若省教育厅或赛事官网有结构化名单，可自动抽取；否则需要人工核验高校、年份和基地属性。
- 需人工/数据库导出：E3_AI_X_COURSE_COUNT、E3_UNIV_AI_PUBLICATION、E3_UNIV_AI_PATENT。课程数据分散在高校培养方案和课程中心；论文和专利必须依赖数据库检索式、申请人/作者单位清洗和年份口径复核。

## 当前数据限制

- 教育部本科专业备案和审批结果反映的是“当年新增备案/审批/调整”等年度结果，不等同于福建省高校存量开设专业总数。
- 当前只对 2020 年 xls 完成了福建省支撑专业清单结构化筛选：计算机科学与技术 2 条；其他年份虽已下载原件，但尚未形成全量可复核计数。
- 所有未核验到的数值均在 `collected_data.csv` 中留空，并标注 `needs_manual_review=是`。

## 是否支撑主模型

当前 E3 扩大口径不建议进入主模型。原因是支撑专业、AI+X课程、竞赛基地、论文和专利均存在外延较宽或知识产出属性强的问题，容易把一般数字化能力、科研产出和教育供给混在一起。

建议主模型仍优先使用 E2_CORE_MAJOR_COUNT 和 E2_CORE_SCHOOL_COUNT。E3_SUPPORT_MAJOR_COUNT 可作为稳健性检验；E3_AI_X_COURSE_COUNT 和 E3_AI_COMPETITION_BASE 可作为教育扩散/实践能力补充；E3_UNIV_AI_PUBLICATION、E3_UNIV_AI_PATENT 更适合单列为高校 AI 知识产出机制变量或拓展检验，不宜与专业数量简单合成。
