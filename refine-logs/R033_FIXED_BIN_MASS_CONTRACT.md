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
