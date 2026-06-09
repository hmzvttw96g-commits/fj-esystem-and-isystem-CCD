# 泉州民企数字化岗位采集与 I 端系统边界审计报告

## 1. 本次运行信息

- run_id：20260606_171849
- 采集城市：泉州
- 采集年份：2019、2020
- latest experimental base panel：data/panel/experimental_analysis/latest_experimental_analysis_base_panel_2019_2024.csv
- 本轮不重算 CCD，不覆盖 latest experimental base panel，不使用 legacy 文件。

## 2. 本轮收集的来源

- 泉州市国资委八家市属国企赴福州大学招聘公告：official_state_owned_enterprise_recruitment，https://gzw.quanzhou.gov.cn/gzdt/tzgg/201904/t20190408_1492150.htm
- 泉州兰台信息科技股份公司招聘简章：university_employment_page，https://jy.mbu.cn/index.php?s=/home/article/detail/id/1411.html
- 泉州三安半导体科技有限公司2019招聘：university_employment_archive，https://archiverm.yingjiesheng.com/job-003-999-096.html
- 福建省晋华集成电路有限公司招聘：university_employment_page，https://apd.wh.sdu.edu.cn/info/1567/4380.htm
- 晋华集成电路2020春季校园招聘岗位页：official_campus_recruitment_page，https://campus.51job.com/jhicc/job.html
- 泉州市金控集团及权属企业公开招聘公告：official_state_owned_enterprise_recruitment，https://www.quanzhou.gov.cn/zfb/xxgk/zfxxgkzl/rsxx/zkzp/202006/t20200602_2303269.htm
- 2020年泉州师范学院公开招聘博士研究生学历学位教师公告：official_public_institution_recruitment，https://rsj.quanzhou.gov.cn/zwgk/zxdt/tzgg/202004/t20200430_2234402.htm
- 2020年泉州市事业单位公开招聘编制内工作人员岗位信息表：official_hr_recruitment_attachment，https://rsj.quanzhou.gov.cn/zwgk/zxdt/syzk/202008/t20200810_2403095.htm
- 借力5G+智能制造 创新产业数字发展：government_industry_project，https://gxj.quanzhou.gov.cn/zwgk/gzdt/202011/t20201124_2463941.htm
- 12个高新产业项目签约落地泉州市软件与工业设计基地：government_industry_project，https://www.qzfz.gov.cn/zwgk/xwzx/fzxw/202012/t20201211_2476018.htm

## 3. 岗位数量和类型

- 总扫描岗位记录：11
- I_job 纳入数量：8
- E_extension 数量：1
- G_public_sector 数量：1
- F_financial_candidate 数量：1
- I_tech_transfer_candidate 数量：0
- 项目证据数量：3
- 企业主体证据数量：2
- 高优先级人工复核数量：2

## 4. 系统边界修正说明

本轮继续执行 v2 边界规则：先识别 `employer_sector`，再判断 `job_function`，最后确定 `system_mapping`。高校教师/科研/实验员岗位转入 E 端延伸，政府机关和普通事业单位信息化岗位转入 G 公共部门，金控、银行、基金、担保等金融岗位转入 F 端候选。项目公告、科技计划、智能制造示范、企业名单和园区企业名录均不得伪装成岗位。

产业端企业岗位只有在具备企业主体、岗位名称、年份、城市归属和 source_url 时，才进入 I_job 候选。本轮新增可进入 I_job 候选的记录主要来自泉州兰台信息科技、泉州市搏浪信息科技、泉州三安半导体、福建省晋华集成电路等企业岗位线索。

## 5. 人工复核队列

高优先级复核集中在两类记录：一是高校教师/科研相关记录，防止误计入 I_job；二是政府项目中涉及技术转化中心、研究院、工业互联网或智能制造平台的记录，后续需要确认是否存在明确岗位。当前未发现可直接标记为 `I_tech_transfer_candidate` 的研究员/工程化岗位记录。

## 6. 对泉州 2019/2020 I_index 的潜在影响

本轮找到若干企业产业端数字化岗位候选，说明泉州 2019/2020 I 端完全为 0 的口径可能偏保守，尤其是 2019 年泉州软件园企业岗位、半导体企业 MES/软件岗位，以及 2020 年晋华集成电路软件/大数据岗位。但这些记录仍需人工复核 source_url、原始附件和年份口径后，才能用于构造 `I_index_upgraded_C/B/X`。

项目证据能够支持泉州存在智能制造、5G+工业互联网、软件园高新项目活动，但不能计入岗位数量，也不能单独推翻 I_index=0。

## 7. 是否需要重算 CCD

本轮不需要重算 CCD。当前 CCD 主结果仍基于企业存量和专利等 experimental I 端输入，岗位/技能数据尚未正式进入主模型。只有在人工复核完成并构造升级版 I_index 后，才建议另行运行升级版 CCD 对比。

## 8. 下一步建议

1. 优先人工打开并保存兰台信息、三安半导体、晋华集成电路、搏浪信息科技岗位原始页面或附件。
2. 对政府项目中的技术转化中心、研究院、智能制造平台继续查找是否有明确企业服务型岗位。
3. 暂不重跑当前 experimental CCD。
4. 人工复核通过后，构造 `I_index_upgraded_C/B/X`，再做升级版 CCD 对比。

## 9. 输出文件

- data/interim/i_system_upgrade/20260606_171849/i_system_upgrade_quanzhou_2019_2020_private_digital_official_job_candidates_20260606_171849.xlsx
- data/interim/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_private_digital_official_job_candidates.xlsx
- data/panel/i_system_upgrade/20260606_171849/i_system_upgrade_quanzhou_2019_2020_private_digital_job_city_year_panel_20260606_171849.xlsx
- data/panel/i_system_upgrade/latest_i_system_upgrade_quanzhou_2019_2020_private_digital_job_city_year_panel.xlsx
- data/interim/system_boundary_audit/20260606_171849/system_boundary_audit_job_record_review_20260606_171849.xlsx
- data/interim/system_boundary_audit/latest_system_boundary_audit_job_record_review.xlsx
- data/interim/system_boundary_audit/20260606_171849/system_boundary_corrected_mapping_template_20260606_171849.xlsx
- data/interim/system_boundary_audit/latest_system_boundary_corrected_mapping_template.xlsx
- data/audit/system_boundary_audit/20260606_171849/system_boundary_audit_report_20260606_171849.md
- data/audit/system_boundary_audit/latest_system_boundary_audit_report.md
- data/audit/system_boundary_audit/20260606_171849/system_boundary_audit_manifest_20260606_171849.json
- outputs/tables/i_system_upgrade/20260606_171849/i_system_upgrade_quanzhou_2019_2020_official_job_candidates_20260606_171849.xlsx
- outputs/tables/i_system_upgrade/20260606_171849/i_system_upgrade_quanzhou_2019_2020_job_city_year_panel_20260606_171849.xlsx
