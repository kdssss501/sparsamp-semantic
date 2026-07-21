# 论文初稿中文作者说明

## 定位

这版初稿按 Nature Communications 风格的计算方法论文组织，而不是直接按 Nature 主刊投稿强度包装。当前最稳妥的主线是“跨精度随机生成的稀疏重放证书”，不是隐写容量、安全性或语义质量论文。

核心句：在已知目标精度环境、固定模型与 tokenizer 的条件下，公开离散概率合同配合稀疏 token 修正记录，可以恢复完全一致的随机生成轨迹；Qwen 主实验为 60/60，平均修正率为 2.16%。

## 结构选择

- 摘要采用“问题 -> 缺口 -> 方法 -> 定量结果 -> 边界”结构。
- 引言先说明随机推理可复现性，再引入有限精度概率边界，不从隐写应用直接开场。
- Results 将“证书保证精确恢复”与“修正记录是否稀疏”分开，避免循环论证。
- top-2/top-4 被写成 Pareto 结果，不写成 top-4 全面退化或 top-2 全面最优。
- Discussion 明确说明证书依赖已知目标环境，因此不是任意硬件上的通用确定性方案。
- Methods 单独区分 logit 量化、support truncation 和整数质量分配，禁止把 `-log Z` 写成完整总 KL。

## 当前可以写进摘要的结果

- Qwen FP16 到 BF16：60/60 修正后精确重放，未修正 10/60。
- 平均修正率 2.16%，prompt-cluster bootstrap 95% CI 为 1.80%-2.53%。
- 旧 fixed-width payload-only 比例为 2.88%，95% CI 为 2.40%-3.36%；它不包含 header，不能写成完整证书开销。
- R049 seed-0 审计：versioned binary payload 为 6.65%，引用共享 bundle 的 compact package 为 24.76%（6.123 bits/token），自包含 JSON audit package 为 63.89%。
- 58/60 达到公开句末结构条件。
- BF16 到 FP16 的 20-prompt 消融为 20/20。
- 按每条轨迹等权统计，top-4 相对 top-2 的 retained mass 增加 0.1100，truncation KL component 降低 0.1840 nats/token，但没有降低修正率。

## AUTHOR_INPUT_NEEDED

1. 作者姓名、单位、通讯作者和邮箱。
2. CRediT 作者贡献与利益冲突声明。
3. 目标期刊：Nature Communications、Scientific Reports 或计算机领域会议/期刊。
4. 数据与代码的长期归档地址；投稿前建议创建 Zenodo DOI。
5. 是否把早期 GPT-2/R022-R023 负面结果放入 Supplementary Information。
6. 是否能获得第二台 GPU 或不同 CUDA 栈完成独立复验。
7. 是否开展盲法文本评价；若招募人类评价者，需要在实验前确认伦理、知情同意和数据管理要求。

## 投稿前 P0/P1 风险

- **P0：跨硬件主张尚无证据。** 当前只允许写“tested software and hardware stack”。
- **P0：不能声称零 KL 或完整分布保持。** top-2 的截断项约为 0.353 nats/token，整数 apportionment 误差未单独测量。
- **P1：top-4 只有一个 seed。** 当前足够支持设计消融，不足以支持一般语义质量结论。
- **P1：没有盲法语义评价。** 句末标点只是一项结构指标。
- **P1：模型范围只有 Qwen2.5-1.5B，GPT-2 仅为小型先导实验。**
- **P1：精确恢复本身由 manifest 构造保证。** 论文必须把主要经验贡献放在稀疏率、分布代价和目标环境边界上。
- **P1：多篇 2026 引用仍是 arXiv 预印本。** 投稿前需要再次核验出版状态和版本。
- **P1：R047 仍不是独立硬件证据。** 当前 20/20 是同一机器上的 reference-only bundle 与 fresh target replay smoke。
- **P1：R048 只有材料，没有真人结果。** 原生 top-16、top-2、top-4 的 20 组匿名材料已生成，但伦理状态仍为 `ETHICS_PENDING`，不能招募或报告评分。

## 下一版优先顺序

1. 在第二台 GPU/CUDA 栈上运行 R047 reference-only bundle，保存完整 target JSON。
2. 完成 R048 伦理/导师确认、功效分析和预注册后，再开始 native/top-2/top-4 盲评。
3. 为主实验 artifacts 建立不可变 Zenodo 归档并补 DOI。
4. 根据目标期刊压缩摘要、主文长度和 Methods 位置。
5. Figure 1-4、PDF/300 DPI PNG 与 source CSV 已完成；投稿排版时只需引用正式文件。
