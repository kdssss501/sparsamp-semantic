# R029：Byte-Sliced Reed-Solomon SparSamp

## 目的

R028 证明稀疏区间的初始整数尺度是跨精度脆弱性的关键因素。逐窗口加入 8-bit tag 会把 1-byte 数据帧扩大为 16 bits，使初始状态从 `n=256` 增加到 `n=65536`。R029 将每个固定窗口恢复为单独的 8-bit RS codeword 字节，认证移到完整消息层。

## 输入与输出

- 输入：payload bytes、秘密密钥、公开 prompt、RS parity 字节数、固定窗口长度；
- 输出：固定窗口 token 序列、恢复 payload、纠正后的 RS codeword、错误和擦除记录；
- 每个窗口的 SparSamp block size 固定为 8；
- 完整消息必须由 `PayloadCodec` 的 ChaCha20-Poly1305 或等价 AEAD/MAC 再验证。

## 算法

```text
ENCODE
  codeword = RS.encode(authenticated_payload, parity_bytes)
  for each byte c_j in codeword:
    reset sparse interval with n=256, k=c_j
    embed inside a public fixed-length token window
    after singleton, fill remaining positions with native model sampling

DECODE
  independently invert each token window to a byte or erasure
  RS.decode(recovered_codeword, erasure_positions)
  authenticate the complete recovered payload with AEAD/MAC
```

RS 能纠正 `2e+s <= parity_bytes` 的错误/擦除组合，其中 `e` 为未知错误字节、`s` 为已知擦除。无逐窗口 tag 时，错误字节不会自动变成擦除，因此最终 AEAD 验证是必需条件。

## 安全与分布边界

Byte-sliced 只改变秘密块的分组和外层冗余，不改变每一步的目标模型条件分布。若 payload 已经由 AEAD 加密，payload 字节在计算意义上接近伪随机；RS parity 带来跨窗口相关性，因此不能写成固定密钥下的信息论独立均匀或严格零 KLD。

## 复杂度

对 `m` 个 codeword bytes、每窗口 `W` 个 token、平均候选数 `K`，SparSamp 部分时间为 `O(mWK)`，状态空间为 `O(W)`；RS 复杂度由 `reedsolo` 实现决定。固定窗口下净容量为 `8*payload_bytes / (W*(payload_bytes+parity_bytes))` bit/token。
