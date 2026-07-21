# 论文作者说明

## 当前定位

正式稿按 Nature Communications 风格的计算方法论文组织。核心主线是“跨数值精度随机生成的稀疏重放证书”，而不是宣称获得了更高隐写容量、零分布偏差或不可检测性。

当前最稳妥的一句话结论是：在模型、tokenizer、prompt、公开随机配置和目标数值环境固定时，公开离散概率合同配合目标环境专用的稀疏 token 修正记录，可以恢复完全一致的随机生成轨迹。Qwen 主实验实现 60/60 精确重放，平均修正率为 2.16%。

## 已完成证据

- Qwen FP16 到 BF16：修正后 60/60 精确重放，未修正 10/60。
- 平均修正率 2.16%，prompt-cluster bootstrap 95% CI 为 1.80%-2.53%。
- 58/60 输出达到公开句末结构条件。该指标不是语义质量或事实正确性评价。
- BF16 到 FP16 的 20-prompt 消融为 20/20 精确重放。
- top-4 相对 top-2 提高 retained source mass 并降低 truncation component，但没有降低修正率，且 shared-contract exactness 更低。
- R049 seed-0 审计区分了三种开销边界：payload-only 6.65%，引用共享 bundle 的 compact package 24.76%，自包含 JSON audit package 63.89%。三者不是同一估计量。
- Figure 1-4 的 PDF、300-dpi PNG、source-data CSV、生成脚本和哈希 trace 已生成并通过视觉检查。
- 正式稿 claim 审计为 22/22 通过，状态为 `PASS_WITH_AUTHOR_INPUT`。

## 官方 SparSamp 复现状态

- R001 Basic compatibility reproduction 已完成：105 tokens、576 bits、5.486 bits/token、精确解码。
- R002 正在运行论文 Tables 2-4 对应的 12 个唯一配置，共 100 个 IMDB contexts 和 1,200 trials。
- 当前矩阵使用未修改的 Zenodo 15025436 算法源码、PyTorch 2.7.1+cu126 与 Transformers 4.41.2。
- 这属于 compatibility reproduction，不是严格 Torch 2.2.2 环境复现。Transformers 4.57.6 已记录旧 cache API 不兼容失败，严格 Torch 2.2.2 CUDA wheel 下载因上游 TLS/连接中断未完成。
- R002 逐 trial 原子保存，最终结果将进入 Supplementary Information；速度只作硬件相关描述，容量与解码才是主要验收门禁。

## 禁止写成的结论

- 不得写“跨任意硬件通用确定性”。当前只有一台 RTX 3060 Laptop GPU。
- 不得写“零 KL”“完整分布保持”或“等价于原始模型分布”。top-k 截断和整数质量分配均有明确代价。
- 不得写“语义等价于原生生成”。R048 只有盲评材料，没有真人评分。
- 不得写“安全”或“不可检测”。当前论文研究的是随机轨迹重放，不是完整隐写安全证明。
- 不得把 target-specific manifest 的构造性精确恢复包装成纯经验发现。真正的经验贡献是修正的稀疏性、开销和边界。
- 不得把 R047 写成独立硬件复现。它是同一机器上的 reference-only bundle 与 fresh target replay smoke test。

## 作者必须提供

1. 作者姓名、单位、通讯作者和邮箱。
2. CRediT 作者贡献。
3. 资金来源；若无专项资金，应明确写“无专项资助”。
4. 利益冲突声明。
5. 最终目标期刊或会议。
6. 公开代码和数据的不可变归档地址及 DOI。
7. 是否能够获得第二台 GPU 或不同 CUDA 栈完成独立复现。
8. 是否计划进行真人盲评；如进行，必须先确认伦理、知情同意和数据管理要求。

## 投稿前 P0/P1 风险

- **P0：作者元数据与归档 DOI 缺失。** 这些内容不能由模型代填。
- **P0：Stage 2.5 与最终完整性审查尚未完成。** 正式稿必须经过引用、统计、图表和 AI research failure-mode 门禁。
- **P1：跨硬件主张无证据。** 只能写“tested software and hardware stack”。
- **P1：没有真人语义评价。** 句末标点只能作为结构指标。
- **P1：模型范围有限。** Qwen2.5-1.5B 是主模型，GPT-2 用于先导与官方 artifact 兼容复现。
- **P1：多篇 2026 引用仍是 arXiv 预印本。** 投稿前需要重新核验版本与出版状态。

## 推荐提交顺序

1. 完成 R002，生成官方复现分析、附录表格与 Supplementary Figure。
2. 将 R002 的有界结论写入 Methods、Results 和 Supplementary Information。
3. 完成 Stage 2.5 完整性审查与 7 类 AI research failure-mode checklist。
4. 进行模拟同行评审并按问题严重度修订。
5. 作者补齐身份、资金、贡献、利益冲突和归档 DOI。
6. 通过最终完整性门禁后再生成 LaTeX、DOCX 和 PDF 投稿包。
