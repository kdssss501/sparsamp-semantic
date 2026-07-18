# R023 Canonical Candidate Order V1

## Material Passport

- Schema：ARS Material Passport 9 compatible local record
- Stage：experiment-agent / plan -> run -> validate
- Verification Status：REPRODUCED, PARTIAL-GO
- Date：2026-07-18
- Source：本地源码、单元测试、GPT-2 FP32/FP16 共享前缀实验
- External upload：无

## 研究问题

R022 发现 GPT-2 FP32 -> FP16 的 32 个共享前缀步骤中，只有 14 步候选顺序一致，但有 20 步候选集合一致。其中 6 步失败来自“集合相同、概率排名不同”。R023 检验：top-p 支持选定后按稳定 token ID 排列区间，能否消除这 6 步顺序故障，并提高精确概率合同一致率。

## 假设

- H1：在候选集合相同的步骤上，`token_id` 合同的候选顺序一致率为 100%。
- H2：32 步整体候选顺序一致数由 R022 的 14/32 提升到候选集合一致上限 20/32。
- H3：至少一个被审计概率合同的精确一致步数由 10/32 提升到不少于 14/32。
- Anti-claim：规范顺序不能修复 12/32 的 top-p 候选 churn，也不能单独保证跨精度消息恢复。

## 因果隔离

- 模型、prompt、top-p、温度、共享 top-1 前缀和概率质量位宽保持与 R022 相同；
- 共享前缀按原始概率 `rank=0` 选择，不按候选数组第一个元素选择；
- 唯一处理变量为 `candidate_order`：R022 使用 `probability`，R023 使用 `token_id`；
- 支持选择发生在规范排序之前，因此排序不应改变候选集合或 source mass。

## 决策门禁

- GO：候选顺序一致达到 20/32，且至少一个精确合同达到 14/32；随后研究支持稳定合同。
- PARTIAL-GO：顺序一致达到 20/32，但精确合同低于 14/32；说明顺序机制正确，但概率漂移仍主导，不进入消息级 Qwen 扩展。
- NO-GO：顺序一致未达到候选集合一致步数；优先审计 token ID 稳定性、排序接入点或实验轨迹。

## 当前实现

- `HuggingFaceConfig.candidate_order`：`probability | token_id`；
- top-p 支持和归一化完成后重排，token 概率和原始 rank 保持不变；
- 非默认合同写入 `context_id` 和 snapshot metadata；
- CLI、REST API、completion pilot 与 Vue 编解码参数完整接入；
- 旧 artifact 缺失字段时恢复为 `probability`；
- 审计输出 schema 升级为 `sparsamp-precision-contract-audit-v2`，增加结构一致性汇总。

## 预注册指标

1. 候选顺序一致步数；
2. 候选集合一致步数；
3. 平均候选 Jaccard；
4. Decimal `1e-15` 精确合同一致步数；
5. integer `b={16,20,24,28,32}` 精确合同一致步数；
6. 首个共享前缀 token 从支持中消失的步骤；
7. 公共候选最大概率差和 source mass 差。

## 复杂度与边界

- 每步额外时间 `O(K log K)`，空间 `O(K)`；
- 规范排序不改变目标 token 概率，因此理想区间采样下容量和目标分布不变；
- 整数质量的余数平局可能因候选位置变化而改变 `1/2^b` 量级的具体计数分配；
- 未经 GPU 对照前，不报告性能提升百分比，不进入 Qwen 消息级恢复结论。

## 可复现命令

```powershell
.\.venv\Scripts\python.exe scripts\audit_precision_contract.py `
  --model models/gpt2 `
  --reference-dtype float32 `
  --replay-dtype float16 `
  --tokens 32 `
  --candidate-order token_id `
  --mass-bits 16 20 24 28 32 `
  --output outputs/R023_gpt2_canonical_order.json
```

## 实验结果

原始结果：`outputs/R023_gpt2_canonical_order.json`。该目录由 Git 忽略，提交中只保存审计代码、理论合同和结果摘要。

| 指标 | R022 probability order | R023 token-ID order | 变化 |
|---|---:|---:|---:|
| 候选顺序一致 | 14/32 (43.75%) | 20/32 (62.50%) | +6 步，+18.75 pp |
| 候选集合一致 | 20/32 (62.50%) | 20/32 (62.50%) | 0 |
| Decimal `1e-15` 精确合同 | 10/32 (31.25%) | 10/32 (31.25%) | 0 |
| Integer 16-bit 精确合同 | 10/32 (31.25%) | 10/32 (31.25%) | 0 |
| Integer 20-bit 精确合同 | 10/32 (31.25%) | 10/32 (31.25%) | 0 |
| Integer 24-bit 精确合同 | 10/32 (31.25%) | 10/32 (31.25%) | 0 |
| Integer 28-bit 精确合同 | 10/32 (31.25%) | 10/32 (31.25%) | 0 |
| Integer 32-bit 精确合同 | 10/32 (31.25%) | 10/32 (31.25%) | 0 |

结构指标：

- 平均候选 Jaccard：`0.9941238`；
- 首个共享前缀 token 支持丢失：无；
- 最大公共候选概率差：均值 `0.0012523`，中位数 `0.0007949`，最大 `0.0061921`；
- 由规范排序修复的步骤：`1,2,4,5,7,8`；
- 上述 6 步中转为精确合同一致的步骤：0；
- 候选集合相同但合同不精确的步骤：`1,2,4,5,7,8,11,13,16,19`。

## 假设判定

- H1：支持。候选集合相同时，token-ID 顺序全部一致，达到 20/20。
- H2：支持。整体顺序一致由 14/32 提升到预注册上限 20/32。
- H3：否定。所有精确合同仍为 10/32，没有达到不少于 14/32 的门禁。
- Anti-claim：支持。12 个候选 churn 步骤仍失败，且顺序修复没有转化为概率合同修复。

按照预注册规则，本轮判定为 `PARTIAL-GO`：规范候选顺序是正确且必要的结构合同，但当前 FP32/FP16 重放的主瓶颈已明确转为逐 token 概率漂移和 top-p 支持 churn。R023 不进入 Qwen 消息级跨精度恢复实验，也不报告端到端性能提升。

## 科研含义

1. Observation：顺序一致率提高 18.75 个百分点，精确合同一致率不变。
2. Interpretation：原先 6 个“顺序故障”步骤也同时存在大于当前量化格宽的概率漂移；排序是并发故障之一，而非唯一故障。
3. Implication：后续不能继续优化排序，也不能提高整数位宽；更高位宽只会让合同对漂移更敏感。
4. Next step：R024 扫描满足 `2^b >= K` 的更粗整数质量位宽，并同时记录候选数、支持保持可行性、量化 KL/TV 与精确合同一致率。只有粗量化能提高同支持步骤的合同一致率，才进入消息级验证。

## 验证记录

- Pytest：122 项通过；
- Ruff check：通过；本轮 8 个 Python 文件格式检查通过；
- Vue `vue-tsc -b`：通过；
- Vite production build：通过，3960 modules transformed；仅有现有 chunk 大小警告；
- GPU：NVIDIA GeForce RTX 3060 Laptop GPU，GPT-2 FP32 reference / FP16 replay，32 步完整运行。
