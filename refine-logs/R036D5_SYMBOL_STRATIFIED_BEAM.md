# R036-D5：残余映射压缩与 Symbol-Stratified Beam

## Material Passport

- Origin Skills: `algorithm-designer`, `analyze-results`
- Origin Mode: algorithm audit
- Origin Date: 2026-07-20
- Verification Status: INTERNAL-VERIFIED
- Version Label: `r036d5_symbol_stratified_beam_v1`

## Algorithm

对每条尚未收敛的合同路径，保存有序残余映射 `M_t[j]`：当前残余索引 `j` 对应的初始 byte。若一次观测得到边界整数 `temp0` 和新宽度 `n_{t+1}`，则

\[
M_{t+1}[j] = M_t[(\operatorname{temp0}+j) \bmod n_t],
\quad 0 \le j < n_{t+1}.
\]

未来转移只依赖 `M_t`（其长度即 `n_t`）和公开的下一步合同，因此相同映射的状态可以保留最低成本后严格合并。该等价性通过逐索引模拟编码更新的穷举测试验证。

beam 需要剪枝时，对 256 个初始 byte 各保留至少 16 条包含该 byte 的最低成本状态；剩余位置按全局成本补齐。配置为 `beam_width=4096`、`symbol_quota=16`。

时间复杂度仍受每步合同分支和 beam 限制，上界为 `O(W * B * C * n)`，其中复制残余映射带来 `n` 因子；空间为 `O(B * n)`。该实现是有限终止的 bounded search，不具有“真实路径一定在 top quota”保证。

## Experiment

复用 R036 的 24 条 GPT-2 FP32 编码 / FP16 重放流：

```powershell
& '.venv\Scripts\python.exe' 'scripts\audit_contract_list_decoder.py' `
  --input 'outputs\R036_gpt2_bin_mass_raw_bytes.json' `
  --output 'outputs\R036D5_contract_list_decoder_k4_r1_b4096_q16.json' `
  --run-label R036-D5 --top-k 4 --bin-radius 1 `
  --beam-width 4096 --symbol-quota 16 --enumeration-limit 1000000
```

输出为 383,649 bytes，SHA-256 `39a349760f2fe6359d9ac8acc55782d17c62483fa8c1850c167b6daa517012ca`。24/24 trial 原子保存并完成；首次进程达到 20 分钟工具时限后，checkpoint 已包含 24 条，恢复命令验证没有重复运行。

## Results

| 变体 | D4 真实 symbol 全覆盖 | D5 真实 symbol 全覆盖 | D5 唯一 payload | D4/D5 平均最大候选 | D5 合并状态 | D5 剪枝状态 |
|---|---:|---:|---:|---:|---:|---:|
| w16/p0 | 3/6 | 3/6 | 0/6 | 167.33 / 230.67 | 6,350,675 | 1,167,943 |
| w16/p2 | 0/6 | 0/6 | 0/6 | 167.33 / 235.17 | 12,053,667 | 3,238,820 |
| w32/p0 | **5/6** | **5/6** | 0/6 | 174.50 / 234.83 | 13,546,264 | 1,498,033 |
| w32/p2 | 1/6 | 1/6 | 0/6 | 182.17 / 235.00 | 28,117,816 | 4,568,226 |

`w32/p0` 的 5 个覆盖 trial 中，真实 byte rank 仍为 `[1,1]`、`[1,1]`、`[3,21]`、`[1,1]`、`[8,1]`，与 D4 完全相同。按候选成本截断：

| 成本阈值 | 真实 byte 覆盖 | 平均列表宽度 | 最大列表宽度 |
|---:|---:|---:|---:|
| 0 | 7/12 | 0.75 | 1 |
| 1 | **10/12** | **8.33** | 19 |
| 2 | 10/12 | 31.33 | 60 |
| 3 | 11/12 | 71.92 | 129 |

上述阈值统计的 12 个 byte 来自 6 个 trial，不可当作 12 个独立实验单元，也不用于声称显著性。

## Findings

1. **Observation**：严格状态合并累计消除了约 6007 万条重复扩展，但所有变体的真实覆盖数与 D4 完全相同。
   **Interpretation**：完整边界历史确有大量冗余，但主要正确性瓶颈是有限 quota 下的路径排序，而不是状态键缺少等价合并。
   **Implication**：状态压缩是正确实现改进，不是消息恢复改进。

2. **Observation**：symbol-stratified beam 保留了更多高成本候选，却没有补回第 6 个 `w32/p0` trial，且运行时间高于 D4。
   **Interpretation**：真实路径不保证位于每个 symbol 的前 16 条最低启发式成本状态；扩大 quota 仍是无证据的算力扩张。
   **Implication**：停止继续扩大 beam/quota。

3. **Observation**：成本不高于 1 的列表平均只有 8.33 个 byte，同时覆盖 10/12 个真实 byte。
   **Interpretation**：合同成本可作为带擦除的软信息；错误候选空间不应逐窗口强行唯一化，而应由跨窗口 code constraint 联合恢复。
   **Implication**：下一阶段使用成熟 RS codeword 的穷举 list-recovery smoke，在同一成本函数下报告唯一最优、真实 rank、码率和错误界。

## Decision

判定为 **STATE-COMPRESSION-GO / RECOVERY-NO-GO**。R037 AEAD 继续暂停。

R036-D6 不再把 parity 仅当作传统硬判决纠错，而把长度受控的 Reed-Solomon codebook 作为 list-recovery 约束。对 2-byte smoke 可完整枚举 `2^16` 个 payload；该方法对 payload 长度呈指数复杂度，只有在后续分块或代数解码替代后才能扩展，论文中必须明确这一限制。
