# R018 Paired Entropy Rescue V2

日期：2026-07-17

## 方法

- 固定与 adaptive 配置共享相同 PRF context，首次救援前 token 前缀严格配对。
- 基础 temperature 0.8；完整分布熵连续 8 步低于 1.0 后切换到 1.4。
- 512-bit payload，3 prompts，Fixed-16 与 Verified-RRC，800-token 预算。

## 结果

| Prompt | Codec | 固定基线 | Rescue V2 | 公共前缀 | Rescue fraction | Candidate mean | Token/s |
|---:|---|---|---|---:|---:|---:|---:|
| 0 | Fixed-16 | 800 未完成 | 420 完成 | 381 | 8.1% | 61.9 | 11.15 |
| 0 | RRC | 415 完成 | 570 完成 | 36 | 22.6% | 137.5 | 10.93 |
| 1 | Fixed-16 | 800 未完成 | 555 完成 | 444 | 7.6% | 25.5 | 15.16 |
| 1 | RRC | 458 完成 | 482 完成 | 132 | 1.7% | 8.2 | 15.73 |
| 2 | Fixed-16 | 465 完成 | 469 完成 | 371 | 0.4% | 6.0 | 15.12 |
| 2 | RRC | 800 未完成 | 499 完成 | 284 | 11.6% | 120.5 | 11.98 |

- 完成率从固定温度的 3/6 提高到 6/6。
- 6/6 token-ID 精确解码。
- 平均 embedded tokens 为 499.2，平均 rescue fraction 8.7%，平均 13.35 token/s。
- 2/6 出现 Token Ambiguity；固定基线为 0/6，但两批输出轨迹不同，样本不足以做比例结论。

## 解释

V2 在三个原失败样本上都有效，证明公开高温介入可以逃离部分低熵重复状态。但它不是单调
增益：RRC prompt 0 从 415 增至 570 tokens。救援温度扩大 top-p 候选集合，在两个 RRC
样本中平均候选数达到 120-138，导致 Decimal codec 和候选处理变慢。

## 结论与下一步

V2 通过可靠性 smoke gate，但不能声称无代价加速。下一候选应采用短脉冲救援：高温最多
持续 N 步，熵恢复后立即冷却，减少候选数和分布偏移。论文实验还必须加入 adaptive native
baseline、重复率、困惑度和 steganalysis，最终规模至少 20 prompts x 3 seeds。
