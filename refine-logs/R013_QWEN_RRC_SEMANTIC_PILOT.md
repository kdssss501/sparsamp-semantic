# R013 Qwen Verified-RRC 语义与有限预算 Pilot

日期：2026-07-17

## 配置

- 模型：本地 `models/qwen2.5-1.5b-instruct`。
- GPU：NVIDIA GeForce RTX 3060 Laptop GPU，CUDA 12.6，Torch 2.7.1，Transformers 4.57.6。
- 采样：top-p 0.95，temperature 0.8，float16，allow_eos=false，probability quantum `1e-15`。
- Prompt：3 个中文任务（可复现实验、教育风险、软件可靠性）。
- Payload：128 bit，2 个确定性 seed；每个 variant 共 6 条独立轨迹。
- Variants：SparSamp Fixed-16、Fixed-64、Verified-RRC；token budget 128/160。
- 运行命令：`scripts/run_completion_pilot.py --config configs/qwen15_rrc_semantic_pilot.json`。

## 统一预算结果

下表每个 prompt/seed 只保留首次完成的最短轨迹；160-token 行若由 128-token 成功轨迹派生，
不重复计为独立样本。

| Variant | 完成 <=128 | 完成 <=160 | 平均 tokens | 平均 bits/token | 平均 token/s | Token Ambiguity | 平均熵利用率 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Fixed-16 | 3/6 | 6/6 | 124.33 | 1.041 | 13.56 | 1/6 | 0.962 |
| Fixed-64 | 3/6 | 6/6 | 129.17 | 1.006 | 13.02 | 0/6 | 0.967 |
| Verified-RRC | 3/6 | 6/6 | 129.33 | 1.008 | 14.83 | 0/6 | 0.980 |

所有完成轨迹的 token-ID 解码均精确；不完整轨迹不进行“部分 payload 成功”的解码率冒充。

## 语义观察

Verified-RRC 生成的文本保持了中文任务的自然结构：可复现实验输出了分点解释，教育 prompt
输出了个性化学习、自动评估等连贯条目，软件可靠性 prompt 输出了代码审查、单元测试和
模块化设计等可读建议。该观察只作为定性证据，尚未做人类盲评或困惑度检验。

## 结论与限制

1. 在这 6 条 Qwen 轨迹上，Verified-RRC 没有超过 Fixed-16/64 的有限预算完成率；不能声称
   它已经“全面加速”或“全面提升容量”。
2. RRC 的熵利用率最高（0.980），生成速度也最高，但平均 token 数与 Fixed-64 基本相同。
3. RRC 与 Fixed-64 均无公开文本 Token Ambiguity；Fixed-16 出现 1/6。
4. top-p=0.95 的平均 source mass 约 0.97，因此相对完整 LM 分布仍存在截断 KL，RRC 的零 KL
   结论只能针对截断后分布 Q。
5. 下一步应优先优化候选概率精度和语义 finishing tail，而不是继续扫 block schedule；同时
   扩展到至少 20 prompts x 3 seeds 后再做显著性检验。
