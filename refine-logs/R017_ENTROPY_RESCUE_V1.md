# R017 Public-State Entropy Rescue V1

日期：2026-07-17

## 配置

- 512-bit payload，3 个中文 prompt。
- Fixed-16 与 Verified-RRC。
- 基础 temperature 0.8；基础完整分布熵连续 8 步低于 1.0 后切换到 1.1。
- 800-token 嵌入预算，V2 语义收尾。

## 结果

| Prompt | Codec | Fixed-temperature baseline | Rescue V1 | Rescue fraction | Mean retained entropy |
|---:|---|---|---|---:|---:|
| 0 | Fixed-16 | 800 tokens 未完成 | 459 tokens 完成 | 0.2% | 1.289 |
| 0 | RRC | 415 tokens 完成 | 523 tokens 完成 | 7.5% | 0.903 |
| 1 | Fixed-16 | 800 tokens 未完成 | 800 tokens 未完成 | 48.4% | 0.462 |
| 1 | RRC | 458 tokens 完成 | 341 tokens 完成 | 0.0% | 1.452 |
| 2 | Fixed-16 | 465 tokens 完成 | 800 tokens 未完成 | 58.1% | 0.482 |
| 2 | RRC | 800 tokens 未完成 | 800 tokens 未完成 | 54.1% | 0.525 |

总完成率仍为 3/6，没有超过固定温度基线。失败轨迹即使长时间处于救援状态，temperature
1.1 仍未把保留分布熵提高到足以稳定编码的水平。

## 审计发现

V1 将 adaptive controller 参数写入 HMAC 随机流的 `context_id`。因此改变控制器配置会从
第一个 token 起改变秘密采样随机流，即使救援从未激活也不是同一轨迹。Prompt 1 的 RRC
在 0 个 rescue steps 下从 458 变为 341 tokens，证明该结果不能归因于救援机制。

## 决策

拒绝 V1 的性能结论。V2 必须让固定和 adaptive 配置共享基础 PRF 流，在第一次救援前保持
token 前缀一致；随后再测试更强救援温度。安全上仍需把完整控制器配置保存在 artifact，并
通过解码重放和 AEAD 校验发现配置不匹配。
