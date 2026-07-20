# R036-D6：Soft Reed-Solomon List Recovery

## Material Passport

- Origin Skills: `algorithm-designer`, `analyze-results`
- Origin Mode: retrospective mechanism test
- Origin Date: 2026-07-20
- Verification Status: INTERNAL-VERIFIED
- Version Label: `r036d6_soft_rs_list_recovery_v1`

## Purpose And Contract

D4/D5 每个 window 输出 byte 候选及合同成本，但不能逐窗口唯一化。D6 将已有 `RS(4,2)` codeword 视为一个包含 `2^16` 个合法码字的公开 codebook。对候选成本映射 `c_i(x)` 和预注册阈值 `tau=1`，定义

\[
s(C) = \left(
\sum_i \mathbf{1}[c_i(C_i)>\tau\ \text{or absent}],
\sum_{i:c_i(C_i)\le\tau} c_i(C_i)
\right).
\]

按字典序选择唯一最小 `s(C)` 的 payload；并列时明确返回失败。decoder 输入只有候选列表、成本和公开 RS 参数，不接收 expected payload 或其哈希。payload 哈希仅由审计脚本在解码结束后判断成功。

对 2-byte payload 完整枚举 `256^2=65,536` 个候选，时间复杂度 `O(2^(8m) * n)`，空间复杂度 `O(n)`。该 decoder 有限终止，但复杂度随 payload bytes `m` 指数增长；当前只能作为短块机制证明，不能直接用于 AEAD 长帧。

## Experiment

复用 R036-D5 的 `window=32, parity=2` 六个独立 trial，并报告 `tau={0,1,2,3}` 敏感性。阈值 1 是根据 D5 预先记录的低成本层选择，其他阈值不用于事后替换主结论。

```powershell
& '.venv\Scripts\python.exe' 'scripts\audit_rs_list_recovery.py' `
  --source 'outputs\R036_gpt2_bin_mass_raw_bytes.json' `
  --candidates 'outputs\R036D5_contract_list_decoder_k4_r1_b4096_q16.json' `
  --output 'outputs\R036D6_rs_list_recovery.json' `
  --variant 'window=32,parity=2' --cost-thresholds 0 1 2 3 `
  --enumeration-limit 65536 --run-label R036-D6
```

输出 13,783 bytes，SHA-256 `102b1d8caca4a59e2f2c49b1eed9fb519ab9a93af4a73755fb5d60e4ad172bf4`，24/24 阈值-trial 单元完成。

## Results

| 成本阈值 | 唯一正确恢复 | expected 在最优并列中 | 平均最优并列数 | 净 bits/token |
|---:|---:|---:|---:|---:|
| 0 | 2/6 | 5/6 | 86.33 | 0.125 |
| **1** | **4/6** | **5/6** | 43.50 | 0.125 |
| 2 | 3/6 | 4/6 | 43.83 | 0.125 |
| 3 | 3/6 | 4/6 | 43.83 | 0.125 |

主阈值 1 的逐 trial 结果：

| prompt/seed | 最优 score | expected score | 最优并列数 | 唯一正确 |
|---|---:|---:|---:|---:|
| 0/0 | (3,0) | (3,0) | 256 | 否，真实值在并列中 |
| 0/1 | (2,0) | (2,0) | 1 | 是 |
| 1/0 | (1,1) | (1,1) | 1 | 是 |
| 1/1 | (1,3) | (3,1) | 1 | 否，错误码字胜出 |
| 2/0 | (2,1) | (2,1) | 1 | 是 |
| 2/1 | (0,1) | (0,1) | 1 | 是 |

平均并列数受 prompt 0 / seed 0 的 256-way tie 支配，因此不能把 43.5 解释成典型 trial 的列表宽度。

## Findings

1. **Observation**：同一 D5 候选在不重新生成 token 的条件下，唯一 payload 恢复由 `0/6` 提高到 `4/6`。
   **Interpretation**：跨 window 的 RS code constraint 确实把合同成本转化为消息级判别力；提升不是更大 beam 或 expected-payload oracle 造成的。
   **Implication**：precision-hardened PSS 的正确抽象是带软信息和擦除的 list-recovery channel。

2. **Observation**：阈值从 1 增至 2/3 后成功率降至 `3/6`。
   **Interpretation**：纳入更多高成本合同会提高错误码字的偶然匹配，候选覆盖与唯一判别之间存在明确 Pareto trade-off。
   **Implication**：不能把“候选越宽越安全”当作恢复目标；必须联合报告真值覆盖和错误码字竞争。

3. **Observation**：两个失败分别是大规模并列和错误码字胜出。
   **Interpretation**：四个 RS 坐标不足以给 65,536 个 payload 提供足够独立约束。
   **Implication**：下一步固定 `tau=1`，增加 RS parity / 坐标数，而不是继续扫阈值或扩大 beam。

## Decision

阶段判定为 **MESSAGE-RECOVERY-PARTIAL-GO (4/6) / R036-GATE-NOT-MET**。这已经是相对 D4/D5 的真实消息级提升，但低于跨精度至少 `5/6` 的预注册门槛，R037 AEAD 继续暂停。

R036-D7 使用 `RS(12,2)`，即 2-byte payload 加 10 parity bytes，窗口固定 32、成本阈值固定 1。净容量将从 0.125 降到 `16/(12*32)=0.0417 bit/token`；该代价必须与恢复率一起报告。
