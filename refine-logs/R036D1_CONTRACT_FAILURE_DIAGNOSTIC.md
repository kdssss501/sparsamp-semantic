# R036-D1：Bin-Mass 消息失败机制诊断

## Material Passport

- Origin Skill: experiment-agent
- Origin Mode: run
- Origin Date: 2026-07-20T07:20:56Z
- Verification Status: UNVERIFIED
- Version Label: r036d1_contract_failure_diagnostic_v1

## Experiment Result

- **ID**: R036-D1
- **Type**: simulation
- **Status**: completed
- **Working Directory**: `C:\Users\41462\Documents\隐写`
- **Duration**: 204.5 seconds
- **Exit Code**: 0
- **GPU**: NVIDIA GeForce RTX 3060 Laptop GPU, 6 GB
- **Model**: local GPT-2
- **Precision**: FP32 reference / FP16 replay
- **Independent unit**: 每个变体 3 prompts × 2 payload seeds，共 6 个单元

执行命令：

```powershell
& '.venv\Scripts\python.exe' 'scripts\audit_bin_mass_failure_modes.py' `
  --input 'outputs\R036_gpt2_bin_mass_raw_bytes.json' `
  --output 'outputs\R036D1_gpt2_failure_modes.json' `
  --run-label R036-D1
```

### Output Files

| File | Size | SHA-256 |
|---|---:|---|
| `outputs/R036_gpt2_bin_mass_raw_bytes.json` | 72,307 bytes | `F164C4C118598A7C59A67F90F76338A6CF9457831DD5D7564033003AB43378A5` |
| `outputs/R036D1_gpt2_failure_modes.json` | 163,659 bytes | `87E9C0ADD6F71A67948B76EBCF36CACCC0C45CA82EB42954DE7F707BD5AFAB3F` |

诊断输出绑定源文件哈希和源实验签名。24 条重放的同精度、跨精度成功状态均与 R036
逐 trial 一致，且没有 `diagnostic_error`。这验证了诊断没有改变原始消息结论。

## Diagnostic Questions

R036-D1 不做新超参数扫描，只回答三个可证伪问题：

1. 同精度失败是否来自固定窗口内未到达 singleton？
2. FP32/FP16 的 integer counts 与 top-2 support 在何时首次分歧？
3. support rejection 是否是跨精度消息失败的唯一原因？

每一步都在完全相同的公开 token prefix 上比较 FP32/FP16。`count divergence` 指总质量
`2^16` 的 token integer counts 不相等；`support divergence` 指 top-2 token 集合或顺序
不相等；`observed rejection` 指编码 token 不在 FP16 retained support 中。

## Results

| Window | Parity | FP32 symbol 完成 | 首 byte 前/同时 count 分歧 | 首 byte 前/同时 support 分歧 | 全程 count 一致 | FP16 token 拒绝 | 无拒绝时跨精度成功 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 16 | 0 | 5/12 | 4/6 | 3/6 | 0/6 | 2/6 | 0/4 |
| 16 | 2 | 9/24 | 4/6 | 3/6 | 0/6 | 2/6 | 1/4 |
| 32 | 0 | 10/12 | 4/6 | 3/6 | 0/6 | 2/6 | 2/4 |
| 32 | 2 | 13/24 | 4/6 | 3/6 | 0/6 | 2/6 | 1/4 |

四个变体的首次 count 分歧中位数均为 token step `4.5`，首次 support 分歧中位数均为
step `7`。成功完成的 symbol 平均需要 `7.6` 到 `14.85` tokens。count 合同通常在一个
byte 完成之前或附近破裂，而不是只在长消息尾部累积误差。

`window=32, parity=0` 的同精度 symbol 完成率由 window=16 的 `5/12` 提高到 `10/12`，
说明窗口不足确实是一个独立问题。但每个变体都是 `0/6` 全程 count agreement，增大窗口
只能给合同分歧更多发生机会，不能构成跨精度修复。

每个变体有 2 条轨迹发生 observed rejection，且这些轨迹跨精度成功均为 `0/2`。但是
没有 rejection 的轨迹仍只有 `0/4` 到 `2/4` 成功。因此 rejection 是强失败信号，但不是
必要条件；support 相同而 integer counts 不同也会改变稀疏区间边界。

在 support 相同时但 counts 不同的 55 个事件实例中，描述性平均 TV 为 `0.03112`，最大
为 `0.10268`；support 不同时的 81 个事件实例描述性平均 TV 为 `0.23622`。这些事件来自
重复变体轨迹，不是独立样本，不能把事件数当作统计样本量，也不据此报告显著性。

## Mechanism Verdict

R036-D1 判定为 **MECHANISM-IDENTIFIED / SINGLE-CONTRACT-NO-GO**：

1. fixed-window byte coder 在同精度下存在右删失的 singleton 收敛失败；
2. FP32/FP16 单一 integer-count 合同对所有 6 个单元都不能维持完整轨迹；
3. top-2 support rejection 会导致确定性失败，但不发生 rejection 也不能保证恢复；
4. RS 只能纠正最终 symbol 错误或擦除，不能恢复已分歧的自回归合同状态。

这解释了 R035 `30/32` 短轨迹结构性 GO 为什么没有转化为消息级 GO：单条短 prefix 的
高 agreement 不是跨 prompt、跨 payload 的轨迹不变量。

## Stage Decision

停止把 `window=64`、更多 parity 或更粗 `q` 作为主修复方向。较大窗口可以作为同精度
coder 对照，但不能解决在首 symbol 前已经出现的跨精度合同分歧。

下一阶段应先完整核验 List-decoding PSS 的论文与公开代码，再在相同 integer counts 上
实现有限宽度合同假设列表，并用每个 byte/window 的 suffix 约束剪枝。该机制需要分别报告：

- list width 与额外内存/时间；
- 正确路径是否仍在列表内；
- suffix 剪枝后的歧义数；
- 消息成功率和无条件 bits/token；
- 相对原模型完整分布的偏差。

在全文和代码核验前不凭摘要猜测 list-decoding 算法。R037 AEAD 继续暂停；只有 raw-byte
恢复重新达到同精度 `6/6`、跨精度至少 `5/6` 后才恢复认证消息实验。

### Anomalies Detected

进程、显存、源哈希和 checkpoint 均无运行异常。发现的异常全部属于科研机制：固定窗口
右删失、早期 integer-count 分歧、top-2 support 分歧和 observed token rejection。
