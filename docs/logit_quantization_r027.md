# R027：相对 logit 量化合同

## 目的

R022-R025 表明候选排序和整数质量不能消除 FP32/FP16 的 top-p 支持漂移。R027 在 top-p 截断前建立一个公开、移位不变的 logit 网格，检验能否把连续数值漂移转换成相同的离散支持和概率合同。

## 定义

对有限 logits `l_i`，令 `m = max_i l_i`，量化步长 `q > 0`，定义

\[
z_i = \left\lfloor \frac{l_i-m}{q}+\frac12 \right\rfloor,\qquad
\tilde l_i=qz_i.
\]

非有限位置保持为 `-inf`。量化后的概率为

\[
\tilde P_i=\operatorname{softmax}(\tilde l_i/T).
\]

相同量化 bin 的候选按 token ID 升序稳定排序；这一步只打破平局，不改变任何非平局的相对顺序。

## 数学性质

1. **移位不变性**：对任意常数 `c`，`Q(l+c)=Q(l)`，因此实现不依赖模型 logits 的绝对偏置。
2. **误差界**：对有限位置，`|(l_i-m)-\tilde l_i| <= q/2`（浮点实现允许一个 machine-epsilon 裕量）。
3. **预截断 KL 界**：设 `e_i=\tilde l_i-(l_i-m)`，则 `e_i\in[-q/2,q/2]`。有
   `log(\tilde P_i/P_i)=e_i-log E_P[exp(e)]`，所以绝对对数比不超过 `q`，从而 `KL(P||\tilde P) <= q` nats。该界只适用于量化前的完整支持，不包含 top-p 截断和后续稀疏区间舍入。
4. **合同充分条件**：若编码端和解码端的所有有限位置 `z_i` 相同，则量化 softmax、稳定排序和固定 top-k 支持相同；top-p 还要求使用相同浮点归一化规则。

## 实现输入/输出

- 输入：模型 logits、温度 `T`、公开网格 `q`、top-p/top-k 参数。
- 输出：量化 logits、整数 bins、候选分布、bin 序列、量化 KL/TV 和最大量化误差。
- 时间复杂度：完整词表上排序为 `O(V log V)`，量化为 `O(V)`。
- 空间复杂度：`O(V)`。
- 数值规则：保留 `float32` softmax；候选保留后使用 `float64` 统一归一化，禁止把舍入误差全部加到最后一个 token，避免产生负概率。

## 边界

量化不会保证两种 dtype 的 bin 一致；当原始 logit 差异跨过半格边界时，bin 仍会变化。固定 top-k 也不能单独恢复概率合同，因为候选 token 的量化概率仍可能不同。R027 因此只主张结构稳定性指标，不主张零 KL 或消息级可靠性。
