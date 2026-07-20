# R030：认证消息级 Byte-Sliced pilot

## 研究问题

R029 只验证了 RS 恢复原始字节。R030 检验同一方案在真实
ChaCha20-Poly1305 frame 上是否仍能恢复可认证的完整消息，并比较
`parity=2` 与 `q=1/16 + parity=2` 的跨 FP32/FP16 表现。

## 设计

- 模型：本地 GPT-2，FP32 编码、FP16 解码，`top_p=0.95`。
- prompt：3 个固定语义 prompt。
- 消息：`Trust tests.`、`Protect meaning.`。
- 每条 frame 使用由 HMAC 派生的唯一 12-byte nonce；密钥不写入输出。
- RS：parity bytes 分别为 2；另加 top-logit quantum `q=1/16`。
- Byte-Sliced：每个窗口 8 token 嵌入一个 8-bit symbol。
- 成功定义：RS 输出 frame 字节完全相等，且 `PayloadCodec.open` 返回原文。

## 关键边界

AEAD 通过只代表消息完整性，不代表概率合同、隐写不可检测性或跨精度可靠通信。
pilot 样本量为 3 prompts × 2 messages × 2 variants = 12，不能用于显著性结论。
若同精度控制失败，应先调整窗口长度，再解释跨精度结果。

## 实测结果（2026-07-20）

输出：`outputs/R030_gpt2_aead_byte_sliced.json`。

| 变体 | trials | 同精度 frame/消息 | 跨精度 frame/消息 | 平均擦除 | 平均 raw symbol errors |
|---|---:|---:|---:|---:|---:|
| `parity=2,q=none` | 6 | 5/6, 5/6 | 0/6, 0/6 | 17.17 | 33.67 |
| `parity=2,q=1/16` | 6 | 6/6, 6/6 | 0/6, 0/6 | 17.67 | 29.33 |

两种变体的平均 frame 长度均为 50 bytes；有效编码容量约为
`0.9615 payload bit/token`，codeword 容量为 `1.0 bit/token`。
跨精度失败行的 `bit_errors` 等于完整 frame 的 bit 数，且 RS 返回
`Too many erasures to correct`，不是 AEAD 偶然拒绝一个近似正确的 frame。

## 阶段结论

`parity=2` 的 R029 配置不能直接扩展到真实 AEAD 消息。`q=1/16` 改善了
同精度合同和平均 raw symbol errors，但在 frame 级别没有形成可用通信链路，
因此 R030 判定为 **NO-GO（原配置）**，不是 SparSamp-API 成功证据。
下一阶段应优先评估能覆盖约 18 个擦除的高冗余 RS 或更短认证帧，并同时
报告净容量下降；不能只增加消息长度或扩大样本量来掩盖该结构性瓶颈。

## 可复现实验

```powershell
uv run --no-sync python scripts\audit_byte_sliced_aead.py `
  --model models\gpt2 `
  --device cuda `
  --reference-dtype float32 `
  --replay-dtype float16 `
  --top-p 0.95 `
  --window-tokens 8 `
  --parity-bytes 2 `
  --logit-quantum 0 0.0625 `
  --output outputs\R030_gpt2_aead_byte_sliced.json
```

`q=0` 表示不做 logit 量化；脚本将其规范化为 `null`，对应已有默认概率路径。
