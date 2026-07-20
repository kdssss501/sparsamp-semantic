# R032：共享粗粒度 logit 合同

## Purpose

R031 证明固定 RS 冗余无法修复 FP32/FP16 产生的大比例擦除与未标记错误。
R032 在稀疏区间编码之前量化相对 logits，目标是减少编码端和解码端的分布差异，
而不是继续纠正已经产生的错误。

## Input / Output

输入：

- next-token logits `l in R^V`；
- 公开量化步长 `q > 0`；
- 温度 `T > 0`、固定 top-p/top-k 和候选排序规则；
- FP32/FP16 两端共享的 prompt、token prefix 和模型版本。

输出：

- 整数 bins `z in Z^V`；
- 量化 logits `l_tilde`；
- 截断并归一化后的候选分布；
- bin/support/probability 合同指标和量化 KL/TV。

## Algorithm

对有限 logits，令 `m=max_i l_i`：

\[
z_i=\left\lfloor\frac{l_i-m}{q}+\frac12\right\rfloor,
\qquad \tilde l_i=qz_i.
\]

```text
ALGORITHM: Coarse shared-logit contract
INPUT: logits l, quantum q, temperature T, truncation rule C
OUTPUT: integer bins z, retained distribution Q

1. Block public forbidden tokens identically at both endpoints.
2. Compute m = max finite(l).
3. For every finite token i:
     z_i = floor((l_i - m) / q + 1/2)
     l_tilde_i = q * z_i
4. Compute softmax(l_tilde / T) using the shared numeric implementation.
5. Apply stable token-ID tie breaking and the fixed truncation rule C.
6. Normalize retained probabilities and return z and Q.
```

## Correctness And Distortion

在理想实数运算中，如果两端所有有限 token 的 `z_i` 相同、屏蔽集合相同且截断
规则确定，则量化分布完全相同。当前实现把两端 logits 转为 FP32 后执行 softmax，
该结论只在相同实现环境中接受实验证据；跨硬件严格合同仍需要固定点 softmax 或
整数质量分配，不能由本轮结果推出。

令 `x_i=l_i-m`，则 rounding 给出

\[
|x_i-\tilde l_i|\le q/2.
\]

在完整词表、top-p 截断之前，有保守界

\[
\mathrm{KL}(P\|\tilde P)\le q\ \text{nats}.
\]

top-p 边界可能产生不连续支持变化，因此最终候选分布必须另行报告实测支持一致率、
KL 和 TV，不能只引用上述完整词表界。

## Complexity

- 量化：时间 `O(V)`，空间 `O(V)`。
- softmax：时间 `O(V)`，空间 `O(V)`。
- 全词表稳定排序：时间 `O(V log V)`，空间 `O(V)`。
- 每生成一个 token 重复一次；不引入迭代收敛过程。

## Registered Gate

在 GPT-2 FP32/FP16 的同一 32-step prefix 上扫描
`q={1/16,1/8,1/4,1/2}`，选择满足下列条件的最小 `q`：

1. Decimal 精确概率合同至少 `30/32`；
2. 候选集合与顺序一致至少 `30/32`；
3. 平均完整词表量化 KL 不超过 `0.005` nats；
4. 平均完整词表量化 TV 不超过 `0.03`。

这些是进入消息级实验的工程门槛，不是安全性定理。若没有候选同时满足，则 R032
判为 NO-GO，不运行长 AEAD 消息实验。

## Outcome

实测扫描没有 q 满足合同门槛。`q=1/2` 的公共 bin agreement 达到约 0.970，
但 Decimal 精确合同仅 7/32、支持一致仅 19/32，且平均 KL/TV 已增至约
0.00458 nats / 0.0290。因此粗量化只能改善局部 bin 指标，不能建立端到端共享
概率合同；R032 不进入消息级实验。
