# R033：Fixed Top-k Bin-Mass Contract

## Purpose

R032 表明粗 logit 量化可以提高公共 bin 一致率，却无法稳定 top-p 的不连续
支持边界。R033 固定候选数 `k`，并直接从共享整数 logit bins 构造总质量
`M=2^B` 的整数分布，从概率合同中移除 endpoint softmax 浮点尾数。

## Input / Output

输入：

- 唯一 token IDs `t_1,...,t_k`；
- 对应量化 bins `z_1,...,z_k in Z`；
- 公开 `q>0`、温度 `T>0` 和 mass bits `1<=B<=52`；
- 固定 top-k 支持，且 `2^B>=k`。

输出：

- 正整数 counts `c_1,...,c_k`；
- `sum_i c_i=2^B`；
- 合同概率 `Q_i=c_i/2^B`。

## Algorithm

令 `z_max=max_i z_i`，用固定 80-digit Decimal context 计算

\[
w_i=\exp\left(\frac{q(z_i-z_{max})}{T}\right).
\]

先给每个候选保留一个 count。对剩余质量 `R=2^B-k` 计算 quota

\[
a_i=R\frac{w_i}{\sum_jw_j}.
\]

```text
ALGORITHM: Fixed Top-k Bin-Mass Contract
INPUT: token IDs t, integer bins z, q, T, B
OUTPUT: integer counts c

1. Validate unique token IDs, equal lengths, q>0, T>0, 2^B>=k.
2. Compute Decimal weights w_i from z_i-z_max.
3. Reserve c_i=1 for every retained token.
4. Set c_i += floor(a_i).
5. Let r = 2^B - sum_i c_i.
6. Give one remaining count to the r largest fractional remainders;
   break exact ties by ascending token ID.
7. Return c.
```

## Contract Guarantee

若编码端和解码端具有相同的 `(token ID, bin)` 集合以及相同的公开参数，
则 Decimal weights、remainders、token-ID tie break 和最终 counts 完全相同。
因此整数质量合同是构造性的，不依赖两端模型 dtype。

该保证是条件保证：如果 FP32/FP16 在 top-k 边界选择了不同 token，或某个 retained
token 的 bin 不同，则本算法不保证合同。R033 的 GPU 审计必须分别报告支持一致、
bin 一致和 count 一致，不能只报告最后一项。

## Approximation And Complexity

- 每个候选至少一个 count，故支持保持。
- 相对于 Decimal softmax 的额外偏差用实测 `KL(P||Q)` 与 TV 报告。
- Decimal exp：`O(k)` 次高精度指数运算。
- largest remainder 排序：时间 `O(k log k)`，空间 `O(k)`。
- 算法有限终止，没有迭代收敛条件。

## Implementation Constraints

- provider 模式要求 `top_p=1.0`、固定 `top_k`、启用 `logit_quantum`；
- 当前禁止 adaptive temperature，避免两端控制状态引入额外分支；
- `bin_mass_bits` 进入 PRF context，防止不同合同配置共用随机流；
- 当前 Decimal 构造保证同一 Python Decimal 语义下可复现；跨语言部署应固化
  exponent lookup table 或发布 counts 生成规范测试向量。

## Registered Experiment

在 GPT-2 FP32/FP16、32-step prefix 上固定 `top_k=64`、`B=16`，扫描
`q={1/16,1/8,1/4,1/2}`。进入消息级实验的门槛：

1. top-k 支持与顺序至少 30/32 一致；
2. bin-mass counts 至少 30/32 一致；
3. integer-16 概率合同至少 30/32；
4. bin-mass 额外平均 KL `<=0.001`、TV `<=0.01`。

选择满足门槛的最小 q；若无 q 合格，则 R033 判为支持边界 NO-GO。
