#!/bin/bash
set -e

# ============================================================
# mac所有讨论内容整合：追加讨论总结并同步到远程 GitHub
# 仓库：/Users/greenbarry/Documents/GitHub/fj-esystem-and-isystem-CCD
# 用法：
#   chmod +x update_mac_discussion_summary.sh
#   ./update_mac_discussion_summary.sh
# ============================================================

REPO_PATH="/Users/greenbarry/Documents/GitHub/fj-esystem-and-isystem-CCD"
FILE_NAME="mac所有讨论内容整合.md"
BRANCH="main"

if [ ! -d "$REPO_PATH" ]; then
  echo "错误：仓库路径不存在：$REPO_PATH"
  exit 1
fi

cd "$REPO_PATH"

if [ ! -d ".git" ]; then
  echo "错误：当前目录不是 Git 仓库：$REPO_PATH"
  exit 1
fi

echo "当前仓库：$(pwd)"
echo "当前分支：$(git branch --show-current)"
echo "远程地址："
git remote -v

cat >> "$FILE_NAME" <<'EOF'

---

# mac所有讨论内容整合

## 更新时间

本节由脚本追加生成，用于归档本阶段关于 E-I CCD 论文数据口径、E 端补齐、I 端升级、系统边界、GitHub 本地远程联动等讨论结论。

## 一、当前研究主线

当前论文研究对象是福建省教育系统 E 端与产业系统 I 端的耦合协调关系，核心方法是构造 E_index、I_index，并计算 E-I CCD。

当前小样本实验范围为：

- 城市：福州、厦门、泉州；
- 年份：2019—2024；
- 样本量：3 个城市 × 6 年 = 18 个城市—年份样本；
- 当前阶段：实验性 CCD 与口径检验，不作为最终因果结论。

## 二、E 端 B 基本口径最终处理结论

### 1. E 端 B 基本口径含义

E 端 B 基本口径用于衡量城市高校系统对 AI 基础专业群人才的培养供给能力。

B 基本口径主要包括：

- 人工智能；
- 计算机科学与技术；
- 软件工程；
- 网络工程；
- 物联网工程；
- 数据科学与大数据技术；
- 智能科学与技术；
- 网络空间安全；
- 信息安全；
- 计算机类中明确包含上述方向的专业；
- 电子信息类中明确包含计算机、软件、数据、网络安全、人工智能方向的专业。

### 2. 厦门 2022 E 端缺失已补齐

之前 experimental base panel 中存在：

- 厦门 2022：E_B 缺失；
- 厦门 2022：E_index 缺失；
- 厦门 2022：D 缺失。

经过 2022 年福建省普通高校招生计划册普通类物理科目组 PDF 抽取与校区重分类，厦门 2022 E_B 补齐值确定为：

```text
corrected_E_B = 704
```

该值构成：

```text
非华侨大学公办主口径 634 + 华侨大学厦门校区确认 B 口径 70 = 704
```

### 3. 泉州 2022 E 端校区重分类修正

华侨大学存在厦门校区和泉州校区，不能简单整体归入厦门或泉州。经校区核验后：

```text
泉州 2022 corrected_E_B = 1324 + 42 = 1366
```

其中 42 为华侨大学泉州校区确认 B 候选计划数。

### 4. 华侨大学校区归属原则

华侨大学专业校区归属采用以下原则：

1. 逐年、逐专业、逐招生类别核验；
2. 官方招生计划、招生章程、招生网、专业介绍页面优先；
3. 不得因为华侨大学有厦门校区就全部归入厦门；
4. 不得因为华侨大学有泉州校区就全部归入泉州；
5. 3+1 或跨校区培养按“最后一年所在地”划分；
6. 校区不明、source_gap、无计划数记录不进入主值；
7. 本地无年度计划数时，只确认校区归属，不新增计划数量。

### 5. E 端三市小样本是否完整

根据补齐版 E 面板 run_id = 20260607_094824：

- 福州 2019—2024：6/6 年 corrected_E_B 非缺失；
- 厦门 2019—2024：6/6 年 corrected_E_B 非缺失；
- 泉州 2019—2024：6/6 年 corrected_E_B 非缺失。

结论：

```text
E 端三市 2019—2024 B 基本口径在补齐版面板中已经完整。
```

但需要注意：

```text
补齐版 E 面板已经完整，不等于 CCD 已经更新完成。
```

下一步应使用 corrected_E_B 重算 E_index、D 和 CCD。

## 三、I 端升级版指标设计原则

### 1. 主模型必须坚持固定口径

I 端升级版指标不能按城市产业结构动态调权。正确原则是：

```text
城市结构影响数据采集路径，不影响主模型权重；
证据类型影响变量分类，不影响城市专属调权；
C/B/X 口径统一适用于所有城市；
主 CCD 结论基于固定口径，城市差异用于解释和稳健性分析。
```

### 2. 不能使用城市动态权重

错误做法：

```text
泉州民企制造业多，所以提高 I_project/I_firm 权重；
福州、厦门科技企业多，所以提高 I_job 权重。
```

这种做法会造成：

1. 城市之间 I_index 不可比；
2. E 端统一、I 端动态，破坏 E-I 对应关系；
3. 可能人为抹平教育—产业错配；
4. 容易被审稿人质疑为事后调参或动态拟合。

### 3. 正确处理城市差异

城市差异应进入：

1. 数据采集策略；
2. 结果解释；
3. 稳健性检验；
4. 异质性讨论。

城市差异不应进入：

1. 主模型城市专属权重；
2. 单独为某城市调整指标公式；
3. 为了让结果更协调而动态修正 I_index。

## 四、I 端 C/B/X 固定口径

推荐的 I 端三套固定口径如下：

| 口径 | 名称 | I 端纳入指标 | 用途 |
|---|---|---|---|
| C | 保守口径 | 企业存量 + 专利申请 + 狭义 AI 岗位 | 稳健性检验 |
| B | 基本口径 | 企业存量 + 专利申请 + 狭义 AI 岗位 + 数字技术岗位 | 主模型候选 |
| X | 扩大口径 | 企业存量 + 专利申请 + 狭义 AI 岗位 + 数字技术岗位 + 智能制造/工业互联网岗位 | 稳健性检验 |

以上 C/B/X 必须对所有城市统一适用。

## 五、E/I 系统边界规则

### 1. 核心边界

E-I CCD 的核心是教育系统与产业系统之间的协调，而不是所有数字岗位的混合匹配。

因此：

```text
高校岗位 → E 端扩展；
企业产业岗位 → I 端主模型；
金融机构岗位 → F 端候选；
政府事业单位岗位 → G 公共部门数字化需求；
项目公告 → I_project_evidence_only，不计入岗位；
企业名单 → I_firm_evidence，不计入岗位。
```

### 2. 高校岗位

以下岗位不得进入 I_job：

- 高校教师岗；
- 高校科研岗；
- 高校实验员岗；
- 高校事业编岗位；
- 高校内部学术科研岗位。

这些岗位可标记为：

```text
E_education_extension
E_research_extension
```

### 3. 政府和事业单位岗位

普通政府机关、事业单位、公共部门的信息化岗位不得进入 I_job，应标记为：

```text
G_public_sector_digital_demand
```

### 4. 金融机构岗位

金控集团、银行、基金、担保、融资平台等信息技术岗不得进入当前 E-I 主模型，应标记为：

```text
F_financial_candidate
```

该类岗位未来可用于毕业论文中 E-I-F 三系统扩展。

### 5. 研究员岗位不能一刀切

“研究员”“科研岗”“技术研究院”“新型研发机构”等不能简单按事业单位性质一律排除，也不能一律纳入 I 端。

应采用三步判定法：

```text
employer_sector → job_function → system_mapping
```

如果明确服务企业研发、成果转化、工程化、产业化应用或企业技术服务，可以标记为：

```text
I_tech_transfer_candidate
```

但仍需人工复核后决定是否进入 I 端。

如果只是高校或事业单位内部学术科研，则标记为：

```text
E_research_extension
```

## 六、泉州 I 端采集策略更新

泉州民营制造业较多，不能只通过官方/高校岗位公告直接搜索 AI 岗位。

应采用：

```text
官方企业名单 / 项目名单
        ↓
识别民营制造业数字化主体
        ↓
反查岗位、技能、企业官网、招聘会附件、专利、项目
        ↓
分层记录岗位证据、项目证据、企业主体证据
```

重点关键词：

- 智能制造；
- 工业互联网；
- 自动化；
- MES；
- ERP；
- PLC；
- 机器视觉；
- 工业软件；
- 数字化车间；
- 智能工厂；
- 两化融合；
- 5G+工业互联网。

### 泉州 2019/2020 当前判断

已有初步证据显示泉州 2019/2020 产业端数字化岗位不应简单视为“完全没有线索”，但仍需人工复核原始 URL/附件后，才能构造正式 I_index_upgraded_C/B/X。

当前不建议立即重跑 CCD；应先完成 I 端岗位与证据人工复核。

## 七、I 端证据分类

| 证据类型 | 是否计入岗位数量 | 处理方式 |
|---|---|---|
| 企业明确招聘岗位 | 是 | 可进入 I_job |
| 高校就业网中的企业招聘岗位 | 是，需复核 | 可进入 I_job 候选 |
| 产业技术研究院技术转化岗位 | pending | I_tech_transfer_candidate |
| 政府项目公告 | 否 | I_project_evidence_only |
| 高新/专精特新/企业名单 | 否 | I_firm_evidence |
| 高校教师/科研/实验员 | 否 | E_extension |
| 政府/事业单位信息化岗 | 否 | G_public_sector |
| 金融机构 IT 岗 | 否 | F_candidate |
| 商业平台线索 | 否，默认 pending | supplement_candidate |

## 八、关于 Boss 直聘等商业平台

参考杨颖/方颖等基于招聘大数据衡量企业 AI 投入的思路，商业招聘平台可以作为补充数据来源，但在当前小样本实验中不能直接作为主数据来源。

建议规则：

1. 官方、公共就业、高校就业网、企业官网优先；
2. Boss 直聘等商业平台只作为 supplement_candidate；
3. 不直接进入 I_job 主模型；
4. 若有历史快照、原始发布时间、企业主体、岗位职责清楚，可进入人工复核队列；
5. 可用于稳健性分析，而不是主模型直接替代。

## 九、当前 CCD 与下一步

### 1. 当前 CCD 主结果是否需立即推翻

不需要。之前 CCD 主结果大概率没有直接使用高校/金融/政府岗位，主要基于企业存量和专利申请，因此系统边界污染没有直接进入主 CCD。

### 2. 需要更新的原因

E 端 corrected_E_B 已补齐，厦门 2022 和泉州 2022 主值已变化：

```text
厦门 2022 corrected_E_B = 704
泉州 2022 corrected_E_B = 1366
```

因此 E_index、D 和 CCD 需要重新计算。

### 3. 推荐下一步

先使用补齐版 E 面板重新跑：

```text
experimental_analysis_pipeline
```

然后重跑：

```text
experimental_caliber_regression_pipeline
```

但应保持：

1. 不覆盖 legacy；
2. 不删除旧结果；
3. 新 run_id 管理；
4. 生成新旧 CCD 对比表；
5. 报告中明确说明 E 端补齐对路径判断的影响。

## 十、GitHub 本地远程联动

当前目标是让本地仓库与远程 GitHub 仓库保持互动关联：

```text
本地修改 / Codex 生成文件
↓
git add / commit / push
↓
远程 GitHub 同步更新

远程 GitHub 有更新
↓
git pull
↓
本地同步更新
```

本地仓库路径：

```text
/Users/greenbarry/Documents/GitHub/fj-esystem-and-isystem-CCD
```

远程仓库目标：

```text
git@github.com:hmzvttw96g-commits/fj-esystem-and-isystem-CCD.git
```

推荐后续操作：

```bash
git status
git add .
git commit -m "Update indicator caliber discussion summary"
git pull origin main --rebase
git push origin main
```

## 十一、当前结论

截至本次整理，最重要的结论是：

1. E 端三市 2019—2024 B 基本口径已经在补齐版面板中完整；
2. 厦门 2022 corrected_E_B = 704 可以进入主值；
3. 泉州 2022 corrected_E_B = 1366 可以进入主值；
4. 华侨大学校区归属已按“逐年逐专业逐招生类别”原则处理；
5. I 端升级不能采用城市动态权重；
6. I 端岗位必须先做 E/I/F/G 系统边界判定；
7. 高校教师/科研岗不能进入 I_job；
8. 研究员岗位要按功能归属复核，不能一刀切；
9. 当前下一步应基于 corrected_E_B 重跑 experimental CCD；
10. I 端升级版岗位/技能指标仍需人工复核后才能正式进入 I_index_upgraded_C/B/X。

EOF

echo "已追加讨论总结到：$FILE_NAME"

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "错误：当前仓库没有 origin 远程地址。请先配置 git remote。"
  exit 1
fi

CURRENT_BRANCH="$(git branch --show-current)"
if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
  echo "当前分支为 $CURRENT_BRANCH，尝试切换到 $BRANCH..."
  git checkout "$BRANCH"
fi

echo "拉取远程最新内容..."
git pull origin "$BRANCH" --rebase

echo "添加文件..."
git add "$FILE_NAME"

if git diff --cached --quiet; then
  echo "没有需要提交的新内容。"
  exit 0
fi

COMMIT_MSG="Update mac discussion summary on indicator calibers"
echo "提交：$COMMIT_MSG"
git commit -m "$COMMIT_MSG"

echo "推送到远程 origin/$BRANCH..."
git push origin "$BRANCH"

echo "完成：本地文件已更新，并已推送到远程 GitHub。"
echo "最近提交："
git log -1 --oneline
