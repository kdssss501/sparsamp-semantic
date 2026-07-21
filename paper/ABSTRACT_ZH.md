# 中文摘要

随机语言生成在不同数值精度之间难以复现，因为一个 token 的变化会沿自回归轨迹持续传播。本文提出稀疏精度重放证书（sparse precision replay certificates, SPRCs）：一种建立在公开整数 next-token 合同上的目标环境专用修正记录。完整证书的精确重放属于协议完整性条件；需要通过实验回答的问题是修正出现的频率，以及在明确传输边界下产生的字节和计算成本。在 Qwen2.5-1.5B-Instruct 的 20 个中英文 prompts 和 3 个公开 seeds 上，未修正的 FP16 到 BF16 重放恢复了 10/60 条轨迹，完整证书恢复了 60/60 条轨迹。平均修正率为 2.16%，prompt-cluster bootstrap 95% 置信区间为 1.80%-2.53%；反向 BF16 到 FP16 实验也恢复了 20/20 条轨迹。在冻结的 20-prompt、seed-0 bundle 上，compact referenced SPRC 为 1,148 bytes，占对应 4,636-byte full trace 的 24.76%，并小于固定 block-repair 基线。保持同一 top-2 support 和 HMAC 随机数但移除 logit-bin 与 integer-mass 合同后，修正率增加了 1.123 个百分点，配对 prompt bootstrap 95% 区间为 0.171-2.015。理论与可执行审计进一步表明，在 top-2、16-bit 整数质量合同下，integer apportionment 的逐步 total variation 严格小于 3.052 x 10^-5。现有证据支持在一个已知模型和 GPU 软件栈内进行紧凑的目标专用重放，但不支持目标无关确定性、原生分布保持、语义等价或跨硬件通用性。

**关键词：** 随机推理；数值精度；精确重放；语言模型；可复现性；概率合同；研究软件审计
