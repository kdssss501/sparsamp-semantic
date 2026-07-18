# R024 Support-Adaptive Integer Mass

## Material Passport

- Schema：ARS Material Passport 9 compatible local record
- Stage：experiment-agent / plan -> run -> validate
- Verification Status：REPRODUCED, GO-MECHANISM
- Date：2026-07-18
- Source：本地源码、GPT-2 FP32/FP16 共享前缀实验
- External upload：无

## 研究问题

在 R023 的 token-ID 规范顺序已经把同支持步骤的顺序固定后，支持可行的粗粒度整数质量能否吸收逐 token 概率漂移，并在可接受的 `KL(Q||R)` 与 TV 代价下提高精确合同一致率？

## 独立变量

| 变量 | 取值 |
|---|---|
| 候选顺序 | 固定 `token_id` |
| headroom `h` | `0,1,2,3,4,6,8` |
| 支持策略 | `base`, `waterfill` |
| 固定质量基线 | Decimal `1e-15`, integer `16,20,24,28,32` |

动态位宽为 `b_t=max(1,ceil(log2 K_t))+h`。所有动态合同保持支持，不运行删除尾部候选的版本。

## 因变量

1. 32 步精确合同一致数；
2. 20 个同支持步骤中的精确一致数；
3. 有效位宽的均值、最小值、最大值；
4. reference FP32 的逐步 `KL(Q||R)` 均值与最大值；
5. reference FP32 的逐步 TV 均值与最大值；
6. 候选数 `K` 的均值、最小值、最大值；
7. 候选顺序一致、候选集合一致和平均 Jaccard。

## 控制变量

- 模型：本地 GPT-2；
- reference：FP32；replay：FP16；
- prompt、32-step top-1 共享前缀、`top_p=0.95`、temperature `1.0`；
- `candidate_order=token_id`；
- 模型 revision、tokenizer、seed 和系统提示词不变。

## 假设

- H1：至少一个动态合同的精确一致步数高于 R023 的 `10/32`，预注册目标为不少于 `14/32`。
- H2：相同 headroom 下，waterfill 的平均 `KL(Q||R)` 低于或等于 legacy base。
- H3：headroom 增大时 KL/TV 总体下降，但精确合同一致率可能下降，形成可观测 Pareto 前沿。
- Anti-claim：任何超过 10/32 的结果若依赖过大分布偏差，不构成可靠隐写改进。

## 决策门禁

- GO：精确合同至少 `14/32`，且 mean KL `<=0.01 nat/step`、mean TV `<=0.05`。
- PARTIAL-GO：精确合同至少 `14/32` 但偏差超门限，或精确合同为 `11-13/32` 且偏差受控。
- NO-GO：所有动态合同仍为 `10/32`，或提升完全来自支持删除。

`20/32` 是当前候选集合一致率给出的结构上限，不能把它当成预期必达值。

## 消融优先级

| 优先级 | 消融 | 审稿问题 |
|---:|---|---|
| 1 | waterfill vs base | 改进来自更粗质量还是更合理的支持投影？ |
| 1 | `h=0..4` | 最小可行质量附近是否存在容错/偏差 Pareto 点？ |
| 2 | `h=6,8` | 增加精度后是否回到 R022 的高敏感区？ |
| 3 | 固定 16-32 bit | 与已发表 R022/R023 基线是否一致？ |

暂不运行 Qwen、消息级恢复、top-k 或允许支持丢失的消融。若 GPT-2 共享前缀合同没有通过门禁，这些实验不会提供可解释增量。

## 预计计算

所有合同在同一批 FP32/FP16 snapshots 上离线计算，只需要一次 32-step reference 和一次 replay，预计与 R023 相同，少于 1 分钟 GPU 时间。

## 可复现命令

```powershell
.\.venv\Scripts\python.exe scripts\audit_precision_contract.py `
  --model models\gpt2 `
  --reference-dtype float32 `
  --replay-dtype float16 `
  --tokens 32 `
  --candidate-order token_id `
  --mass-bits 16 20 24 28 32 `
  --support-headroom-bits 0 1 2 3 4 6 8 `
  --support-strategies base waterfill `
  --output outputs\R024_gpt2_support_adaptive_mass.json
```

## 结果

原始结果：`outputs/R024_gpt2_support_adaptive_mass.json`。输出目录由 Git 忽略，提交保存审计代码、预注册和结果摘要。

固定基线保持 R023 结果：Decimal 与 integer `16-32 bit` 均为 `10/32`。候选顺序一致 `20/32`，候选集合一致 `20/32`，说明实验轨迹与 R023 对齐。

候选数统计：均值 `180.125`，最小 `1`，最大 `2420`。因此最小支持可行位宽随步骤变化，headroom 0 的有效位宽范围为 `1-12 bit`。

| 合同 | 精确步数 | mean bits | mean KL | mean TV | 门禁 |
|---|---:|---:|---:|---:|---|
| base h0 | 17/32 | 5 | 0.429279 | 0.317228 | PARTIAL，偏差过大 |
| base h1 | 15/32 | 6 | 0.118832 | 0.159457 | PARTIAL，偏差过大 |
| base h2 | 15/32 | 7 | 0.041357 | 0.080287 | PARTIAL，偏差过大 |
| base h3 | 13/32 | 8 | 0.015113 | 0.040972 | NO-GO |
| base h4 | 14/32 | 9 | 0.004964 | 0.020122 | GO |
| base h6 | 12/32 | 11 | 0.000416 | 0.005019 | PARTIAL |
| base h8 | 13/32 | 13 | 0.000033 | 0.001276 | PARTIAL |
| waterfill h0 | 18/32 | 5 | 0.380171 | 0.297922 | PARTIAL，偏差过大 |
| waterfill h1 | 16/32 | 6 | 0.090093 | 0.118780 | PARTIAL，偏差过大 |
| waterfill h2 | 14/32 | 7 | 0.024538 | 0.044557 | PARTIAL，KL 过大 |
| waterfill h3 | 15/32 | 8 | 0.005717 | 0.015272 | **GO** |
| waterfill h4 | 14/32 | 9 | 0.001061 | 0.005074 | **GO** |
| waterfill h6 | 12/32 | 11 | 0.000067 | 0.001001 | PARTIAL |
| waterfill h8 | 11/32 | 13 | 0.000003 | 0.000233 | PARTIAL |

## 假设判定

- H1：支持。最佳受控配置 `waterfill+h3` 达到 `15/32`，相对 R023 增加 5 步、15.625 个百分点，或 50% 相对提升。
- H2：支持。waterfill 在全部 7 个 headroom 上降低 mean KL，相对 base 的降幅为 `11.44%-91.19%`；mean TV 也全部下降。
- H3：支持。headroom 增大时 KL/TV 单调下降，而精确一致率非单调，形成明确 Pareto 权衡。
- Anti-claim：支持。`h0-h2` 的高恢复率伴随明显分布偏差，未被选为推荐合同。

## Pareto 与推荐

机制级推荐为 `waterfill+h3`：精确合同 `15/32`、mean KL `0.005717`、mean TV `0.015272`，有效位宽均值 `8`、范围 `4-15`。若更重视低偏差，可选 `waterfill+h4`：精确合同降至 `14/32`，但 mean KL 降至 `0.001061`。

`waterfill+h3` 的精确步骤为：`2,11,13,14,16,17,19,20,22,23,25,26,28,29,31`。5 个同支持步骤仍因概率合同不同而失败；12 个候选 churn 步骤全部失败。因此当前上限仍由支持稳定性控制。

## 结论边界

本轮 `GO` 仅表示支持自适应粗质量在单 prompt、单条 32-step GPT-2 轨迹上通过预注册机制门禁。它不证明：

- 完整消息可在 FP32 编码、FP16 解码间恢复；
- 多 prompt、多 seed 结果稳定；
- Qwen 的中文语义文本获得同样提升；
- 量化偏差足以抵抗现实隐写分析器；
- 已达到原论文 SparSamp 的零偏差性质。

下一步 R025 应把 `waterfill+h3/h4` 接入真实 codec 配置，先做 GPT-2 消息级跨精度恢复和多 prompt 扩展。若完整消息仍因任一步合同失败而无法恢复，则转向纠错/同步检查点，而不能用逐步一致率替代消息成功率。

## 验证记录

- Pytest：126 项通过；
- Ruff：通过；
- GPU：GPT-2 FP32 reference / FP16 replay，32 步完整运行；
- 固定质量基线与 R023 完全一致，支持实验轨迹复现。
