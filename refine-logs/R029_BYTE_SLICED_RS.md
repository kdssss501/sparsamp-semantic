# R029：Byte-Sliced RS 跨精度 Pilot

## 研究问题

将 R026 的 16-bit 认证微帧拆成 8-bit RS codeword 字节，能否在 GPT-2 FP32 编码、FP16 解码下提高完整 payload 恢复率？

## 预注册组件消融

固定 2-byte payload、8 token/window、3 prompts × 2 payload seeds：

1. parity=0：Byte-Sliced 基线；
2. parity=2：检验 RS 是否提供恢复增益；
3. parity=4：检验更多冗余是否继续提高恢复；
4. `q=1/16 + parity=2`：只在前三项完成后，组合 R027 唯一有结构改善的粗 logit 网格。

同精度控制必须全部成功；主指标为完整 payload 成功率、aggregate BER、原始字节错误、擦除数和净 bits/token。

## 实现

- 新增 `ByteSlicedCodec`、`ByteSlicedConfig` 和逐窗口审计记录；
- 使用成熟 `reedsolo`，不手写 RS；
- 支持编码端 R028 CDF guard，但本轮主实验不启用 worst-case guard；
- 新增单条审计和 batch 审计脚本；
- Mock 下 raw bytes、RS、中文消息 AEAD 完整通过。

## GPT-2 FP32→FP16 结果

| 变体 | 同精度 | 跨精度完整恢复 | BER | 原始字节错误 | 擦除 | 净 payload bit/token |
|---|---:|---:|---:|---:|---:|---:|
| parity=0 | 6/6 | 0/6 | 0.8438 | 1.667 | 1.167 | 1.000 |
| parity=2 | 6/6 | 1/6 | 0.6458 | 2.667 | 1.500 | 0.500 |
| parity=4 | 6/6 | 1/6 | 0.7396 | 4.333 | 2.333 | 0.333 |
| `q=1/16`, parity=2 | 6/6 | 3/6 | 0.5000 | 1.667 | 0.833 | 0.500 |

相对未量化 parity=2，组合版本完整恢复率从 16.7% 提高到 50%，BER 相对下降约 22.6%，平均擦除下降约 44.4%，原始字节错误下降 37.5%，容量不变。parity=4 没有继续提高恢复率，说明盲目增加冗余会因更多窗口暴露于漂移而抵消纠错收益。

## 判定

`PARTIAL-GO-STAGE`。

这是项目首次在相同 Byte-Sliced 容量下观察到跨精度完整恢复增益，并且同精度控制保持 100%。但样本仅 6 条、payload 仅 16 bits，仍不能声称统计显著、优于原始 SparSamp、支持 Qwen 或已实现可靠消息通信。

## 下一步 R030

1. 使用 `PayloadCodec` 生成真实 AEAD frame，而不是 2-byte 已知 payload；
2. 对 `q=1/16, parity=2` 扩大到至少 20 条短消息；
3. 报告最终 AEAD 成功率，任何未认证 payload 都算完整失败；
4. 与 pinned FP16→FP16 控制和 R025 Decimal 基线比较；
5. 仅在 AEAD 成功率可复现后迁移到 Qwen 中文生成。
