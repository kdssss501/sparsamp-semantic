# R056 分层双屏障证书研究合同

## 研究问题

R055 的 20-trial pilot 在不查看逐步特征阈值的情况下发现：30 次 FP16/BF16 修正中，27 次属于 top-2 支持变化，3 次属于支持不变时的整数质量迁移。R056 检验把这两类错误分层后，能否将 R054 的高成本单边界证书转化为低于完整轨迹一半的参考端证书。

## 冻结数据划分

- 数据源：`outputs/R055_qwen_dual_barrier_trace.json`。
- 校准集：偶数 prompt 索引，共 10 条 seed-0 轨迹。
- 留出集：奇数 prompt 索引，共 10 条 seed-0 轨迹。
- 每道屏障使用 `alpha=0.10`，即十个 prompt 分数的最大值。
- 两道屏障分别校准。十个校准 prompt 取最大值时，每道屏障的有限样本 prompt 覆盖不低于 10/11；在 prompt 级可交换性假设下，两道屏障的 union bound 联合覆盖不低于 9/11。

## 双屏障构造

支持屏障的 prompt 分数，是该 prompt 所有 `support_flip` 修正位置中参考端 rank-2/rank-3 量化 logit bin gap 的最大值；没有该类修正则为零。留出位置的 gap 小于或等于校准阈值时，记录参考 token。

质量屏障的 prompt 分数，是该 prompt 所有 `mass_flip` 修正位置中参考端 CDF 边界 slack 加一的最大值；没有该类修正则为零。留出位置的 slack 严格小于校准半径时，记录参考 token。

双屏障证书取两类位置的并集。构造时只读取 `reference_trace` 中的 FP16 top-16 bins、top-2 counts、公开 prompt 和 seed，并独立重算 PRF 边界裕量；不读取 `comparison` 中的 BF16 支持、counts、选择或修正位置。BF16 信息只在证书冻结后用于评估 false-safe。

## 同数据基线与判据

单边界基线在同一偶数校准集上，把所有修正混在一起校准一个 slack 半径，并在相同奇数留出集评估。这样隔离“错误分层”贡献，不借用 R054 不同 seed 规模的阈值。

- Strong GO：留出 10/10 精确覆盖，证书负载低于完整轨迹 50%，且不超过单边界基线负载的 50%。
- Pilot GO：至少 9/10 精确覆盖，证书负载低于完整轨迹 50%，且低于单边界基线。
- NO-GO：不满足 Pilot GO。

同时报告证书密度、false-safe、支持/质量屏障各自触发数、目标特定 SPRC 膨胀、完整轨迹比例和单边界比例。结果仅适用于同一 GPU 的 FP16/BF16 留出研究；在扩展到三个 seed 前不能形成稳定方法主张。
