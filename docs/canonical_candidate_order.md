# Canonical Candidate Order

## 目的

SparSamp 把候选 token 的概率质量映射为连续区间。即使两个模型执行得到相同的候选集合，浮点精度差异也可能改变概率降序，从而改变区间位置并导致编码、解码分歧。

R023 在 top-p 支持选择完成后提供公开的规范顺序：按稳定 `token_id` 升序排列候选。默认仍为 `probability`，因此旧配置和旧 artifact 保持兼容；新合同必须显式设置 `candidate_order="token_id"`。

## 输入与输出

输入：

- top-p 截断后候选集合 `S = {(v_i, q_i, r_i)}`；
- `v_i` 为唯一整数 token ID；
- `q_i > 0` 且 `sum_i q_i = 1`；
- `r_i` 为截断前的概率排名；
- 排序合同 `candidate_order`。

输出：

- `probability`：维持 top-p 选择阶段的概率降序；
- `token_id`：按 `v_i` 升序返回候选；
- 每个 token 的 `q_i`、文本、bytes 和原始概率排名 `r_i` 均不变。

## 算法

```text
ALGORITHM CANONICAL-CANDIDATE-ORDER(S, mode)
INPUT: retained candidates S = [(v_i, q_i, r_i)] and public mode
OUTPUT: ordered candidates S'

1. If mode is probability, return S unchanged.
2. If mode is token_id, sort S by integer token ID v_i ascending.
3. Return the reordered sequence while preserving every (v_i, q_i, r_i) tuple.
```

Provider 的完整次序是：先计算 logits 和 top-p 支持，再归一化概率并确定原生采样 token，最后应用公开候选顺序。规范排序不参与支持选择，也不改变 `source_mass`。

## 正确性

### 条件顺序一致性

设编码端和解码端在步骤 `t` 得到相同候选支持 `S_t`，token ID 在固定 tokenizer revision 下唯一且稳定。整数升序是该有限集合上的全序，因此：

```text
sort_token_id(S_t^enc) = sort_token_id(S_t^dec).
```

所以规范顺序消除了“候选集合相同、概率排名不同”造成的区间排列分歧。

该结论是条件保证，不证明两端候选支持必然相同。top-p 边界附近的候选 churn 仍会使合同失败。

### 目标分布不变性

对任意候选排列 `pi`，令候选 `v_i` 的区间长度为 `q_i`。若公共随机位置 `U` 在 `[0,1)` 上均匀，则：

```text
Pr[select v_i] = length(I_i) = q_i.
```

因此仅置换区间位置不改变以 token 标签定义的目标分布 `Q`，也不改变截断产生的 `KL(Q || P) = -log(source_mass)`。

若后续使用有限整数质量合同，最大余数法的余数平局按候选位置打破。规范重排可能改变获得最后一个计数的 token，但仍满足该量化合同已有的误差界；不能把“目标分布不变”误写成“所有有限精度实现计数逐 token 不变”。

### 重放充分条件

某一步精确合同重放至少需要：

1. 两端候选支持集合相同；
2. 两端使用相同 `candidate_order`；
3. 每个 token 的概率经过选定 Decimal 或整数质量合同后逐 token 相同；
4. tokenizer、模型 revision、top-p、温度和其他公开配置相同。

规范排序只直接保证第 2 项，并在第 1 项成立时固定候选排列。

## 复杂度

- `probability` 模式：额外时间 `O(K)` 用于冻结候选序列，额外空间 `O(K)`；
- `token_id` 模式：排序时间 `O(K log K)`，输出空间 `O(K)`；
- 模型前向计算和 top-p 支持选择复杂度不变。

## 实现合同

```json
{
  "candidate_order": "token_id"
}
```

- 默认值为 `probability`；
- 非默认合同写入 Provider `context_id`，防止不同区间合同共享 PRF 流；
- snapshot metadata 和实验 artifact 记录实际合同；
- `rank` 始终表示原概率排名，不表示规范排序后的数组下标；
- FP32/FP16 审计按 `rank=0` 选择共享 top-1 前缀，避免把轨迹变化误当成排序改进。

## 不支持的结论

R023 不证明：

- 跨 FP16/FP32 完整消息一定恢复；
- top-p 候选支持稳定；
- 概率漂移被消除；
- 容量、语义质量或不可检测性优于原始 SparSamp；
- 规范排序本身提供秘密性。

它只验证一个可审计的上游机制：在支持集合相同时，将候选顺序从浮点概率排名依赖改为 tokenizer token-ID 依赖。

## R023 实证结果

GPT-2 FP32 -> FP16 的 32 步共享前缀实验中，候选顺序一致由 `14/32` 提升到 `20/32`，等于候选集合一致步数，验证了条件顺序一致性。但 Decimal 和 integer `b={16,20,24,28,32}` 的精确合同一致率均保持 `10/32`。

因此该机制的实证结论是 `PARTIAL-GO`：它完全修复了观测到的“同集合、不同顺序”，却没有修复逐 token 概率漂移。该结果支持保留 token-ID 规范顺序作为后续合同组件，但不支持单独宣称跨精度恢复性能提升。
