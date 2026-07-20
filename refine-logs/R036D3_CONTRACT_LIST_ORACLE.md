# R036-D3：Contract-List Oracle

## Material Passport

- Origin Skill: experiment-agent
- Origin Mode: run
- Origin Date: 2026-07-20
- Verification Status: UNVERIFIED
- Version Label: r036d3_contract_list_oracle_v1

## Result

GPT-2 FP32 reference / FP16 replay，复用 R036 的 24 条 token 流。测试
`K={2,4,8,16}`、量化 bin 半径 `r={0,1,2}`；`q=0.5`，所以 `r=1` 表示相对 logit
邻域不超过 0.5。完整输出：`outputs/R036D3_contract_list_oracle.json`，935,681 bytes，
SHA-256 `EF710A2928A3FA9B2087E25FAD4372241867DF529B9FBC34AB32071B098C4A73`。

| 配置 | w16/p0 | w16/p2 | w32/p0 | w32/p2 | 保守单步 beam 上界 |
|---|---:|---:|---:|---:|---:|
| K=2,r=0 | 0/6 | 0/6 | 0/6 | 0/6 | 1 |
| K=4,r=0 | 3/6 | 0/6 | 0/6 | 0/6 | 6 |
| K=4,r=1 | **6/6** | **6/6** | **6/6** | **5/6** | 54 |
| K=8,r=1 | **6/6** | **6/6** | **6/6** | **6/6** | 252 |

24 条轨迹的最小需求分布为：18 条 `K=3,r=1`，3 条 `K=3,r=0`，2 条
`K=4,r=1`，1 条 `K=6,r=1`。所有轨迹都能在 FP16 top-16 下完整继续，且所需 bin
半径最大为 1。

## Decision

判定为 **ORACLE-GO / DECODER-UNVERIFIED**。主要失效机制是 top-2 边界排名交换，辅以
一个量化 bin 的局部漂移；不需要无界 support 或大半径。下一步实现 `K=4,r=1` 的
Contract-List decoder，并保留 `K=8,r=1` 作为覆盖上限对照。

该结果只证明正确 FP32 合同存在于有限 FP16 假设包络，尚未证明在线 beam 剪枝能保留
正确路径，也未证明 raw-byte 或 AEAD 消息恢复。正式 GO 门槛仍为同精度 `6/6`、跨精度
至少 `5/6`。
