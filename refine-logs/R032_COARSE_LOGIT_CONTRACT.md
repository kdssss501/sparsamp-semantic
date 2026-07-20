# R032：粗粒度 logit 合同消融

## Research Question

在可量化的分布偏差预算内，增大公开 logit quantum 是否能把 GPT-2
FP32/FP16 的 next-token 分布恢复到足以支持消息级 SparSamp 的一致性？

## Ablation

固定模型、prompt、32-step FP32 top-1 prefix、`top_p=0.95`、token-ID 候选顺序；
仅改变 `q={1/16,1/8,1/4,1/2}`。`q=1/16` 复用 R027 输出，其余 q 独立输出，
任何一次中断不会覆盖已完成 q 的结果。

## Result Gate

采用 `docs/coarse_logit_contract_r032.md` 预注册门槛。只有最小合格 q 才进入
6 条 AEAD 消息 pilot；否则停止，不用消息级失败重复证明合同不足。

## Outputs

- `outputs/R027_gpt2_quantized_top_p_q16.json`（复用基线）
- `outputs/R032_gpt2_quantized_top_p_q8.json`
- `outputs/R032_gpt2_quantized_top_p_q4.json`
- `outputs/R032_gpt2_quantized_top_p_q2.json`

## Results（2026-07-20）

| q | Decimal exact | integer-16 exact | support/order exact | bin sequence exact | common bin agreement | mean KL | mean TV |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1/16 | 10/32 | 12/32 | 22/32 | 12/32 | 0.87072 | 0.0000601 | 0.003015 |
| 1/8 | 10/32 | 12/32 | 15/32 | 12/32 | 0.90079 | 0.0002384 | 0.006164 |
| 1/4 | 10/32 | 11/32 | 16/32 | 11/32 | 0.94775 | 0.0009978 | 0.012630 |
| 1/2 | 7/32 | 13/32 | 19/32 | 13/32 | 0.97046 | 0.0045813 | 0.029026 |

各 q 使用本变体自己的 FP32 top-1 prefix，因此表格是各变体内部的精度合同审计，
不能把行间差异解释为严格配对因果效应。即便按对 `q=1/2` 最有利的指标，
integer-16 合同也只有 13/32，支持一致只有 19/32，远低于预注册的 30/32。

最大内部 CDF 漂移分别为：`q=1/8: 0.02085`、`q=1/4: 0.01596`、
`q=1/2: 0.02141`。粗量化没有单调缩小 CDF 漂移；`q=1/2` 的平均 KL/TV
已经接近偏差门槛，同时 Decimal 合同反而下降。

## Stage Decision

R032 判定为 **COARSE-QUANTIZATION NO-GO**。粗化 q 能提高公共 token 的 bin
一致率，却不能稳定 top-p 支持和最终概率合同，因此按照预注册 gate 不运行长
AEAD pilot。下一步应消除 top-p 的不连续支持依赖，并把候选支持与概率质量都
定义为真正共享的离散对象，例如固定 top-k + 固定点 softmax/整数质量合同；
不能继续无界增大 q。
