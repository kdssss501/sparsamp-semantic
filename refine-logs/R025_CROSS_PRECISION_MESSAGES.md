# R025 Cross-Precision Message Recovery

## Material Passport

- Schema：ARS Material Passport 9 compatible local record
- Stage：experiment-agent / plan -> run -> validate
- Verification Status：REPRODUCED, PARTIAL-GO-FEASIBILITY, NO-ADVANTAGE
- Date：2026-07-18
- Source：本地源码、GPT-2 FP32 encode / FP16 decode
- External upload：无

## 研究问题

R024 的逐步合同改善能否转化为真实的完整 payload 恢复？本轮不再比较共享 snapshots，而是让 FP32 SparSamp 编码器实际生成 token IDs，再由独立 FP16 Provider 重放并解码。

## 必要控制

- Provider 使用 `candidate_order=token_id`；
- 编码端与解码端显式使用 `precision_context=portable`，共享同一 HMAC 随机流；
- 同精度 FP32 encode/decode 作为阳性控制；
- 默认 `strict` context 不参与算法比较，因为其 PRF 流按定义跨 dtype 不同。

## 实验设计

| 变量 | 设置 |
|---|---|
| 模型 | 本地 GPT-2 |
| 编码精度 | FP32 |
| 解码精度 | FP16 |
| prompts | 3 个公开英文任务 prompt |
| payload seeds | `0,1` |
| 每条 payload | 16 raw bits |
| block size | 8 |
| max tokens | 256 |
| 合同 | Decimal `1e-15`、fixed integer 16、waterfill h3、waterfill h4 |
| 总试验 | 6 trials/合同，24 编码轨迹 |

payload 由 HMAC-SHA256 确定性生成。若未设置环境变量，脚本生成并复用
`outputs/R025_experiment.key`；`outputs/` 已被 Git 忽略。JSON 只记录 key fingerprint 和来源，不写入密钥。

## 指标

1. 编码完成率；
2. FP32 同精度完整消息成功率；
3. FP32 -> FP16 完整消息成功率；
4. aggregate BER：编码失败、解码异常和缺失位均按错误计入；
5. token 数、bits/token；
6. 累计 forward quantization KL 与 TV；
7. 解码异常类型和恢复位长度。

## 假设

- H1：所有合同的 FP32 同精度控制均为 `6/6`；否则实现无效，停止跨精度结论。
- H2：waterfill h3 或 h4 的完整消息成功数高于 Decimal 和 fixed-16。
- H3：waterfill h3 的恢复率可能高于 h4，但 h4 的量化偏差更低。
- Anti-claim：逐步 `15/32` 不保证消息成功；任一关键步骤合同失败都可能破坏后续状态。

## 决策门禁

- GO-PILOT：同精度全部 `6/6`；waterfill 至少 `3/6` 完整恢复，比两个基线至少多 2 次，aggregate BER `<=0.10`。
- PARTIAL-GO：同精度全部通过，waterfill 至少恢复 1 条完整消息，或相对最佳基线 BER 降低至少 20%。
- NO-GO：waterfill 完整恢复为 0，且 BER 未相对最佳基线下降 20%；转向同步检查点、纠错或支持稳定合同。
- INVALID：任何合同的同精度控制失败；先修实现，不解释跨精度结果。

本轮样本量是机制 pilot，不做显著性检验，不外推到 Qwen 或自然中文文本。

## 可复现命令

```powershell
.\.venv\Scripts\python.exe scripts\audit_cross_precision_messages.py `
  --model models\gpt2 `
  --reference-dtype float32 `
  --replay-dtype float16 `
  --payload-seeds 0 1 `
  --payload-bits 16 `
  --block-size 8 `
  --max-tokens 256 `
  --output outputs\R025_gpt2_message_audit.json
```

## 结果

原始结果：`outputs/R025_gpt2_message_audit.json`；持久化实验密钥位于 Git 忽略的
`outputs/R025_experiment.key`，JSON key fingerprint 为 `2ae7047d9430`。

| 合同 | 编码 | FP32 同精度 | FP32->FP16 完整恢复 | 成功率 | aggregate BER | 解码异常 |
|---|---:|---:|---:|---:|---:|---:|
| Decimal `1e-15` | 6/6 | 6/6 | 2/6 | 33.33% | 0.3854 | 2 |
| fixed integer 16 | 6/6 | 6/6 | 0/6 | 0% | 0.7500 | 4 |
| waterfill h3 | 6/6 | 6/6 | 0/6 | 0% | 0.5938 | 3 |
| waterfill h4 | 6/6 | 6/6 | 2/6 | 33.33% | 0.4167 | 2 |

容量与量化代价：

| 合同 | mean tokens | mean bits/token | mean cumulative KL | mean cumulative TV |
|---|---:|---:|---:|---:|
| Decimal `1e-15` | 4.167 | 4.644 | approximately 0 | approximately 0 |
| fixed integer 16 | 4.167 | 4.644 | 0.008702 | 0.051126 |
| waterfill h3 | 4.667 | 3.756 | 0.020506 | 0.069110 |
| waterfill h4 | 4.000 | 4.692 | 0.004735 | 0.025257 |

## 假设判定

- H1：支持。4 个合同的 FP32 同精度控制全部 `6/6`，codec 接入与 portable context 实现有效。
- H2：否定。h4 与 Decimal 同为 `2/6`，没有更高；h3 为 `0/6`。
- H3：部分支持。h4 的偏差和容量均优于 h3，恢复率也更高，未观察到 h3 的预期容错优势。
- Anti-claim：支持。R024 的逐步 `15/32` 提升没有直接转化为消息级优势。

按预注册门禁，本轮为 `PARTIAL-GO`，原因仅是 waterfill h4 成功恢复 2 条完整消息；它没有达到 `GO-PILOT` 的至少 `3/6`，也没有比两个基线多 2 次。由于 BER `0.4167` 高于最佳基线 Decimal 的 `0.3854`，本轮同时判定 `NO-ADVANTAGE`。

## 失败分解

- 11/24 trials 抛出 `decoder sparse interval collapsed to zero`；
- 9/24 trials 返回完整或部分解码结果但 payload 错误；
- 4/24 trials 完整恢复；
- 没有观察到“observed token absent”类错误，说明 token-ID 排序和 portable PRF context 已排除两个上游混杂；
- Decimal 成功于 `(prompt1,seed0)`、`(prompt2,seed1)`；h4 成功于 `(prompt1,seed0)`、`(prompt2,seed0)`，成功集合仅部分重合。

## 科研解释

1. Observation：waterfill h4 可以改变可恢复轨迹，但总体成功率与 Decimal 相同。
2. Interpretation：粗质量减少部分概率边界漂移，却不能阻止任一关键步骤造成后续区间状态塌缩；h3 的额外量化偏差反而降低容量并增加失败。
3. Implication：继续降低 headroom 不会形成可靠端到端改进。逐步合同一致率不能作为消息成功率代理。
4. Next step：R026 设计固定 token 窗口的独立微帧，每个窗口重置区间与 PRF domain，并以认证标记失败窗口、用跨窗口纠错恢复 payload。该设计把单点失败限制在一个公开窗口，而不是污染整条消息。

## 结论边界

本轮只有 3 prompts × 2 seeds，不做显著性推断。结果证明“跨精度完整恢复可发生”，但不证明 waterfill 优于 Decimal，也不支持扩展到 Qwen。R026 在固定窗口机制通过前，不运行更大模型批量实验。

## 验证记录

- Pytest：133 项通过；
- Ruff：通过；
- Vue `vue-tsc -b`：通过；
- Vite production build：通过，3960 modules transformed；仅有现有 chunk 大小警告；
- GPU：24 条 FP32 encode / FP16 decode 轨迹完整运行。
