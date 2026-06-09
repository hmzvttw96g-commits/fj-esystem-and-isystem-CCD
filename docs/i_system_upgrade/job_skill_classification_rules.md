# 岗位—技能识别规则

本文档用于 I 端产业系统升级版试点。规则只用于岗位/技能候选数据的实验性分类，不得倒填历史年份，也不得直接替代当前 experimental I_index。

## 1. 分类规则

1. 命中 `strong_ai_keywords >= 1`：
   `job_classification = ai_job_strong`

2. 命中 `ai_tool_keywords >= 1`，且岗位标题或描述包含“技术、研发、工程师、算法、开发、数据”之一：
   `job_classification = ai_job_tool_based`

3. 命中 `basic_digital_keywords >= 2`，且岗位标题或描述包含“技术、研发、工程师、开发、数据”之一：
   `job_classification = digital_tech_job`

4. 命中 `industrial_digital_keywords >= 1`，且岗位标题或描述包含“工程师、技术、研发、自动化、制造、设备、工业”之一：
   `job_classification = industrial_digital_job`

5. 只命中 `weak_keywords`：
   `job_classification = weak_only_review`

6. 没有有效命中：
   `job_classification = non_ai_job`

## 2. C/B/X 口径

- C 保守口径 = `ai_job_strong + ai_job_tool_based`
- B 基本口径 = `C + digital_tech_job`
- X 扩大口径 = `B + industrial_digital_job`
- `weak_only_review` 不直接纳入任何口径，只进入人工复核。

## 3. 人工复核原则

- 岗位标题只出现“智能、科技、平台、系统”等弱词时，不应自动认定为 AI 或数字技术岗位。
- 制造业岗位需要结合岗位描述识别是否涉及工业互联网、机器视觉、智能制造、自动化控制、工业软件等实质性数字化技能。
- 同一岗位多次发布时，需要保留原始记录，但城市—年份面板汇总时应标记去重口径。
- 岗位年份应以发布时间或招聘公告发布时间为准，不能用当前页面抓取日期倒推历史年份。


## 4. 系统边界规则

岗位分类前必须先识别 `employer_sector`。高校自身岗位、政府事业单位岗位、金融机构岗位优先按系统边界排除或转端，不能仅因命中 AI/数字技术关键词就进入 I_job。

- 高校自身教师、科研、实验员、事业编、辅导员、行政岗位：转入 `E_education_extension`，不进入 I_job。
- 政府机关、事业单位、公共部门信息化岗位：转入 `G_public_sector_digital_demand` 或 `exclude_or_review`，不进入 I_job。
- 金控、银行、基金、担保、融资平台等金融岗位：转入 `F_financial_candidate`，不进入当前 E-I 主模型。
- 只有企业产业端岗位才能进入 I_job，包括制造业、软件信息服务、工业互联网、智能制造企业岗位。
- 高校就业网中的企业岗位和高校自身岗位必须区分；前者可作为 I_job 候选，后者转入 E_extension。
- weak_only_review 不直接进入 C/B/X 口径。

## 5. 研究员/科研岗 v2 判定字段

岗位候选表和人工复核表建议增加以下字段：

- `employer_sector`：用人单位部门属性，如 `university`、`government_agency`、`public_institution`、`industry_research_institute`、`enterprise`、`financial_institution`、`unknown`。
- `job_function`：岗位功能，如 `teaching`、`academic_research`、`public_sector_it`、`enterprise_r_and_d`、`tech_transfer`、`engineering_application`、`industrialization_service`、`project_evidence`、`unknown`。
- `system_mapping`：系统归属，如 `I_industry`、`I_tech_transfer_candidate`、`E_research_extension`、`G_public_sector_digital_demand`、`F_financial_candidate`、`I_project_evidence_only`、`manual_review_required`。
- `evidence_level`：证据强度，如 `explicit_job_record`、`attachment_pending`、`project_or_policy_evidence`、`weak_text_only`、`insufficient_evidence`。
- `include_in_I_job`：是否进入 I_job 主模型。只有企业产业端岗位或人工确认后的产业技术转化岗位可以为 true。
- `manual_review_priority`：人工复核优先级，建议取值 `high`、`medium`、`low`。

`evidence_level` 建议采用 A-H 分级：

- A：官方或高校就业来源中的企业岗位记录，具备企业主体、岗位名称、年份、城市和 source_url，可进入 I_job 候选。
- B：官方或高校就业来源转载/归档的企业岗位记录，字段较完整，但仍需人工核验原始公告或附件。
- C：官方招聘会、就业活动、双选会或岗位表附件线索，企业和岗位方向存在但附件待人工解析。
- D：政府产业项目、政策、科技计划、智能制造或工业互联网项目证据，只能进入 `I_project_evidence_only`。
- E：企业名单、平台名录、高新技术企业、产教融合企业等主体证据，只能进入 `I_firm_evidence_only`。
- F：高校、政府、事业单位、金融机构等边界排除证据，按 E/G/F 端或人工复核处理。
- G：弱关键词或岗位功能不清晰记录，进入 `manual_review_required`。
- H：页面不可用、信息不足或无法判断的记录，暂不进入 I_job。

## 6. 研究员/科研岗 v2 判断规则

1. 先判断 `employer_sector`，区分高校、普通事业单位、产业技术研究院、新型研发机构、企业、金融机构和政府机关。
2. 再判断 `job_function`，特别区分教学/学术科研、公共部门信息化、企业研发、技术转化、工程化、产业化应用和企业服务。
3. 最后判断 `system_mapping`，不得只依据岗位关键词或单位性质一刀切。
4. 对 `research`、`researcher`、`研究员`、`科研岗`，不自动排除，也不自动纳入 I 端。
5. 只有证据明确显示岗位服务企业研发、技术转化、工程化、产业化应用或企业服务时，才可标记为 `I_tech_transfer_candidate`，并进入高优先级人工复核。
6. 高校内部学术科研、教师、实验员岗位进入 `E_research_extension` 或 `E_education_extension`。
7. 普通政府机关、事业单位内部信息化岗位进入 `G_public_sector_digital_demand`。
8. 无法判断产业转化功能的研究员/科研岗进入 `manual_review_required`，不得直接进入 C/B/X。
