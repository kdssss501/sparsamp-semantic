# R059 有界决策集合独立确认合同

## 目标与冻结来源

R059 只回答一个问题：R058 在已暴露 seed-0 上取得的 `10/10`、55.72% 完整轨迹负载，能否在从未进入 R055-R058 开发过程的 seed 1、2 上保持可靠性和相对 R056 的负载优势。

- 冻结实现提交：`33d14df`。
- R058 结果签名：`ac2e945cfdcee73f043013b6c645901fb32c6e33532afa4bbe8c7b09cda9e069`。
- bin shift 半径：1。
- 同支持质量半径：1984 counts。
- R056 支持 gap 对照：1 bin。
- 数据：R044 的 20 个 prompt × seed `{1,2}`，共 40 trial。

## GPU 轨迹生成

使用现有 `audit_dual_barrier_contracts.py`，顺序加载 FP16 与 BF16，不同时驻留两个模型。输出每完成一个 trial 即原子替换 checkpoint；配置签名不一致时拒绝续跑，重复完成命令不会重跑已完成 trial。

```powershell
& '.venv\Scripts\python.exe' scripts/audit_dual_barrier_contracts.py `
  --source outputs/R044_qwen_replay_scale.json `
  --output outputs/R059_qwen_independent_trace.json `
  --run-label R059 `
  --prompt-indices 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 `
  --seeds 1 2
```

中断后执行完全相同的命令继续；只有显式 `--fresh` 才归档并重置进度。

## 冻结分析与验收

分析器只从 R058 文件读取上述三个阈值，对 R059 每条参考轨迹构造有界决策集合，再读取 BF16 比较字段评估覆盖。对照为相同 R059 轨迹上的 R056 双屏障，禁止引用 seed-0 固定字节数替代同数据比较。

- `confirmation_strong_go`：40/40 trial 精确覆盖，且合并负载低于同数据 R056。
- `confirmation_pilot_go`：每个 seed 至少 18/20 trial 精确覆盖，且合并负载低于同数据 R056。
- 其他均为 `no_go`。

必须报告每个 seed 与合并结果、false-safe step、支持/质量错误类型、证书密度、完整轨迹比例、R056 比例、tail 告警和平均枚举合同数。不得在看到 seed-1/2 标签后改变半径、prompt 子集或验收门槛。

## 资源与主张边界

实验使用一张 RTX 3060 Laptop 6GB GPU，轨迹数量是 R055 的两倍。该确认仍是同一物理 GPU 上 FP16/BF16 的 seed 外推，不构成跨硬件认证；但若通过，可把 R058 从回顾性机制信号升级为独立随机种子确认的 pilot 贡献。
