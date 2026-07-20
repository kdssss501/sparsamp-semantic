# R034：Top-k 合同与容量前沿

## Research Question

减小固定 top-k 能否把 FP32/FP16 的完整 bin-mass 合同提升到消息级可用范围，
同时保留足够分布熵和原模型概率质量？

## Registered Sweep

- 模型：GPT-2，FP32 reference / FP16 replay；
- prefix：每个变体自身的 32-step FP32 top-1 prefix；
- 固定：`top_p=1.0`、`q=1/2`、`bin_mass_bits=16`、token-ID order；
- 扫描：`top_k={2,4,8,16,32,64}`；
- `k=64` 复用 R033，其他 k 独立输出。

## Metrics And Gate

必须同时报告：

1. support/order exact steps；
2. bin-mass count exact steps；
3. integer-16 contract exact steps；
4. reference mean/min entropy bits；
5. reference mean/min retained source mass；
6. bin-mass 额外 KL/TV。

进入消息级 pilot 的候选必须满足：count 和 integer-16 合同至少 `30/32`，平均
熵至少 `0.5 bit/token`。在合格候选中选择最大的 k。source mass 作为质量代价
报告但不设事后门槛。`k=1` 合同平凡且容量为零，预先排除。

固定 top-k 本身产生的截断偏差不包含在 bin-mass KL/TV 中；source mass 用于显示
这部分代价，不能把 retained-distribution KL 误称为相对原模型的总 KL。

## Planned Outputs

- `outputs/R034_gpt2_fixed_k2_q2.json`
- `outputs/R034_gpt2_fixed_k4_q2.json`
- `outputs/R034_gpt2_fixed_k8_q2.json`
- `outputs/R034_gpt2_fixed_k16_q2.json`
- `outputs/R034_gpt2_fixed_k32_q2.json`
- `outputs/R033_gpt2_fixed_k64_q2.json`（复用）

## Results（2026-07-20）

为保留 R033 原输出，k=64 重新写入 `outputs/R034_gpt2_fixed_k64_q2.json`。

| k | support exact | count/int16 exact | mean entropy | min entropy | mean source mass | min source mass |
|---:|---:|---:|---:|---:|---:|---:|
| 2 | 31/32 | 30/32 | 0.45049 | 0.01071 | 0.60838 | 0.09362 |
| 4 | 27/32 | 24/32 | 0.93493 | 0.02453 | 0.66679 | 0.15041 |
| 8 | 29/32 | 23/32 | 1.44638 | 0.04250 | 0.74142 | 0.25280 |
| 16 | 23/32 | 15/32 | 1.90420 | 0.06214 | 0.81314 | 0.37702 |
| 32 | 20/32 | 9/32 | 2.35288 | 0.08770 | 0.88739 | 0.50304 |
| 64 | 26/32 | 6/32 | 2.72830 | 0.10811 | 0.94571 | 0.60785 |

没有 k 同时满足 30/32 count 合同和平均熵 0.5。k=2 距离熵门槛最近，且合同
已达标；k=4 以上虽然熵更高，但联合 bin 一致率快速下降。source mass 随 k
增加而上升，说明小 k 的可靠性来自显著截断，而不是免费改进。

## Stage Decision

R034 判定为 **PARETO-FRONTIER / NEAR-GO-k2**。下一步固定 k=2 与 q=1/2，
提高公开温度以增加二元合同分布熵；温度不改变相对 logit bins 与 top-k 排名，
理论上不会降低由 bins 决定的 count 一致步数，但会进一步降低 retained source mass，
必须继续报告该代价。
