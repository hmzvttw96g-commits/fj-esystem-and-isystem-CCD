# 教育系统 E 指标数据采集规范

生成日期：2026-05-17

## 一、任务目标

围绕论文中的 AI 教育供给系统，分别采集三套口径数据：

- E1 保守口径：只统计明确以“人工智能”命名的教育供给。
- E2 基本口径：统计 AI 核心专业群及直接支撑 AI 人才培养的教育供给。
- E3 扩大口径：进一步纳入 AI 支撑专业、AI+X 课程、竞赛基地、高校 AI 论文/专利等拓展指标。

## 二、硬性约束

1. 数据来源必须真实可核验，优先使用教育部、省教育厅、高校官网、研招网、国务院学位委员会等官方来源。
2. 不得虚构数据、不得用没有来源的估计数替代正式数据。
3. 对无法自动采集的数据，应标注为“需人工核验”或“需数据库导出”，不能编造。
4. 每条数据必须保留来源 URL、来源标题、访问日期、采集方法和口径判断。
5. 教育系统 E 不纳入融资金额、贷款、基金、创投等金融变量；这些指标留给金融系统 F。

## 三、统一字段

所有 agent 最终至少输出以下文件：

```text
collected_data.csv
source_register.csv
collection_notes.md
```

`collected_data.csv` 字段：

```text
system,indicator_code,indicator_name,scope_level,province,city,school,year,value,unit,source_id,collection_method,confidence,needs_manual_review,notes
```

`source_register.csv` 字段：

```text
source_id,source_title,source_url,publisher,access_date,source_type,reliability_level,raw_file_path,notes
```

## 四、可靠性分级

- A：教育部、国务院学位委员会、省教育厅、官方统计年鉴、高校官网正式页面或正式 PDF。
- B：高校二级学院官网、官方新闻稿、官方招生简章、政府转载页面。
- C：第三方数据库、媒体报道、百科或非官方汇总，仅能作为线索，不能直接作为最终数据。

## 五、建议输出判断

每个 agent 在 `collection_notes.md` 中必须回答：

1. 本口径最可靠的数据源是什么？
2. 哪些指标可以自动采集？
3. 哪些指标必须人工核验或数据库导出？
4. 当前收集结果能否支撑论文主模型？
5. 若不能，建议用哪个替代指标？
