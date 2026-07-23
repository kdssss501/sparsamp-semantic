# Stage 3' 聚焦复审检查点

## 结论

**复审决定：Major Revision（大修），但核心科学主张已经稳定。**

这不是退回原点。第一轮最关键的质疑是“SPRC 是否只是普通稀疏 delta 记录”。R051/R052 的同边界对照已经给出正面但克制的回答：在冻结的 1,500-token 数据上，SPRC 为 1,148 bytes、2.054% 修正率；去掉量化概率合同的 top-2 delta 为 1,200 bytes、3.178% 修正率，修正率增加 1.123 个百分点，prompt 配对 bootstrap 95% 区间为 0.171-2.015。它说明概率合同有小而可测的贡献，但不说明全局最优。

## 已闭合

- 匹配的 seed-only、full trace、block repair、unquantized delta 基线。
- exact replay 与经验稀疏性的概念分离。
- integer apportionment 的 `TV < 2(k-1)/M` 数学上界。
- constructor/recipient/auditor、共享状态、两次 target pass 和隐私边界。
- 从宽泛叙事收缩到 specialist ML-systems / reproducibility 定位。
- 明确排除跨硬件、原生分布保持和语义等价等未被证据支持的结论。

## 尚未闭合

- 未在第二块独立物理 GPU/软件栈上执行冻结 bundle。
- 未完成预注册的 `q/T/B/k` 完整敏感性研究。
- Methods 仍把 exact equality 写为 primary outcome，与其他章节的“修正密度为经验主指标”冲突。
- 作者、单位、CRediT、资金、利益冲突、license 和 archive DOI 尚缺。

## Pipeline 状态

- Stage 3'：已完成。
- 当前门槛：强制确认点。
- 推荐下一步：Stage 4' 聚焦二次修订。
- Stage 4.5 最终完整性核验：尚不可开始。

根据 `academic-pipeline`，复审决定属于强制检查点，必须由作者明确确认后才能进入 Stage 4'。
