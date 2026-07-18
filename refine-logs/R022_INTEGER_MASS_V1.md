# R022 确定性整数概率合同 V1

## Material Passport

- Schema：ARS Material Passport 9 compatible local record
- Stage：experiment-agent / validate
- Verification Status：REPRODUCED, NO-GO-V1
- Date：2026-07-18
- Source：本地源码、Mock 测试设计、GPT-2/Qwen 本地模型
- External upload：无

## 研究问题

`1e-15` Decimal 量化能让相同浮点输入确定性重放，但不同精度模型仍可能产生略有差异的
概率。R022 检验：固定整数总质量是否能把未跨越桶边界的小漂移映射为相同计数，同时显式
测量支持丢失、候选 churn 和量化 KL/TV。

## 假设

- H1：在候选集合与顺序相同的步骤上，某个整数位宽 `b` 的精确合同一致率高于
  `1e-15` Decimal 合同。
- H2：support-preserving 分配使量化支持丢失计数为零。
- Anti-claim：整数分配不能修复候选集合变化，也不自动保证跨精度消息恢复。

## 实现

- 新增确定性最大余数分配，公开质量为 `2^b`。
- 可选 support-preserving 基础计数。
- 接入基础 SparSamp、FH、Verified-RRC 和 Fixed-Length RRC。
- 每步记录 `KL(Q||R)`、TV、支持丢失候选数与丢失质量。
- 新增 GPT-2 FP32 -> FP16 共享前缀审计脚本，扫描 `b={16,20,24,28,32}`。
- Decimal 模式仍为默认值，避免改变既有版本轨迹。

## 预注册主要指标

1. 可重放共享前缀步数；
2. 候选顺序完全一致率与候选 Jaccard；
3. Decimal `1e-15` 精确合同一致率；
4. 各整数位宽的精确计数一致率；
5. 支持丢失候选数、丢失 `Q` 质量、`KL(Q||R)` 和 TV；
6. 整数模式下 Mock token-ID 编解码互逆。

## 决策门禁

- GO：至少一个位宽在相同候选支持步骤上提高精确合同一致率，且 support-preserving 模式
  无支持丢失；随后扩大到 Qwen 和消息级跨精度恢复。
- NO-GO：整数合同与 Decimal 一致率相同或更差，或主要失败来自候选 churn；停止宣传
  “概率桶解决跨精度”，转向固定 logits/count side information 或 bit-exact inference。

## 实验设置

- 模型：本地 GPT-2；
- 硬件：NVIDIA GeForce RTX 3060 Laptop GPU；
- 参考精度：FP32；重放精度：FP16；
- 共享历史：FP32 每步选择 top-1 token，FP16 重放相同 token 前缀；
- `top_p=0.95`，temperature `1.0`，32 个 next-token 分布；
- 合同：Decimal `1e-15` 与 support-preserving integer
  `b={16,20,24,28,32}`。

原始结果：`outputs/R022_gpt2_precision_contract.json`，该目录忽略 Git 提交。

## 合同一致率

| 合同 | 精确一致步数 | 一致率 | 相对 Decimal 改善 |
|---|---:|---:|---:|
| Decimal `1e-15` | 10/32 | 31.25% | baseline |
| Integer 16-bit | 10/32 | 31.25% | 0 pp / 0% |
| Integer 20-bit | 10/32 | 31.25% | 0 pp / 0% |
| Integer 24-bit | 10/32 | 31.25% | 0 pp / 0% |
| Integer 28-bit | 10/32 | 31.25% | 0 pp / 0% |
| Integer 32-bit | 10/32 | 31.25% | 0 pp / 0% |

所有整数位宽只在 Decimal 也完全一致的 10 步上一致，未吸收任何额外 FP32/FP16 漂移。
提高位宽只会减小桶宽，不能解决本轮观测到的 `1e-4` 到 `1e-3` 级概率差异。

## 原始失败分解

| 类别 | 步数 | Step IDs | 含义 |
|---|---:|---|---|
| 完整合同一致 | 10 | 14,17,20,22,23,25,26,28,29,31 | 顺序、概率合同均一致 |
| 顺序一致但概率合同不同 | 4 | 11,13,16,19 | 概率漂移跨过所有测试整数桶 |
| 候选集合相同但顺序不同 | 6 | 1,2,4,5,7,8 | 概率排序改变区间排列 |
| 候选集合 churn | 12 | 0,3,6,9,10,12,15,18,21,24,27,30 | top-p 支持本身不同 |

- 候选顺序完全一致：14/32，`43.75%`；
- 候选集合相同：20/32，`62.50%`；
- 候选 churn：12/32，`37.50%`；
- 平均候选 Jaccard：`0.99412`，最小 `0.92857`；
- 最大公共候选概率差：均值 `0.001252`，中位数 `0.000795`，最大 `0.006192`；
- source mass 差：均值 `0.000158`，最大 `0.000706`；
- FP16 能重放完整 32-token top-1 前缀，没有 token 从候选支持中完全消失。

## 假设判定

- H1：**否定**。所有测试整数位宽相对 Decimal 的改善均为零。
- H2：**单元验证支持**。support-preserving 分配对正概率候选强制至少一个计数，测试中支持
  丢失为零；本实验未单独比较关闭支持保持的版本。
- Anti-claim：**得到支持**。候选顺序变化和 top-p churn 占 18/32 步，是整数概率量化之前的
  更上游故障。

该结果触发预注册 NO-GO：V1 不进入 Qwen 大规模消息级跨精度实验，也不能宣称整数概率桶
提高了跨精度恢复。

## 机制解释

整数合同只在输入候选顺序和概率落入相同离散桶时稳定。本轮有三个层级的失败：

1. 12 步 top-p 候选集合不同，任何只重分配已有候选质量的方法都无法修复；
2. 6 步候选集合相同但概率排名不同，当前按概率降序排列使区间顺序变化；
3. 4 步顺序相同但概率最大差为 `2.28e-4` 到 `9.41e-4`，大于 16-bit 单位
   `1/65536 approximately 1.53e-5`。

因此“提高整数位宽”方向与观测机制相反。更高位宽对概率更敏感，只改善量化逼近，不改善
跨精度容错。

## 下一研究门禁

R023 优先验证 canonical candidate order：在 top-p 支持选定后，按稳定 token ID 排列区间，
而不是按容易受精度扰动影响的概率排名排列。该排列不改变各 token 的目标概率，只改变区间
位置，可直接针对 6 个“同集合、不同顺序”步骤。

随后再做：

1. 记录每步候选数，扫描满足 `2^b >= K` 的更粗位宽，而不是只扫描 16-bit 以上；
2. 把候选集合 churn 与概率桶不一致分别报告；
3. 若 canonical order 后仍受 top-p churn 主导，再设计量化累计质量或固定 top-k 支持合同；
4. 只有共享前缀合同一致率明显超过 31.25% 后，才进入 Qwen 消息级恢复。

## 可复现命令

```powershell
.\.venv\Scripts\python.exe -m pytest -q

.\.venv\Scripts\python.exe scripts\audit_precision_contract.py `
  --model models/gpt2 `
  --reference-dtype float32 `
  --replay-dtype float16 `
  --tokens 32 `
  --mass-bits 16 20 24 28 32 `
  --output outputs/R022_gpt2_precision_contract.json
```

最终完整项目 Pytest 运行 117 项全部通过；Ruff、Ruff 新文件格式检查和 Vue 类型检查通过。
FP32 inference tensor 首次执行暴露了 logits 原地屏蔽错误，已改为显式 clone；本次完整
32-step GPU 实验和新增 clone 回归测试均已验证该路径。
