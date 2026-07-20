# R031：认证消息的 RS 冗余消融

## Ablation Plan

| # | 变体 | What it tests | 若 RS 冗余是主要瓶颈，预期现象 | 优先级 |
|---|---|---|---|---:|
| 1 | `parity=16` | 覆盖中等数量擦除的能力 | 跨精度成功率高于 R030，净容量下降 | 1 |
| 2 | `parity=32` | 覆盖高擦除和少量错误的能力 | 若仍为 0，说明错误率而非擦除数是主瓶颈 | 1 |

固定项：GPT-2、FP32 编码 / FP16 解码、`top_p=0.95`、`q=1/16`、
8-token window、3 prompts × 2 messages、ChaCha20-Poly1305 frame。

## 数学审计预期

RS 的可纠正条件为

\[
2e+s\leq p,
\]

其中 `e` 是未标记错误、`s` 是擦除数、`p` 是 parity bytes。R030 的
`q=1/16, parity=2` 平均观测到 `raw=29.33`、`s=17.67`，对应粗略
校验需求 `2(raw-s)+s = 41`。这个估计不是 R031 的保证，因为增加 parity
也会增加需要解码的窗口；R031 的目的正是验证这一反馈效应。

## 可复现实验

```powershell
.venv\Scripts\python.exe scripts\audit_byte_sliced_aead.py `
  --model models\gpt2 `
  --device cuda `
  --reference-dtype float32 `
  --replay-dtype float16 `
  --top-p 0.95 `
  --window-tokens 8 `
  --parity-bytes 16 32 `
  --logit-quantum 0.0625 `
  --run-label R031 `
  --output outputs\R031_gpt2_aead_rs_sweep.json
```

## 结果判定门

- 同精度消息成功必须接近 100%；否则先修正实现，不解释跨精度。
- 跨精度完整消息成功率若仍为 0%，记录为 RS-only NO-GO，并转向窗口级
  重同步/选择性重试；不继续无目的增加 parity。
- 若出现成功，下一轮至少扩大到 20 条消息，并报告净容量、费用/bit 和
  成功率置信区间。

## 第一次运行状态

- 2026-07-20：原命令达到 30 分钟硬超时，退出码 `124`。
- 原脚本仅在全部 trial 完成后写 JSON，因此没有可分析的部分结果；不得据此
  判断 parity 16 或 32 的成败。
- 已修改审计脚本：每完成一个 reference/replay trial 都原子写入 checkpoint，
  `phase` 分别为 `reference_partial`、`replay_partial` 或 `completed`。
- checkpoint 包含完整实验配置签名；再次运行相同命令会自动跳过已完成的
  reference/replay trial。参数不一致时拒绝合并；只有显式 `--fresh` 才从零开始。
- 用户已确认授权以更长 timeout 重跑，并要求每次保留上次进度。
