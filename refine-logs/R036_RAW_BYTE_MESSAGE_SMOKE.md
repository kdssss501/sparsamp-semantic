# R036：Raw-byte 端到端消息验证

## Material Passport

- Origin Skill: experiment-agent
- Origin Mode: run
- Origin Date: 2026-07-20T05:38:28Z
- Verification Status: UNVERIFIED
- Version Label: r036_raw_byte_result_v1

## Experiment Result

- **ID**: R036
- **Type**: simulation
- **Status**: completed
- **Working Directory**: `C:\Users\41462\Documents\隐写`
- **Duration**: 121.8 seconds
- **Exit Code**: 0
- **GPU**: NVIDIA GeForce RTX 3060 Laptop GPU, 6 GB
- **Model**: local GPT-2
- **Precision**: FP32 encode / FP16 replay

执行命令：

```powershell
& '.venv\Scripts\python.exe' 'scripts\audit_byte_sliced_messages.py' `
  --model 'models\gpt2' --device cuda `
  --reference-dtype float32 --replay-dtype float16 `
  --top-p 1.0 --top-k 2 --logit-quantum 0.5 `
  --bin-mass-bits 16 --temperature 1.2 `
  --payload-bytes 2 --payload-seeds 0 1 `
  --window-tokens 16 32 --parity-bytes 0 2 `
  --run-label R036 `
  --output 'outputs\R036_gpt2_bin_mass_raw_bytes.json'
```

### Output Files

| File | Size | SHA-256 |
|---|---:|---|
| `outputs/R036_gpt2_bin_mass_raw_bytes.json` | 72,307 bytes | `F164C4C118598A7C59A67F90F76338A6CF9457831DD5D7564033003AB43378A5` |

`outputs/` 保持 Git ignored；哈希用于核对本地原始报告。脚本按 trial 原子保存，配置
签名为报告中的 `experiment_signature`，不同签名不能续接。显式 `--fresh` 会先归档旧报告，
不会覆盖上一次进度。

## Registered Gate

每个变体包含 3 prompts × 2 payload seeds，共 6 trials。预注册 GO 条件为：

1. FP32 同精度完整恢复 `6/6`；
2. 至少一个变体 FP32→FP16 完整恢复不低于 `5/6`；
3. 合格变体按完整恢复率、净容量、运行时间依次选择。

## Results

| Window | Parity | FP32→FP32 | FP32→FP16 | Same BER | Cross BER | 净 bit/token | Cross 有效 bit/token |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 16 | 0 | 1/6 | 0/6 | 0.8333 | 0.9063 | 0.5000 | 0.0000 |
| 16 | 2 | 3/6 | 1/6 | 0.5000 | 0.7396 | 0.2500 | 0.0417 |
| 32 | 0 | 4/6 | 2/6 | 0.3333 | 0.6667 | 0.2500 | 0.0833 |
| 32 | 2 | 4/6 | 1/6 | 0.3333 | 0.7396 | 0.1250 | 0.0208 |

四个变体均未达到同精度 `6/6`，因此 R036 判定为 **NO-GO**，没有可选择变体。
按照预注册门槛，不进入 R037 AEAD 实验。

## Mechanism Audit

24 个 trials 中，同精度完整恢复为 `12/24`，跨精度完整恢复为 `4/24`。这不是单一的
FP16 漂移问题，至少包含两个独立失效机制：

1. **固定窗口收敛不足**：同精度失败均首先表现为一个或多个 8-bit symbol 在窗口结束前
   未收缩到 singleton，随后成为 erasure。`window=32, parity=0` 的精确 symbol 恢复为
   `10/12`，优于 `window=16` 的 `5/12`，但仍不足以保证消息恢复。
2. **跨精度支持分歧**：`8/24` 个跨精度 trials 出现
   `token ... is not in the current retained distribution`。自回归前缀一旦在 top-2 支持上
   分歧，后续概率合同无法继续。另有未触发显式支持错误但恢复到错误 symbol 的情况。

RS 不能修复合同本身。增加 parity 会增加 codeword symbol 数量和暴露于失效的窗口数；
本实验中 parity=2 没有提高完整消息成功率，反而降低净容量。因此停止无界增加 parity
符合预注册停止规则。

R035 的 `30/32` count agreement 只证明了单条短轨迹上的结构性可行性。R036 说明该结果
不能直接外推到多 prompt、多 payload 和完整消息；这是 R035 的边界收紧，而不是对其数学
构造的否定。

## Stage Decision

R036 产出为 **MESSAGE-NO-GO / TWO-FACTOR FAILURE**：

- 当前 fixed bin-mass 合同尚未形成认证消息信道；
- 不能声称 precision-hardened PSS 已实现；
- 不能把全部失败归因于 FP32/FP16，因为 FP32 同精度门槛已失败；
- R037 暂停，避免把长 AEAD frame 和更多 parity 叠加到未稳定的 raw-byte 信道上。

下一阶段先做机制诊断：测量不同窗口下 singleton 收敛的生存曲线，并记录首次 top-k
支持/整数 counts 分歧的位置。若增大窗口能使同精度达到 `6/6` 但跨精度仍失败，则把
list decoding + suffix matching 前移，作为支持分歧后的有限候选恢复机制；若同精度仍不
稳定，则应更换 byte-sliced coder，而不是继续优化 FP16 合同。

### Anomalies Detected

进程、显存和 checkpoint 未出现运行异常。科研异常是同精度固定窗口未收敛和跨精度
top-2 支持分歧；两者均保留为负面结果。
