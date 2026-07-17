# FH-SparSamp v1 算法设计

## 目的

固定 block 的 SparSamp 只有在当前 block 的稀疏区间收缩到单点后，才能确认该
block 的全部 bit。有限 token 预算在 block 中途结束时，未完成 block 的进度会全部
丢失。FH-SparSamp v1 在每个 block 边界根据可重放状态选择 block size，目标是在
预算宽松时保留大 block 的长期容量，在预算紧张时减小尾部失败风险。

该版本是待实验验证的控制器，不预设其优于最佳固定 block。

> 实验状态（2026-07-17）：v1 已被拒绝。128-token 成功率为 2/6，低于固定
> block 16 的 5/6；160-token 为 5/6，低于固定 block 16 的 6/6。后续
> tail-fragmentation 烟雾实验也未超过固定 16。本实现保留用于负面结果复现，
> 不作为推荐默认算法。

## 输入与输出

输入：

- 确定性模型会话及每步候选概率分布；
- 固定且双方已知的 payload 长度 `L`；
- 最大生成预算 `T`；
- 候选 block 集合 `B={8,16,32}`；
- 熵 EMA 系数 `alpha`、最低有效熵 `H_min`；
- 容量比阈值 `rho_tight < rho_loose`；
- 二进制 payload、共享密钥和概率量化配置。

输出：

- cover token IDs 和公开文本；
- 完成的 payload bit 数与逐 token block 选择；
- 若在预算内完成，则输出可精确重放的全部 payload；
- 若未完成，则返回包含部分进度的 `IncompleteEncodeError`。

payload 长度 `L` 在 v1 中是公开实验参数。若实际消息长度敏感，应先填充到固定长度，
不能让控制器直接暴露可变明文长度。

## 控制规则

在 step `t` 的新 block 开始前，计算：

```text
remaining_tokens = T - t
remaining_bits   = L - completed_bits
H_eff            = max(H_ema, H_min)
rho              = H_eff * remaining_tokens / remaining_bits
```

`rho` 是按当前熵估计的剩余信道容量与剩余 payload 的比值。控制器把
`[rho_tight, rho_loose]` 均分为 `|B|` 个区间：

- `rho <= rho_tight`：选择最小可用 block；
- `rho >= rho_loose`：选择最大可用 block；
- 中间区域：按 `rho` 所在区间选择对应 block；
- 最后不足最小 block 的 payload 直接使用实际剩余 bit 数，不添加隐式 padding。

熵 EMA 仅使用当前及历史模型分布：

```text
H_ema <- H_t                              第一个观测
H_ema <- alpha * H_t + (1-alpha) * H_ema  后续观测
```

## 伪代码

```text
ALGORITHM: FH-SparSamp Encode
INPUT: payload m[0:L], key K, model session S, config C
OUTPUT: cover tokens y, completed bits, audit records

1. completed <- 0; active_block <- none; H_ema <- none
2. FOR t = 0 ... T-1:
   2.1 P_t <- S.next_distribution()
   2.2 更新 H_ema
   2.3 IF P_t 不满足可嵌入门限:
         选择原生采样 token，转到 2.7
   2.4 IF active_block is none:
         b <- controller(H_ema, T-t, L-completed)
         初始化 SparSamp 区间 N=2^b 和消息整数 k
   2.5 用论文 SparSamp 逆 CDF 规则选择 token 并更新 (k,N)
   2.6 IF N=1:
         completed <- completed+b; active_block <- none
   2.7 S.append(token)，保存 step、b、熵和 completed
   2.8 IF completed=L: RETURN 完成结果
3. RAISE IncompleteEncodeError(部分 token、completed、records)
```

解码器在相同 step 使用相同分布、EMA、剩余预算和已恢复 bit 数运行同一控制器，
随后使用 SparSamp 的反向区间递推恢复每个动态 block。

## 正确性与终止条件

- 若编码器和解码器使用相同模型、prompt、密钥、数值精度、预算和控制器配置，
  每个完成 block 的反向区间递推与固定 block SparSamp 相同，因此可精确恢复。
- 算法在 `T` 个 token 后有限停止，但不保证 payload 一定完成；未完成是实验结果，
  不能通过静默增加预算隐藏。
- 控制器只在 block 边界选择大小，不允许在 block 中途切换，否则会破坏当前区间状态。

## 分布与安全边界

block 选择不读取当前未编码秘密 bit 的取值，只读取双方可重放的模型分布、step、
固定 payload 长度和已完成长度。选定 block 后仍执行原 SparSamp 条件采样。

v1 尚未给出自适应停止时间下的完整不可检测性证明。论文中必须分别验证：

- token 级分布和 steganalysis 指标是否相对固定 block 退化；
- block schedule、文本长度或停止位置是否泄漏额外信息；
- 跨精度和公开文本重分词时能否重放相同 schedule。

## 复杂度

- 控制器每个新 block 扫描 `|B|` 个候选，时间 `O(|B|)`，空间 `O(1)`；
- SparSamp 区间更新仍为每 token `O(1)`；
- 总成本仍由模型前向和词表排序主导，本地 Provider 每 token 约为
  `O(model_forward + V log V)`；
- 审计记录为 `O(T)`，未完成 block 的解码状态为 `O(L_block)`。

## 第一轮消融

- 固定 block：8、16、32；
- FH 完整控制器：`rho_tight=1.0`、`rho_loose=1.5`；
- 熵关闭：固定 `H_eff=1.0`；
- 预算关闭：始终选择最大 block；
- 预算：96、128、160、192 tokens；
- 主指标：完整消息成功率；次指标：bit/token、p95 tokens、Token Ambiguity、速度。
