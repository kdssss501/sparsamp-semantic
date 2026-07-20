# R033：固定支持的整数 Bin-Mass 合同

## Research Question

固定 top-k 并从整数 logit bins 直接生成 `2^16` 总质量，能否在偏差可控的条件下
把 GPT-2 FP32/FP16 合同从 R032 的最多 13/32 提升到至少 30/32？

## Components

- `allocate_logit_bin_mass`：Decimal exp + support reservation + largest remainder；
- `HuggingFaceConfig.bin_mass_bits`：仅允许 fixed top-k 离散模式；
- snapshot metadata：counts、额外 KL/TV；
- precision audit v6：分开报告 support/bin/count/probability contract。

## Planned Outputs

- `outputs/R033_gpt2_fixed_k64_q16.json`
- `outputs/R033_gpt2_fixed_k64_q8.json`
- `outputs/R033_gpt2_fixed_k64_q4.json`
- `outputs/R033_gpt2_fixed_k64_q2.json`

每个 q 独立写文件；已完成 q 不会因后续运行失败而丢失。结果门槛和算法边界见
`docs/fixed_bin_mass_contract_r033.md`。

## GPT-2 FP32/FP16 Results（2026-07-20）

固定 `top_k=64`、`top_p=1.0`、`B=16`：

| q | support/order exact | bin exact | count exact | integer-16 exact | common bin agreement | bin-mass KL | bin-mass TV |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1/16 | 25/32 | 0/32 | 0/32 | 0/32 | 0.70634 | 0.0000693 | 0.000723 |
| 1/8 | 25/32 | 0/32 | 1/32 | 1/32 | 0.79628 | 0.0000700 | 0.000722 |
| 1/4 | 23/32 | 4/32 | 4/32 | 4/32 | 0.89500 | 0.0000720 | 0.000727 |
| 1/2 | 26/32 | 6/32 | 6/32 | 6/32 | 0.96314 | 0.0000255 | 0.000695 |

`count exact` 可能比 retained `bin exact` 多一行，因为不同 bin 组合在有限质量下可
偶然映射为相同 counts；这不是一般合同保证。构造性保证仍然只使用“相同支持与
bins 推出相同 counts”的单向命题。

## Stage Decision

R033 判定为 **PARTIAL-GO-COMPONENT / NO-GO-k64**：

- 正结果：固定 bin-mass 的额外 KL/TV 很小，且消除了同 bins 条件下的浮点概率漂移；
- 负结果：64 个 retained bins 的联合一致率太低，最佳完整 count 合同仅 6/32；
- 因此不进入 k=64 的消息级 AEAD 实验。

下一步 R034 扫描更小 `k`，同时报告 count 合同与分布熵，寻找可靠性和容量之间的
Pareto 前沿。`k=1` 虽然合同平凡成立但容量为零，不作为候选。
