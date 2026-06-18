# 论文A数据缺口检查报告

## 1. 本次检查信息

- run_id：`20260617_193421`
- 检查对象：论文A《福建省人工智能赋能教育系统与产业系统协调发展测度、诊断与政策优化研究》
- 重点章节：第3章研究设计、第4章测度结果、第5章稳健性与边界校验、第6章功能链诊断
- 仓库目录：`/Users/greenbarry/Documents/GitHub/fj-esystem-and-isystem-CCD`
- 读取文件：
  - `manuscripts/README.md`
  - `manuscripts/论文A_测量与诊断_完整稿.md`
  - `config/e_caliber_majors.yml`
  - `config/i_caliber_firm.yml`
  - `config/i_caliber_patent.yml`
  - `config/functional_chain.yml`
  - `docs/口径冻结文档_v1.0_草案.md`
  - `docs/数据采集自动化方案_v1.0.md`
  - `docs/四环节功能链_数据可得性测试_v1.md`
  - `data/audit/e_system_wp05_audit/latest_wp05_e_system_audit_report.md`
- 本报告只做数据管道缺口审计，不修改论文正文，不重算 CCD，不覆盖旧结果。

## 2. 总体结论

当前仓库已经具备论文A的数据框架、口径配置、部分三市实验性输出、E端补齐核验和系统边界审计材料，但**尚未具备可直接填充论文A第5章、第6章的正式九市 2019—2024 E-I CCD 结果**。

当前已有的数值性 CCD 输出主要是三市实验性结果，且 WP0.5 E端审计已经明确指出当前 E 面板存在抽取不完整、标准化锚点污染、福州 2020 内部不一致等问题。因此，现有 CCD 数值结果**不能作为正式论文结果使用**，最多可作为方法管道验证或数据问题说明材料。

论文A正式可用数据的关键前置条件是：完成福建9市 2019—2024 的 E端重抽、I端企业/专利面板构建、四环节功能链面板落地，并修复 `scripts/functional_chain_ccd_pipeline.py` 的真实运行部分。

## 3. 论文A第3—6章所需输出对照检查

| 论文A所需输出 | 当前状态 | 现有证据/文件 | 是否可用于正式论文 |
|---|---:|---|---:|
| 福建9市 2019—2024 的 `E_index`、`I_index`、`C`、`T`、`D`、`CCD_level` | 缺失 | 仅有 `data/panel/experimental_analysis/latest_experimental_analysis_base_panel_2019_2024.csv`，覆盖福州、厦门、泉州三市，且无 `C`、`T` 字段 | 否 |
| C/B/X 三套口径结果 | 缺失 | `config/e_caliber_majors.yml`、`config/i_caliber_firm.yml`、`config/i_caliber_patent.yml` 已有口径配置；`scripts/caliber_nesting_check.py` 可通过校验 | 否 |
| 人均化主口径与未人均化对照 | 缺失 | `config/functional_chain.yml` 已声明 per_capita 设计，但无正式输出表 | 否 |
| 朴素 CCD vs 边界清洗后 CCD 对比 | 缺失 | 已有系统边界审计文档和岗位边界规则，但无九市 CCD 对比结果 | 否 |
| 功能链障碍度分解：供给规模、供给质量、产业承接、产业转化 | 缺失 | `config/functional_chain.yml` 与 `scripts/functional_chain_ccd_pipeline.py` 有框架；四个真实环节面板缺失 | 否 |
| 城市类型分类 | 缺失 | `functional_chain_ccd_pipeline.py` 有合成样例函数，未形成正式九市输出 | 否 |
| 演化路径分类 | 缺失 | 三市旧实验性口径检验表中有路径字段，但 E端已被 WP0.5 审计判为不可正式使用 | 否 |
| 热力图、城市时序图 | 部分存在但不适用 | 旧三市实验性图表存在；缺九市、C/B/X、人均化、边界清洗后版本 | 否 |
| run_id 版本目录和 latest 入口 | 部分具备 | 三市 experimental、caliber、E recheck、I upgrade、boundary audit 有 run_id/latest 习惯；论文A正式九市管道尚未形成 | 否 |

## 4. 已经齐备的部分

1. **论文A文本结构已经明确。**  
   `manuscripts/README.md` 与 `manuscripts/论文A_测量与诊断_完整稿.md` 已经把论文A定位为测度与诊断论文，不做论文B，不做因果识别，不把 F 端或暴露率变量纳入 CCD 主模型。

2. **C/B/X 口径配置已经有机器可读草案。**  
   E端专业口径、I端企业口径、I端专利口径均已有 `config/*.yml`。`python3 scripts/caliber_nesting_check.py` 当前可以通过嵌套性检查。

3. **功能链框架已经有配置草案。**  
   `config/functional_chain.yml` 已定义四个环节：供给规模、供给质量、产业承接、产业转化，并给出 E/I 聚合、CCD、障碍度、城市类型、路径类型的设计。

4. **系统边界审计已经形成。**  
   仓库中已有 E/I/F/G 边界规则、岗位复核表、边界审计报告和 v2 规则修正。该部分可以支持论文A第3章的方法边界说明，但不能替代正式 CCD 计算。

5. **厦门 2022 E_B 补齐和华侨大学校区核验已有阶段性材料。**  
   `data/panel/e_system_recheck/latest_E_B_three_city_2019_2024_completed_panel.xlsx` 已将厦门 2022 E_B 主值设为 704，并保留了 HQU 校区重分类痕迹。但该文件是三市 E_B 补齐材料，不是九市正式 E_index 面板。

6. **E端 WP0.5 审计已经指出不能直接使用旧 E 面板。**  
   `data/audit/e_system_wp05_audit/latest_wp05_e_system_audit_report.md` 给出明确结论：当前 E 面板存在覆盖不完整、福州 2020 内部不一致、标准化锚点污染等问题，不能进入正式分析。

## 5. 主要缺口与阻断项

1. **九市 E端供给规模面板缺失。**  
   论文A需要福建9市 2019—2024 年 E 端主面板。现有正式可追溯输出只覆盖三市，且旧 E 面板已被 WP0.5 审计判为不可用。

2. **九市 E端供给质量面板缺失。**  
   论文A第6章需要“供给质量”进入功能链障碍度分解。当前只有质量指标配置草案，尚未形成 `e_supply_quality_panel.csv`。

3. **九市 I端产业承接面板缺失。**  
   企业存量、企业注册资本或相关承接指标尚未形成论文A正式的九市 2019—2024 面板。

4. **九市 I端产业转化面板缺失。**  
   专利申请等产业转化指标尚未形成论文A正式的九市 2019—2024 面板。

5. **四环节功能链真实输入面板缺失。**  
   `scripts/functional_chain_ccd_pipeline.py --run` 当前要求以下文件，但仓库中尚未生成：
   - `data/panel/functional_chain/e_supply_scale_panel.csv`
   - `data/panel/functional_chain/e_supply_quality_panel.csv`
   - `data/panel/functional_chain/i_carrier_panel.csv`
   - `data/panel/functional_chain/i_conversion_panel.csv`

6. **功能链 CCD 管道尚未实现真实运行。**  
   `scripts/functional_chain_ccd_pipeline.py` 当前是骨架：有合成自检和核心函数，但 `run_real` 仍是 TODO。并且 `--self-test` 当前失败，原因是合成样例末年四环节全部达到理想值时障碍度分母为 0，自检仍要求障碍度和为 1。

7. **论文A正式 run_id 输出目录尚未形成。**  
   旧三市 experimental 输出有 run_id/latest，但不等于论文A正式九市输出。论文A需要单独建立 `paper_a` 或 `functional_chain` 的 run_id 归档输出与 latest 入口。

8. **口径冻结文档仍是草案。**  
   `docs/口径冻结文档_v1.0_草案.md` 明确写有待人工裁决事项，尚未 freeze。并且该文档中关于 E 端主模型使用 `t-4` 滞后的表述，与当前论文A正文中“当年招生计划作为教育系统培养承诺或体量”的主口径表述存在不一致，需要在正式跑数前统一。

9. **缺少质量闸门脚本。**  
   `docs/数据采集自动化方案_v1.0.md` 提到的 `quality_gates.py` 尚未在 `scripts/` 中发现。

## 6. 脚本可运行性判断

### 6.1 可以直接运行的脚本

| 脚本 | 当前作用 | 检查结论 |
|---|---|---|
| `python3 scripts/caliber_nesting_check.py` | 检查 E/I C/B/X 配置嵌套性 | 可直接运行；当前通过，但只校验配置，不生成论文A结果 |
| `python3 scripts/e_system_xiamen_2022_b_recheck.py` | 厦门 2022 E_B 补齐核验 | 可用于三市 E端补齐追溯，不是九市正式 CCD |
| `python3 scripts/hqu_2019_2024_campus_verification.py` | 华侨大学校区归属核验 | 可用于 E端清洗辅助，不是完整九市 CCD |
| `python3 scripts/e_system_three_city_b_completion_panel.py` | 三市 E_B 补齐版面板 | 可用于修复三市 E_B 候选，不是论文A正式面板 |

### 6.2 可以运行但不应作为论文A正式流程的脚本

| 脚本 | 原因 |
|---|---|
| `python3 scripts/experimental_analysis_pipeline.py --input ...` | 面向旧实验性 CCD Excel，主要是三市小样本，不满足论文A九市、C/B/X、功能链诊断要求 |
| `python3 scripts/experimental_caliber_regression_pipeline.py --input ...` | 是三市口径检验和探索性回归，不属于论文A正式测度结果；论文A当前不需要回归结论 |
| `python3 scripts/i_system_upgrade_quanzhou_2019_2020_official_collect.py` | 是泉州岗位/技能试点，不是九市 I端正式企业/专利面板 |
| `python3 scripts/system_boundary_audit.py`、`python3 scripts/system_boundary_audit_v2_refine.py` | 可维护边界规则，但不生成正式 CCD |

### 6.3 需要修复或补充的脚本

| 脚本/模块 | 需要修复或补充的内容 |
|---|---|
| `scripts/functional_chain_ccd_pipeline.py` | 修复 `--self-test` 的全理想点障碍度边界情况；实现真实读取四环节面板、C/B/X、人均化/未人均化、朴素/清洗后 CCD、城市类型、路径类型、图表、run_id/latest 输出 |
| `scripts/experimental_analysis_pipeline.py` | 如果继续沿用，需要从三市实验性脚本改造成九市论文A正式管道；但更建议新建或重构为 `paper_a_functional_chain_pipeline.py` |
| `scripts/quality_gates.py` | 当前未发现，需要新增，用于检查九市年份完整性、C/B/X 嵌套、零值、缺失、边界清洗、标准化锚点等 |
| E端九市招生计划抽取脚本 | 当前只有补齐/核验脚本，缺少统一 WP2 九市 2019—2024 批量抽取与学校—城市归属脚本 |
| I端企业/专利面板构建脚本 | 当前有口径配置和试点材料，缺少正式九市企业、专利面板构建脚本 |

## 7. 当前最小可运行流程

当前最小可运行流程不是“正式论文A跑数”，而是“确认正式跑数尚未满足条件”的守门流程：

```bash
cd /Users/greenbarry/Documents/GitHub/fj-esystem-and-isystem-CCD
python3 scripts/caliber_nesting_check.py
python3 scripts/functional_chain_ccd_pipeline.py --run
sed -n '1,220p' data/audit/e_system_wp05_audit/latest_wp05_e_system_audit_report.md
```

预期解释：

1. `caliber_nesting_check.py` 应通过，说明 C/B/X 配置关系暂时无阻断。
2. `functional_chain_ccd_pipeline.py --run` 会提示四个功能链输入面板缺失，说明正式九市 CCD 还不能运行。
3. WP0.5 报告会说明旧 E 面板不能进入正式分析。

因此，当前最小可运行流程只能用于项目状态核验，不能用于填充论文A第5章、第6章的正式结果。

## 8. 若要填充论文A第5章、第6章，下一步命令顺序

### 8.1 现在应先运行的核验命令

```bash
cd /Users/greenbarry/Documents/GitHub/fj-esystem-and-isystem-CCD
python3 scripts/caliber_nesting_check.py
python3 scripts/functional_chain_ccd_pipeline.py --run
```

这一步用于确认口径配置有效，并再次确认四环节输入面板缺失。

### 8.2 下一步应先补数据，而不是重跑旧 experimental pipeline

需要先形成以下四个正式面板：

```text
data/panel/functional_chain/e_supply_scale_panel.csv
data/panel/functional_chain/e_supply_quality_panel.csv
data/panel/functional_chain/i_carrier_panel.csv
data/panel/functional_chain/i_conversion_panel.csv
```

这四个面板应覆盖：

- 福建9市；
- 2019—2024；
- C/B/X 口径；
- 主口径人均化字段和未人均化对照字段；
- 边界清洗标记；
- 缺失、零值、人工复核状态。

### 8.3 修复功能链管道后，正式跑数命令应类似

```bash
cd /Users/greenbarry/Documents/GitHub/fj-esystem-and-isystem-CCD
python3 scripts/quality_gates.py --scope paper_a --input-dir data/panel/functional_chain
python3 scripts/functional_chain_ccd_pipeline.py --run
```

但注意：`scripts/quality_gates.py` 当前尚未存在，`scripts/functional_chain_ccd_pipeline.py --run` 当前尚未实现真实输出。因此这两条是目标流程，不是当前已可完成的正式流程。

### 8.4 当前不建议用于论文A正式填数的命令

```bash
python3 scripts/experimental_analysis_pipeline.py --input 当前数据与CCD实验性分析整理_20260604.xlsx
python3 scripts/experimental_caliber_regression_pipeline.py --input data/panel/experimental_analysis/latest_experimental_analysis_base_panel_2019_2024.csv
```

原因：这两条命令对应旧三市实验性分析和探索性回归，不满足论文A九市、功能链、C/B/X、人均化、边界清洗后 CCD 的正式要求。

## 9. 对论文A第5章、第6章的具体影响

### 第5章：稳健性与边界校验

当前缺少可写入正文的正式结果。需要补齐：

1. B 基本口径主结果；
2. C 保守口径对照；
3. X 扩大口径对照；
4. 人均化主口径；
5. 未人均化对照；
6. 朴素 CCD 与边界清洗后 CCD 对比；
7. 当前 E 主口径与滞后 E 稳健性对照，如果最终仍决定保留滞后检验；
8. 九市热力图和城市时序图。

### 第6章：功能链诊断

当前缺少可写入正文的正式结果。需要补齐：

1. 四环节标准化值；
2. 四环节障碍度；
3. 城市主导障碍识别；
4. 城市类型分类；
5. 演化路径分类；
6. 瓶颈迁移图或表；
7. 9市分组诊断表。

## 10. 是否可用于正式论文

当前结论：**不可以直接用于正式论文的实证结果章节**。

可以用于正式论文或附录的内容包括：

1. 第3章的方法设计逻辑；
2. C/B/X 口径设计说明；
3. E/I/F/G 系统边界原则；
4. 三市实验性结果作为“前期试验发现的问题”或数据清洗动机，但不能作为福建9市正式结论；
5. WP0.5 审计作为为什么需要重抽 E端数据的证据。

不能用于正式论文的内容包括：

1. 旧三市 `D`、`CCD_level`、路径分类；
2. 旧三市探索性回归；
3. 当前 `latest_experimental_analysis_base_panel_2019_2024.csv` 中的 E/I CCD 数值；
4. 由旧 E 面板派生出的任何城市结论、排名、路径判断。

## 11. 建议的下一步

1. 先冻结论文A主口径：确认 E端主模型使用“当年招生计划作为培养承诺/体量”，滞后口径只作为稳健性或补充说明。
2. 启动 WP2：重抽福建9市 2019—2024 E端招生计划，优先形成 `e_supply_scale_panel.csv`。
3. 同步补充 E端供给质量面板，形成 `e_supply_quality_panel.csv`。
4. 构建 I端企业存量/注册资本等产业承接面板，形成 `i_carrier_panel.csv`。
5. 构建 I端专利申请等产业转化面板，形成 `i_conversion_panel.csv`。
6. 修复并扩展 `functional_chain_ccd_pipeline.py`，让其生成论文A正式 run_id 输出和 latest 入口。
7. 生成九市 C/B/X、人均化/未人均化、朴素/边界清洗后 CCD 对比后，再填充论文A第5章和第6章。
