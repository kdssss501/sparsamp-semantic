# 确定性整数概率合同

## 目的

浮点或 Decimal 概率即使只发生很小漂移，也可能使编码器和解码器重放不同区间。整数概率
合同把每步归一化候选分布映射为公开总质量 `M=2^b` 上的整数计数，使后续区间边界只依赖
候选顺序、整数计数和公开配置。它是有限精度重放机制，不是模型跨硬件确定性的充分条件。

## 输入与输出

输入：

- 有序候选概率 `p=(p_1,...,p_K)`，`p_i >= 0` 且总质量为正；
- 质量位宽 `b in [16,52]`，总质量 `M=2^b`；
- `preserve_support`，是否保证每个正概率候选至少获得一个计数。

输出：

- 整数计数 `c_i >= 0`；
- 严格守恒 `sum_i c_i=M`；
- 实现概率 `r_i=c_i/M`；
- 候选顺序不变，同余数按原始候选下标确定性打破平局。

## 算法

```text
ALGORITHM INTEGER-MASS(p, b, preserve_support)
INPUT: ordered non-negative probabilities, mass bits, support policy
OUTPUT: integer counts c with sum c = 2^b

1. Normalize p exactly after converting decimal strings to rational numbers.
2. Set M = 2^b.
3. If preserve_support:
   3.1 Give one base count to every p_i > 0.
   3.2 Set R = M - number_of_positive_candidates.
   Otherwise set every base count to zero and R = M.
4. Compute quota q_i = R * p_i and floor a_i = floor(q_i).
5. Add a_i to candidate i.
6. Let L = M - sum_i c_i.
7. Sort candidates by fractional remainder q_i-a_i descending, then index ascending.
8. Add one count to the first L candidates.
9. Return c.
```

算法有限步终止，不涉及迭代收敛。

## 误差保证

不保持支持时，Hamilton/最大余数分配满足：

```text
|r_i-p_i| < 1/M,
L1(p,r) < K/M,
TV(p,r) < K/(2M).
```

但当 `0 < p_i < 1/M` 时可能得到 `c_i=0`，此时 `KL(p||r)=infinity`。

保持支持时，令正概率候选数为 `K`。算法先分配一个计数，再对 `M-K` 做最大余数分配，
因此 `r_i >= 1/M`，不会由整数合同删除正概率支持。逐项保守界为：

```text
|r_i-p_i| < K/M,
TV(p,r) < K^2/(2M).
```

该界较宽，但在 `M=2^32` 且候选数为几十到数百时仍很小。实际 KL/TV 必须逐步计算，不能
只引用最坏界。

## 复杂度

- 概率规范化与 floor：`O(K)`；
- 最大余数排序：`O(K log K)`；
- 工作空间：`O(K)`；
- 编码和解码后续区间操作保持原复杂度。

若未来只选择前 `L` 个余数，可用选择算法降低到期望 `O(K)`，但当前候选规模下排序更简单、
更易审计。

## 重放边界

整数合同保证：给定完全相同的有序输入概率字符串和配置，输出计数逐位一致。它不保证：

- FP16、BF16、FP32 的候选集合必然相同；
- 概率漂移不会跨越 floor 或余数排序边界；
- tokenizer、模型 revision 或 top-p 支持发生变化后仍可解码；
- 固定整数质量本身具有现实不可检测性。

因此 R022 同时报告候选 Jaccard、最大概率漂移、Decimal 合同精确一致步数，以及不同
`b` 下整数合同的精确一致步数。候选 churn 时，无论整数位宽如何都不能声称重放成功。

## 配置

Decimal 默认路径保持不变：

```json
{
  "probability_quantum": "1e-15",
  "probability_mass_bits": null
}
```

整数支持保持路径：

```json
{
  "probability_quantum": null,
  "probability_mass_bits": 32,
  "preserve_probability_support": true
}
```

两种概率合同互斥，配置同时启用时直接拒绝。

## R022 经验结果

GPT-2 的 FP32 -> FP16 32-step 共享前缀审计中，Decimal `1e-15` 与整数
`b={16,20,24,28,32}` 均只有 `10/32` 精确一致，整数模式改善为零。14 步候选顺序一致，
20 步候选集合一致；18 步顺序变化，其中 12 步存在 top-p 候选 churn。该结果否定了“仅靠
16-bit 以上整数质量即可提高跨精度重放”的 V1 假设。

下一版本优先把 top-p 支持选定后的区间顺序改为稳定 token ID 顺序，再评估更粗且满足
`2^b >= K` 的质量位宽。整数质量仍保留为可选、支持保持的精确合同，但不再单独作为已验证
的跨精度改进。
