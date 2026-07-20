# R036-D4：在线 Contract-List 候选恢复

## Material Passport

- Origin Skill: `analyze-results`
- Origin Mode: result audit
- Origin Date: 2026-07-20
- Verification Status: INTERNAL-VERIFIED
- Version Label: `r036d4_online_contract_list_v1`

## Experiment

复用 R036 的 24 条 GPT-2 FP32 编码 / FP16 重放 token 流，使用 `K=4`、bin 半径 `r=1`、beam width `4096` 的在线合同列表解码器。payload 哈希只在解码完成后评估候选覆盖，不参与候选生成、排序或选择。

执行命令：

```powershell
& '.venv\Scripts\python.exe' 'scripts\audit_contract_list_decoder.py' `
  --input 'outputs\R036_gpt2_bin_mass_raw_bytes.json' `
  --output 'outputs\R036D4_contract_list_decoder_k4_r1_b4096.json' `
  --run-label R036-D4 --top-k 4 --bin-radius 1 `
  --beam-width 4096 --enumeration-limit 1000000
```

输出文件 `outputs/R036D4_contract_list_decoder_k4_r1_b4096.json` 为 282,957 bytes，SHA-256 为 `a96a521736aa348183fe33c1b2ed6cc6ad5f77878aa27e317ac3f117e3d3faba`。24/24 trial 完成，耗时 906.6 秒。

## Raw Results

| 变体 | trial | 全部真实 symbol 在列表 | expected payload 已验证在列表 | 唯一 payload 恢复 | 平均最大 window 候选 | 总剪枝状态 |
|---|---:|---:|---:|---:|---:|---:|
| w16/p0 | 6 | 3/6 | 3/6 | 0/6 | 167.33 | 1,351,988 |
| w16/p2 | 6 | 0/6 | 0/6 | 0/6 | 167.33 | 3,543,984 |
| w32/p0 | 6 | **5/6** | **5/6** | 0/6 | 174.50 | 1,647,023 |
| w32/p2 | 6 | 1/6 | 0/6 | 0/6 | 182.17 | 4,602,311 |

`w32/p2` 的 1 个全 symbol 覆盖 trial 的候选笛卡尔积为 682,865,568，超过显式枚举上限，因此表中的 expected payload `0/6` 表示“未验证”，不能解释成候选中确定不存在。

在 `w32/p0` 的 5 个覆盖成功 trial 中，10 个真实字节的候选 rank 为：

```text
[1,1], [1,1], [3,21], [1,1], [8,1]
```

rank 中位数为 1，最大值为 21；对应路径成本为 `[0,0]`、`[0,0]`、`[1,3]`、`[1,0]`、`[1,0]`。但每个 trial 的 payload 候选组合仍有 20,265 至 43,442 个，无法在不知道真实 payload 的条件下唯一选择。

## Findings

1. **Observation**：`w32/p0` 把原始跨精度完整恢复从 R036 的 `2/6` 提高为正确 payload 候选覆盖 `5/6`，但唯一恢复仍为 `0/6`。
   **Interpretation**：有限局部合同确实能包住多数 FP32 真路径，但覆盖不等于解码；当前实验不能报告 `5/6` 消息成功率。
   **Implication**：R036-D3 的 oracle 结果已部分转化为可执行 decoder，但尚未满足 raw-byte GO。

2. **Observation**：所有 trial 的 active states 都触达 beam width 4096，四个变体共剪掉 11,145,306 个状态。
   **Interpretation**：当前状态键保留完整 `temp0` 历史，把对未来具有相同残余符号映射的路径视为不同状态，造成组合爆炸和真路径剪枝。
   **Implication**：继续扩大 beam 只会迅速增加时间和内存，不能解决唯一性。

3. **Observation**：覆盖成功时真实 symbol 通常是最低成本候选，但仍存在 rank 21；只取 top-1 会损失正确性。
   **Interpretation**：support-rank 与 bin-offset 成本具有信息，但不是充分的似然或认证约束。
   **Implication**：下一阶段应先做状态等价压缩和 symbol-stratified pruning；候选唯一化仍需要独立、公开的冗余约束，不能使用 payload 哈希 oracle。

## Decision

阶段判定为 **CANDIDATE-COVERAGE-GO / UNIQUE-DECODE-NO-GO**。

R037 AEAD 继续暂停。R036-D5 将把状态表示改为“当前残余索引到初始 byte 的双射”，按该映射做等价状态合并，并在需要剪枝时对 256 个初始 symbol 分层保留。该变换必须先通过穷举等价性单元测试；若候选覆盖提高但仍不唯一，下一步再加入显式 window checksum/suffix，并把其冗余计入净容量。
