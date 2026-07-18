# Support-Adaptive Integer Mass Contract

## 目的

R022-R023 表明，固定 `16-32 bit` 整数质量不能吸收 GPT-2 FP32/FP16 的概率漂移。更粗的质量格可能提高重放一致率，但 support-preserving 分配要求总质量至少覆盖全部正概率候选。

R024 定义每步动态位宽：

```text
b_t = max(1, ceil(log2 K_t)) + h,
M_t = 2^b_t,
```

其中 `K_t` 是保留支持中的正概率候选数，`h >= 0` 是公开 headroom。该合同保证 `M_t >= K_t`，并避免固定低位宽在高熵步骤无法保留支持。

## 输入与输出

输入：

- 规范排序后的候选概率 `Q=(q_1,...,q_K)`；
- 公开 headroom `h`；
- 支持策略 `base | waterfill`。

输出：

- 有效位宽 `b` 和总质量 `M=2^b`；
- 整数计数 `c_i >= 1`；
- `sum_i c_i=M`；
- 实现分布 `R_i=c_i/M`；
- `KL(Q||R)` 与 `TV(Q,R)`。

生产 `CodecConfig` 仍限制固定整数质量为 `16-52 bit`。`1-15 bit` 只在 R024 审计中使用，未经结果门禁不接入编码器、REST API 或前端。

## Legacy Base 策略

现有策略先给每个候选一个计数，再把 `M-K` 个计数按原始 `Q` 分配。其连续近似为：

```text
R_i approximately 1/M + (1-K/M) q_i.
```

当 `M` 接近 `K` 时，该策略把分布明显推向均匀分布。它作为 R022 兼容基线保留，不作为最优性声明。

## KL Waterfill 策略

先求连续约束问题：

```text
minimize    KL(Q||R) = sum_i q_i log(q_i/r_i)
subject to  sum_i r_i = 1
            r_i >= 1/M for q_i > 0.
```

KKT 条件给出唯一的 token-label 分布：

```text
r_i* = max(1/M, alpha q_i),
```

其中 `alpha` 使 `sum_i r_i*=1`。实现按概率升序固定违反下界的尾部候选，并对剩余候选重新计算 `alpha`，有限步终止。

随后令 `u_i=M r_i*`，先取 `floor(u_i)`，再按小数余数降序补齐剩余计数，同余数按规范候选顺序打破平局。因为 `r_i* >= 1/M`，所有正概率候选的 floor 至少为 1。

```text
ALGORITHM WATERFILL-INTEGER-MASS(Q, h)
INPUT: ordered positive distribution Q, public headroom h
OUTPUT: integer counts c and mass bits b

1. K <- number of positive candidates.
2. b <- max(1, ceil(log2 K)) + h; M <- 2^b.
3. Sort positive candidates by (q_i, candidate_index) ascending.
4. Repeatedly fix the smallest candidate at 1/M while alpha*q_i < 1/M.
5. Set every remaining r_i <- alpha*q_i so sum_i r_i = 1.
6. Set c_i <- floor(M*r_i).
7. Give residual counts to the largest fractional remainders.
8. Return (c, b).
```

## 正确性

### 有限终止

水填充循环每次至少固定一个候选，最多执行 `K` 次。实际实现排序后从最小概率依次扫描，不会回退。

### 支持保持与质量守恒

由 `M>=K` 且 `r_i*>=1/M`，正概率候选满足 `floor(Mr_i*)>=1`。最大余数补齐只增加计数，因此最终 `c_i>=1` 且 `sum_i c_i=M`。

### 连续 KL 最优性

对未触发下界的候选，KKT 驻点满足 `r_i=alpha q_i`；触发下界的候选满足 `r_i=1/M`。目标函数对正 `r_i` 为凸函数，可行域为凸集，因此该 KKT 解是全局最优连续支持保持投影。

该结论不等价于整数格上的全局 KL 最优。最大余数量化保证逐项相对连续投影误差小于 `1/M`，实际 KL/TV 必须实验报告。

## 复杂度

- 候选概率排序：`O(K log K)`；
- 水填充扫描：`O(K)`；
- 最大余数排序：`O(K log K)`；
- 总时间：`O(K log K)`；
- 工作空间：`O(K)`；
- 无迭代收敛容差，全部计算使用精确 `Fraction`，有限步终止。

## 安全边界

- 动态位宽依赖候选数；候选集合 churn 仍会改变 `K`、位宽和计数合同；
- 更粗质量提高容错时会增加分布偏差，不能只报告恢复率；
- waterfill 只最小化给定支持下的概率偏差，不提高模型语义质量；
- 本合同不改变 token-ID 规范顺序，也不解决 tokenizer ambiguity；
- 未达到 R024 门禁前，不宣称比原论文 SparSamp 更安全或更高效。

## R024 实证结果

GPT-2 FP32 -> FP16 的 32-step 共享前缀审计中，固定 `16-32 bit` 合同保持 `10/32`。支持自适应合同出现恢复率与偏差的 Pareto 前沿：

- `waterfill+h3`：`15/32`，mean KL `0.005717`，mean TV `0.015272`；
- `waterfill+h4`：`14/32`，mean KL `0.001061`，mean TV `0.005074`；
- `waterfill+h0`：`18/32`，但 mean KL `0.380171`、mean TV `0.297922`，因偏差过大被拒绝。

按预注册门禁，R024 判定为机制级 `GO`，推荐 `waterfill+h3` 进入消息级验证。相同 headroom 下，waterfill 在全部 7 个设置上都降低 mean KL 和 mean TV，说明 KL 投影相对 legacy base 的改进不是单点偶然。

该结果仍受 12 个 top-p 候选 churn 步骤限制。`15/32` 是逐步合同一致率，不是完整消息成功率，不能直接转写为端到端恢复提升。
