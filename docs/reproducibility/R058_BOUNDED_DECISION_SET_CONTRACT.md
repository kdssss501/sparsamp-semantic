# R058 有界决策集合研究合同

## 目的

R057 的最近挑战者反事实只替换候选、不允许整数质量同时漂移，导致在 rank-0 参考选择和同支持质量迁移处漏判。本研究把有限精度扰动视为量化 logit bin 的有限盒集合，直接检验公开采样决策在该集合内是否不变。

## 输入与输出

输入为一个参考端 step 的按 rank 降序 top-16 token ID (v_1,ldots,v_m)、整数 bins (b_1,ldots,b_m)、参考 token (y)、公开 `(prompt, seed, step)` 上下文、固定概率合同 `(q=0.5, T=1.2, B=16, k=2)`，以及整数 bin 扰动半径 (Delta)。每个可观测 token 的可能 bin 属于 `[b_i-Delta,b_i+Delta]`；top-16 之外 token 的上界设为 (b_m+Delta)。

输出是一个 `BoundedDecisionWitness`：可行 top-2 对数量、可行整数合同数量、可能公开 token 集、是否存在未知 tail 候选，以及 `decision_invariant`。若存在任何非参考 token 的可行决策或未知 tail 可能进入 top-2，则该 step 必须写入参考 token。

## 算法

```text
ALGORITHM BoundedDecisionSet
INPUT reference envelope (v, b), reference token y, public context, Δ
OUTPUT possible decisions D and invariant flag

1. For each envelope token i, form L_i = b_i - Δ and U_i = b_i + Δ.
2. For every pair (i, j), test feasibility:
   min(U_i, U_j) >= max_{r not in {i,j}} L_r.
   A feasible pair can be top-2 for at least one interval assignment.
3. For each feasible pair and each pairwise bin assignment
   (z_i, z_j) in [L_i,U_i] × [L_j,U_j]:
   3.1 Allocate exact integer mass with the public token-ID tie rule.
   3.2 Map the shared PRF fraction to a token and add it to D.
4. If b_m + Δ >= the second-largest L_i, add UNKNOWN_TAIL to D.
5. Return invariant iff D = {y}; otherwise emit a sparse correction.
```

第 2 步是盒约束下候选对可行性的充分条件；第 3 步枚举是保守上界，因为某些 pairwise bin 指派可能不与其他 token 的 top-2 可行性同时成立。该保守性只能增加记录位置，不能使屏幕错误地把已枚举的非参考公开决策标为安全。

## 半径校准与数据分离

- 开发材料：R055 seed-0。偶数 prompt 的每条轨迹分数为 `common_envelope_max_bin_shift` 的 step 最大值；`alpha=0.10` 取最大 calibration score，得到 (Delta)。质量半径仍按 R056 的偶数 prompt 规则校准。
- 奇数 prompt 已被 R056/R057 查看，只输出**开发性**诊断，不作确认性主张。
- 确认材料：R044 seed 1、2。R059 在同一 GPU 上重新采集 FP16/BF16 轨迹，使用 R058 冻结的 (Delta)、质量半径和代码哈希；不按确认数据调整任何规则。

## 复杂度与终止性

对于 envelope 大小 (m) 与半径 (Delta)，最多枚举 `C(m,2) × (2Δ+1)^2` 个二元整数合同，时间复杂度为 `O(m^2(2Δ+1)^2)`，空间为 `O(|D| + m)`。本研究固定 `m=16, Δ` 为小整数，因此无迭代优化与收敛问题，有限枚举必然终止。

## 冻结验收

- 开发信号：回顾性 10/10 精确覆盖，且总负载低于 R056 的 63.0174% 完整轨迹负载。
- 确认性 pilot（R059）：每个未使用 seed 至少 9/10 prompt 精确覆盖，合并负载低于 R056 基线；同时报告 tail 触发数、可行合同数、证书密度和错误类型。
- 若开发或确认失败，保留完整负结果；不得通过缩小 (Delta)、更换 split 或移除 tail 检查追求正结果。

## 主张边界

该方法只对“top-16 envelope 内每 token 独立整数 bin 扰动不超过 (Delta)”的抽象模型给出保守决策不变性结论。它不等价于模型浮点计算的全局误差界，也不声称跨硬件、跨模型或原始语言模型分布的安全性。
