# Rotation Range Coding 复现设计

## 目的与证据边界

本模块独立复现 Yan 和 Murawaki 在 ACL 2026 提出的 Rotation Range-Coding (RRC)
语言隐写算法，用于检验其是否能在 Qwen 等语义模型上弥补 SparSamp 的有限 block
容量损失。论文规范页为 <https://aclanthology.org/2026.acl-long.39/>，本地核验文本来自
ACL 论文 PDF。作者 GitHub 仓库当前没有许可证，因此本实现只依据论文 Algorithm 3、
Algorithm 4 和正文公式编写，不复制其源码。

论文声称的零 KL 散度成立于每一步使用语言模型完整目标分布和理想连续算术的条件下。
本项目默认使用 top-p=0.95，因此只对截断后重归一化分布 Q 保持 RRC 采样性质；相对原始
模型分布 P 仍报告 `-log(source_mass)` 截断偏差，不能写成对 P 的零 KL。

## 输入与输出

输入：确定的模型/采样配置、公开 prompt、长度为 `message_bits` 的二进制密文、至少
16 bytes 的共享密钥，以及最大生成 token 数。

输出：stego token 序列、可见文本、逐步熵/概率质量/耗时记录；解码输出固定长度 bit 串。
编码器和解码器必须重放相同模型、tokenizer、prompt、精度和候选分布。

## 算法

```text
EMBED(bits, key):
  ds <- integer(bits); [L, R) <- [0, 2^message_bits)
  for t = 0 .. max_tokens-1:
    p <- normalized next-token probabilities
    width <- R - L
    o_t <- HMAC-PRF(key, context, t) in [0, 1)
    ds <- L + positive_mod(ds - L + o_t * width, width)
    choose token i whose rescaled cumulative interval contains ds
    [L, R) <- interval(i)
    append token i
    stop when (L + R)/2 - ds is in (-0.5, 0.5]

EXTRACT(tokens, key):
  replay tokens and store every pre-update interval [L_t, R_t)
  mid <- midpoint of final interval
  for t in reverse order:
    mid <- L_t + positive_mod(mid - L_t - o_t * (R_t - L_t), R_t - L_t)
  ds <- round_half_down(mid)
  return fixed-width binary(ds)
```

## 数值实现与终止审计

参考版本使用 Python `Decimal`，精度为
`max(min_precision, ceil(message_bits * log10(2)) + 1 + guard_digits)`。概率先按公开
`probability_quantum` 量化并重新归一化，编码和解码必须使用相同参数。正模单独实现，避免
负数余数破坏反向旋转。若在 `max_tokens` 内未满足论文终止条件，返回带完整 token 前缀和
审计记录的 `IncompleteEncodeError`。

独立实现发现论文 Algorithm 3 的局部终止条件并不总能保证 Algorithm 4 精确恢复：最终
中点与旋转后秘密的线性距离虽然小于等于 0.5，但反向模旋转跨越上/下边界后，该距离会变成
`distance - previous_width`。一个固定 64-bit 反例在 141 位 Decimal 精度下仍解码为原值减
2，排除了精度不足。500 个确定性 Mock 随机样本的论文原样成功数为：16 bit 93/100、
32 bit 92/100、64 bit 95/100、128 bit 91/100、256 bit 93/100。

因此本参考版本只用于复现和反例审计，不能作为可靠通信实现。下一版本必须在发送端对候选
终止点执行完整反向重放，仅在接收端的公开解码规则确实恢复原整数时停止。该检查不改变每步
token 选择，只可能增加尾部 token；其长度侧信道和容量损失需要单独测量。

时间复杂度是每 token `O(K)`，K 为 top-p 后候选数；解码额外保存 `O(T)` 个区间，T 为
stego token 数。模型前向和候选排序不包含在 codec 的渐进复杂度中，但包含在端到端实验
时间中。

## 实验门禁

- 人工分布和 MockProvider：保留可复现的 modular-wrap 反例，并在修复版要求
  1/13/64/128 bit 精确 round-trip。
- 相同 context 和 key：token 序列确定。
- 错 prompt/key/config：不得恢复原 payload。
- Qwen：与 Fixed-16、Fixed-64 在相同 payload、prompt、top-p、temperature 和 token budget
  下比较完成率、bits/token、token/s、Token Ambiguity 和截断 KL。
- 只有 token-ID 解码、公开文本重分词和多 seed 均通过后，才讨论语义质量和安全优势。
