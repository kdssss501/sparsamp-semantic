# R035：Binary Contract Temperature Rescue

## Hypothesis

固定 `top_k=2`、`q=1/2`、`bin_mass_bits=16` 时，提高共享温度只改变两个
候选之间的整数质量比例，不改变量化 bins 或 top-k 排名。因此 count 合同应保持
约 30/32，同时平均熵可能从 0.4505 提高到至少 0.5 bit/token。

## Registered Sweep

- GPT-2 FP32/FP16，32-step，各变体自身 FP32 top-1 prefix；
- `top_p=1.0`、`top_k=2`、`q=1/2`、`B=16`；
- `temperature={1.0,1.1,1.2,1.5}`；T=1.0 复用 R034；
- 每个温度独立输出。

GO gate：count 与 integer-16 合同至少 30/32，平均熵至少 0.5 bit/token。
选择满足条件的最小温度。必须同时报告 source mass，且不能把 retained-distribution
偏差误称为相对原模型的总偏差。

## Planned Outputs

- `outputs/R034_gpt2_fixed_k2_q2.json`（T=1.0）
- `outputs/R035_gpt2_fixed_k2_q2_t11.json`
- `outputs/R035_gpt2_fixed_k2_q2_t12.json`
- `outputs/R035_gpt2_fixed_k2_q2_t15.json`

## Results（2026-07-20）

| T | count/int16 exact | mean entropy | min entropy | mean source mass | min source mass |
|---:|---:|---:|---:|---:|---:|
| 1.0 | 30/32 | 0.45049 | 0.01071 | 0.60838 | 0.09362 |
| 1.1 | 30/32 | 0.47820 | 0.01845 | 0.55763 | 0.07041 |
| 1.2 | 30/32 | 0.50469 | 0.02887 | 0.50731 | 0.05286 |
| 1.5 | 30/32 | 0.57708 | 0.07637 | 0.36462 | 0.02307 |

所有温度均保持 30/32 count 合同，符合“温度不改变 bins/top-k 排名”的预期。
T=1.2 是第一个同时满足平均熵 `>=0.5` 的点，bin-mass 相对 retained
distribution 的额外平均 KL/TV 约为 `6.33e-9 / 8.93e-6`。

source mass 随温度升高显著下降。T=1.2 平均只保留原量化分布 50.7% 质量，
最差 5.3%；该代价来自 fixed top-2 截断，不包含在 bin-mass KL/TV 中。

## Stage Decision

R035 判定为 **STRUCTURAL-GO / MESSAGE-UNVERIFIED**。最小合格配置为：

```text
top_p=1.0, top_k=2, q=0.5, bin_mass_bits=16, temperature=1.2
```

这证明可靠性-平均熵双门槛在 32-step 精度合同上可同时满足，但尚未证明长消息
可靠、语义质量可接受或优于 SparSamp。下一阶段先运行 2-byte raw payload smoke，
确认有限窗口稀疏编码能利用该二元合同；通过后才运行 AEAD frame。
