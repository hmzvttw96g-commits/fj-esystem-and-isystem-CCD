# E/I 系统边界审计报告

## 1. 本次运行信息
- run_id：20260606_100516
- 扫描目录：data、data/interim、data/panel、data/audit、outputs/tables、outputs/figures、config、scripts、docs、paper_framework.md
- 输出文件：
  - data/audit/system_boundary_audit/20260606_100516/system_boundary_audit_file_inventory_20260606_100516.xlsx
  - data/audit/system_boundary_audit/latest_system_boundary_audit_file_inventory.xlsx
  - data/interim/system_boundary_audit/20260606_100516/system_boundary_audit_job_record_review_20260606_100516.xlsx
  - data/interim/system_boundary_audit/latest_system_boundary_audit_job_record_review.xlsx
  - data/interim/system_boundary_audit/20260606_100516/system_boundary_corrected_mapping_template_20260606_100516.xlsx
  - data/interim/system_boundary_audit/latest_system_boundary_corrected_mapping_template.xlsx
  - data/audit/system_boundary_audit/20260606_100516/system_boundary_audit_report_20260606_100516.md
  - data/audit/system_boundary_audit/latest_system_boundary_audit_report.md

## 2. 审计背景
本轮审计用于检查 E-I 双系统 CCD 中是否存在教育端、产业端、金融端和公共部门之间的边界污染。近期岗位/技能试点中出现高校教师岗、事业单位岗位和金控信息技术岗，若直接进入 I_job，会造成 E/I 系统重合或误把非产业岗位当作产业承接。

## 3. 当前 CCD 主结果是否受影响
- 当前已跑 CCD 是否直接使用了高校事业编岗位：否。
- 当前已跑 CCD 主要由 E_index/I_index 面板构成；已有文件显示 I 端当前主结果仍是企业存量、专利申请等实验性候选变量，并未把本轮岗位试点记录写入 latest experimental base panel。
- 当前 CCD 主结果不需要立即重算。
- 需要增加边界风险说明的结论：泉州 2019/2020 I_index=0 的升级复核、岗位/技能试点采集结论、I_index_upgraded_C/B/X 设计说明。

## 4. 发现的系统边界风险
- 高校岗位/E_extension 风险记录：13
- 政府/事业单位/G_public_sector 风险记录：19
- 金融机构/F_candidate 风险记录：5
- 项目证据/I_project_evidence_only 记录：21

| source_file | row_id | employer_name | job_title | original_job_classification | corrected_system_mapping | correction_reason |
| --- | --- | --- | --- | --- | --- | --- |
| data/interim/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_official_job_candidates.xlsx | 01_job_candidates:2 | 泉州师范学院 | 教师A24（计算机/软件工程/人工智能/物联网工程方向） | ai_job_strong | E_education_extension | 高校自身教师/科研/事业编岗位属于教育系统延伸，不能进入 I_job。 |
| data/interim/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_official_job_candidates.xlsx | 01_job_candidates:3 | 泉州金控集团及权属企业 | 信息技术岗 | weak_only_review | F_financial_candidate | 金控/银行/基金/担保/融资平台岗位属于 F 端候选，不进入当前 E-I 主模型。 |
| data/interim/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_official_job_candidates.xlsx | 02_source_pages:2 | 泉州市国资委八家市属国企赴福州大学招聘公告 |  |  | exclude_or_review | 边界不明确，需要人工复核。 |
| data/interim/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_official_job_candidates.xlsx | 02_source_pages:3 | 福州大学2019届毕业生泉港石化专场双选会 |  |  | exclude_or_review | 高校就业信息网来源页可能包含企业招聘，需区分企业岗位和高校自身岗位后再决定。 |
| data/interim/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_official_job_candidates.xlsx | 02_source_pages:4 | 2020年泉州师范学院公开招聘博士研究生学历学位教师公告 |  |  | E_education_extension | 高校自身教师/科研/事业编岗位属于教育系统延伸，不能进入 I_job。 |
| data/interim/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_official_job_candidates.xlsx | 02_source_pages:5 | 2020年泉州市事业单位公开招聘编制内工作人员公告 |  |  | G_public_sector_digital_demand | 政府机关、事业单位、公共部门岗位不进入 I_job。 |
| data/interim/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_official_job_candidates.xlsx | 02_source_pages:6 | 泉州市金控集团及权属企业公开招聘公告 |  |  | F_financial_candidate | 金控/银行/基金/担保/融资平台岗位属于 F 端候选，不进入当前 E-I 主模型。 |
| data/interim/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_official_job_candidates.xlsx | 02_source_pages:7 | 泉州市工信局推进5G+工业互联网和智能制造报道 |  |  | I_project_evidence_only | 项目公告只能作为 I_project_evidence，不计入岗位数量。 |
| data/interim/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_official_job_candidates.xlsx | 02_source_pages:8 | 2019年泉州市级科技计划项目公示 |  |  | I_project_evidence_only | 项目公告只能作为 I_project_evidence，不计入岗位数量。 |
| data/interim/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_official_job_candidates.xlsx | 02_source_pages:9 | 2020年丰泽区科技计划项目立项 |  |  | I_project_evidence_only | 项目公告只能作为 I_project_evidence，不计入岗位数量。 |
| data/interim/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_official_job_candidates.xlsx | 03_attachment_candidates:2 | 2020年泉州市事业单位公开招聘编制内工作人员岗位信息表 | 岗位信息表及其他附件（RAR） |  | G_public_sector_digital_demand | 政府机关、事业单位、公共部门岗位不进入 I_job。 |
| data/interim/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_official_job_candidates.xlsx | 03_attachment_candidates:3 | 泉州师范学院公开招聘岗位需求表 | 2020年泉州师范学院公开招聘博士研究生学历学位教师岗位需求信息表 |  | E_education_extension | 高校自身教师/科研/事业编岗位属于教育系统延伸，不能进入 I_job。 |
| data/interim/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_official_job_candidates.xlsx | 04_government_project_evidence:2 | 2019年泉州市级科技计划项目公示 | 机器视觉/智能控制/工业互联网相关科技计划项目 |  | I_project_evidence_only | 项目公告只能作为 I_project_evidence，不计入岗位数量。 |
| data/interim/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_official_job_candidates.xlsx | 04_government_project_evidence:3 | 泉州市工信工作总结 | 数字化车间、智能制造试点、工业互联网平台 |  | I_project_evidence_only | 项目公告只能作为 I_project_evidence，不计入岗位数量。 |
| data/interim/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_official_job_candidates.xlsx | 04_government_project_evidence:4 | 泉州市工信局推进5G+工业互联网和智能制造报道 | 5G+工业互联网与智能制造 |  | I_project_evidence_only | 项目公告只能作为 I_project_evidence，不计入岗位数量。 |
| data/interim/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_official_job_candidates.xlsx | 04_government_project_evidence:5 | 2020年丰泽区科技计划项目立项 | 物联网、AI算法、物流信息化等科技项目 |  | I_project_evidence_only | 项目公告只能作为 I_project_evidence，不计入岗位数量。 |
| data/interim/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_official_job_candidates.xlsx | 04_government_project_evidence:6 | 泉州市工信局2020年工作总结 | 智能制造、工业互联网、上云上平台 |  | I_project_evidence_only | 项目公告只能作为 I_project_evidence，不计入岗位数量。 |
| data/interim/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_official_job_candidates.xlsx | 05_manual_review_required:2 | 2020年泉州市事业单位公开招聘编制内工作人员岗位信息表 |  |  | G_public_sector_digital_demand | 政府机关、事业单位、公共部门岗位不进入 I_job。 |
| data/interim/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_official_job_candidates.xlsx | 05_manual_review_required:3 | 泉州师范学院公开招聘岗位需求表 |  |  | E_education_extension | 高校自身教师/科研/事业编岗位属于教育系统延伸，不能进入 I_job。 |
| data/interim/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_official_job_candidates.xlsx | 05_manual_review_required:4 | 2020年泉州师范学院公开招聘博士研究生学历学位教师公告 |  |  | E_education_extension | 高校自身教师/科研/事业编岗位属于教育系统延伸，不能进入 I_job。 |

## 5. 修正规则
- 高校教师/科研/实验员/事业编岗位：转入 E_education_extension，不进入 I_job。
- 金控、银行、基金、担保、融资平台岗位：转入 F_financial_candidate，不进入当前 E-I 主模型。
- 政府机关、事业单位、公共部门信息化岗位：转入 G_public_sector_digital_demand，不进入 I_job。
- 智能制造、工业互联网、数字化转型项目公告：进入 I_project_evidence_only，不计入岗位数量。
- 企业名单、高新技术企业名单、专精特新名单：进入 I_firm_evidence_only 或 entity_evidence，不伪装为岗位。
- 民营制造业、软件信息服务、工业互联网、智能制造企业岗位：可作为 I_industry 候选并人工复核。

## 6. 已修正文档
- /Users/greenbarry/Documents/Codex/2026-06-04/imported-codex-24/docs/system_boundary/e_i_system_boundary_rules.md
- /Users/greenbarry/Documents/Codex/2026-06-04/imported-codex-24/docs/i_system_upgrade/job_skill_classification_rules.md
- /Users/greenbarry/Documents/Codex/2026-06-04/imported-codex-24/docs/i_system_upgrade/i_system_upgrade_indicator_design.md

## 7. 对泉州 2019/2020 试点的影响
- 泉州师范学院教师岗不能挑战 I_index=0，应转入 E_education_extension。
- 泉州金控信息技术岗不能直接挑战 I_index=0，应转入 F_financial_candidate。
- 真正能挑战 I_index=0 的应是企业产业端岗位、项目证据或企业主体证据；但项目证据只能作为项目证据，不能计入岗位数量。
- 2020 年已有试点岗位证据需要重映射后再判断：高校教师岗和金控信息岗都不能直接作为 I_job 主模型证据。

## 8. 下一步建议
- 不需要立即重新跑 CCD。
- 需要修正岗位候选表或在后续 I_index_upgraded 构造前应用 corrected mapping。
- 继续泉州民企数字化证据采集，重点找制造业、软件信息服务、工业互联网、智能制造企业岗位。
- 暂不构造正式 I_index_upgraded_C/B/X；先完成附件和来源 URL 人工复核。
- 后续构造 C/B/X 时必须使用固定口径，不得按城市动态调权。