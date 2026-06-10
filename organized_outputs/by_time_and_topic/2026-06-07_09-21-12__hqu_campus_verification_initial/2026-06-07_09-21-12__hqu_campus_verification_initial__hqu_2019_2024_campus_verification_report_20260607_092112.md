# 华侨大学 2019—2024 年 AI 基础专业群校区归属核验报告

## 1. 本次运行信息
- run_id：20260607_092112
- 输入候选表：data/interim/e_system_recheck/latest_xiamen_2022_E_B_candidates.xlsx
- 输入 2022 PDF：/Users/greenbarry/Desktop/finacial system and educational system CCD/e-基本口径data/2022年福建省普通高校招生计划（普通类物理科目组）.pdf
- 输出文件：
  - data/interim/e_system_recheck/20260607_092112/hqu_2019_2024_ai_major_campus_verification_20260607_092112.xlsx
  - data/panel/e_system_recheck/20260607_092112/xiamen_2019_2024_E_B_reclassified_by_hqu_campus_20260607_092112.xlsx
  - data/panel/e_system_recheck/20260607_092112/quanzhou_2019_2024_E_B_hqu_quanzhou_candidate_20260607_092112.xlsx

## 2. 核验背景
华侨大学同时在厦门、泉州两地办学，E 端如果只按学校名称或计划册中的院校所在地处理，可能把不同校区专业错误归入同一个城市。因此，本轮按“年份—专业—招生类别”核验，已确认校区的记录才进入厦门或泉州候选；校区不明、跨校区或缺少年份计划明细的记录进入人工复核。

## 3. 数据来源
本轮优先使用华侨大学招生信息网的招生章程、专业目录、学院介绍页面，以及本地 2022 福建省招生计划册 recheck 候选表。已核验来源：

- 华侨大学2019年普通高等教育招生章程：https://zsc.hqu.edu.cn/info/1024/2732.htm
- 华侨大学2020年普通高等教育招生章程：https://zsc.hqu.edu.cn/info/1024/3069.htm
- 华侨大学2021年普通高等教育招生章程：https://zsc.hqu.edu.cn/info/1024/3431.htm
- 华侨大学2021年普高招生专业目录（境内版）：https://zsc.hqu.edu.cn/info/1024/3459.htm
- 华侨大学2023年境内本科招生信息列表：https://zsc.hqu.edu.cn/zsxx/jnbkzsxx/nzsxx2023.htm
- 华侨大学2023年普高招生专业目录（境内版）：https://zsc.hqu.edu.cn/info/1024/3679.htm
- 华侨大学2024年普通高等教育招生章程：https://zsc.hqu.edu.cn/info/1024/7422.htm
- 华侨大学2024年普高本科招生专业目录（境内版）：https://zsc.hqu.edu.cn/info/1024/7462.htm
- 华侨大学招生网学院介绍：计算机科学与技术学院：https://zsc.hqu.edu.cn/xyjs/jsjkxyjsxy.htm
- 华侨大学招生网学院介绍汇总页：https://zsc.hqu.edu.cn/xyjs.htm

## 4. 专业逐年逐条校区判定
本地实际可逐条核验的华侨大学计划记录来自 2022 年厦门 E_B 补齐候选表，共 7 条，其中 B 口径 6 条、X 扩大口径 1 条：

- 2022 人工智能：计划 8，校区 xiamen_campus，重分配 厦门，证据 C_official_major_page
- 2022 计算机科学与技术：计划 35，校区 xiamen_campus，重分配 厦门，证据 C_official_major_page
- 2022 软件工程：计划 15，校区 xiamen_campus，重分配 厦门，证据 C_official_major_page
- 2022 信息安全：计划 12，校区 xiamen_campus，重分配 厦门，证据 C_official_major_page
- 2022 物联网工程：计划 17，校区 quanzhou_campus，重分配 泉州，证据 C_official_major_page
- 2022 数据科学与大数据技术：计划 25，校区 quanzhou_campus，重分配 泉州，证据 C_official_major_page
- 2022 智能制造工程：计划 29，校区 xiamen_campus，重分配 厦门，证据 C_official_major_page

2019、2020、2021、2023 年本地未发现华侨大学计划明细，因此只记录 source_gap，不生成计划数。2024 年官方章程显示人工智能存在跨校区培养安排，本轮不将其直接归入单一城市。

## 5. 厦门 2019—2024 E_B 重分类结果
本轮对 2022 年前一版补齐值进行了校区拆分：原 `include_B_main` 中华侨大学 112 人不再全部计入厦门。其中，人工智能、计算机科学与技术、软件工程、信息安全合计 70 人可作为厦门校区确认候选；物联网工程、数据科学与大数据技术合计 42 人转为泉州校区候选。

- 2019：strict=495；with_confirmed_hqu_xiamen=495
- 2020：strict=559；with_confirmed_hqu_xiamen=559
- 2021：strict=3511；with_confirmed_hqu_xiamen=3511
- 2022：strict=634；with_confirmed_hqu_xiamen=704
- 2023：strict=3670；with_confirmed_hqu_xiamen=3670
- 2024：strict=2799；with_confirmed_hqu_xiamen=2799

因此，厦门 2022 年 E_B 补齐候选建议从原 746 调整为 704（非华侨大学公办主口径 634 + 华侨大学厦门校区确认 70），但仍需人工确认后再更新主面板。

## 6. 泉州 2019—2024 E_B 候选影响
确认属于华侨大学泉州校区的 B 口径候选目前只在 2022 年本地明细中出现，合计 42 人：

- 2019：HQU泉州校区 B 候选=0
- 2020：HQU泉州校区 B 候选=0
- 2021：HQU泉州校区 B 候选=0
- 2022：HQU泉州校区 B 候选=42
- 2023：HQU泉州校区 B 候选=0
- 2024：HQU泉州校区 B 候选=0

这部分可以作为泉州 2022 年 E_B 校区重分类候选，但不得直接覆盖原泉州 E 端面板。其它年份因为缺少华侨大学计划明细，暂不生成新增计划数。

## 7. 对当前 CCD 的影响
本轮不重算 CCD，也不覆盖 latest experimental base panel。当前 latest 面板中厦门 2022 仍为 missing_E，泉州 2022 仍沿用原 E_B 计划数。若人工确认本轮拆分结果，则厦门 2022 补齐候选值应使用 704 而不是 746；泉州 2022 可新增华侨大学泉州校区 B 候选 42。该变化可能影响厦门/泉州 2022 的 E_index 和后续 CCD，但需要先更新 E 端候选底表，再正式重跑 experimental_analysis_pipeline。

## 8. 下一步建议
1. 建议更新厦门 2022 E_B 补齐值：从 746 改为 704 的人工确认候选。
2. 建议新增泉州 2022 E_B 华侨大学候选：物联网工程 17、数据科学与大数据技术 25，合计 42。
3. 建议补齐 2019、2020、2021、2023、2024 年福建招生计划册或华侨大学分省分专业计划，再扩展所有年份 E 面板。
4. 人工确认后再重跑 experimental_analysis_pipeline 和 caliber test；现在不建议立即重跑 CCD。
