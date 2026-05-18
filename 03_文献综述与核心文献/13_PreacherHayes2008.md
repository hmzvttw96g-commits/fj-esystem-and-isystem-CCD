# Preacher, K.J. & Hayes, A.F. (2008)

## 基本信息
- **作者**：Kristopher J. Preacher, Andrew F. Hayes
- **年份**：2008
- **发表**：*Behavior Research Methods*, 40(3), 879-891
- **核心问题**：如何更准确地检验中介效应？

## 核心论点

### 1. Bootstrap方法的优势
- 传统Sobel检验假设正态分布 → 不适用于非正态数据
- Bootstrap**不假设分布**，更稳健
- 建议：5000次重抽样

### 2. Bootstrap CI for Indirect Effect
```
Step 1: 从原始数据中随机重复抽样（放回），得到B个Bootstrap样本
Step 2: 对每个Bootstrap样本计算ab乘积
Step 3: 构建95%置信区间
→ 如果CI不包含0，中介效应显著
```

### 3. 软件实现
- SPSS: PROCESS macro
- Stata: bootstrapping
- R: lavaan/memore

## 对本研究的启发

### 方法层面（⭐⭐⭐⭐ 稳健的中介效应检验）
- ✅ **Bootstrap方法** → 论文B（金融调节效应）的中介检验应使用此方法
- ✅ 论文B的具体模型：金融发展(X) → 产学研合作(M) → AI产教耦合(Y)

### 推荐分析代码
```stata
* Stata Bootstrap中介效应
bootstrap r(ind_eff) r(dir_eff), reps(5000): ///
    sem (M <- X) (Y <- M X)
estat bootstrap, bc percentile
```

## 待讨论问题
