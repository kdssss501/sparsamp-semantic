# Semantic SparSamp

本项目复现 SparSamp 的稀疏采样编解码核心，并把默认语言模型从 GPT-2
替换为更适合生成自然中文和可读回答的指令模型。

默认模型是 `Qwen/Qwen2.5-1.5B-Instruct`。它可在 6GB 显存上直接使用
半精度推理，并提供完整 next-token 概率分布。可选实验模型为
`Qwen/Qwen2.5-3B-Instruct`，建议在 4-bit 环境验证后启用。

## 设计边界

- 本地 Hugging Face 后端能够访问完整概率分布，适合作为 SparSamp 主实验。
- DeepSeek V4 Pro 后端仅能观察 top-20 logprobs，是单独的黑盒 API 扩展，
  不等价于原论文的分布保持结论。
- 当前可靠解码路径使用生成 token IDs。文本重新分词路径会明确检测
  Token Ambiguity，不会静默声称解码成功。
- 密钥只从环境变量读取；`.env`、模型权重和实验输出不会进入 Git。

## 环境

推荐使用项目自带的 Python 3.11 环境：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1 -Local -Api
```

`-Local` 会通过可断点续传脚本安装固定的 `torch 2.7.1+cu126`，用于 RTX 3060
等支持 CUDA 12.6 的 NVIDIA 显卡。安装后可用以下命令确认 CUDA：

```powershell
& ".\.venv\Scripts\python.exe" -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CUDA unavailable')"
```

若网络中断，直接重新运行 `scripts/install_cuda_torch.ps1`，脚本会继续已有的
`.downloads` 文件。模型也建议显式下载，以便断点恢复：

```powershell
& ".\.venv\Scripts\python.exe" scripts\download_model.py `
  --repo Qwen/Qwen2.5-1.5B-Instruct `
  --output models/qwen2.5-1.5b-instruct
```

只运行数学与 Mock 测试：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1
uv run --no-sync pytest
```

## 快速验证

无需下载模型的端到端演示：

```powershell
$env:SPARSAMP_SECRET_KEY = "replace-with-a-long-random-secret"
uv run --no-sync sparsamp mock-demo --message "这是一条隐藏消息"
```

使用本地 Qwen 编码：

```powershell
$env:SPARSAMP_SECRET_KEY = "replace-with-a-long-random-secret"
uv run --no-sync sparsamp encode-local `
  --model models/qwen2.5-1.5b-instruct `
  --device cuda `
  --dtype float16 `
  --prompt "请用自然、清晰的中文解释为什么可复现实验很重要。" `
  --message "实验编号 A-17" `
  --output outputs/qwen-run.json
```

解码：

```powershell
uv run --no-sync sparsamp decode-local --input outputs/qwen-run.json
```

只根据公开的 cover text 重新分词并解码，可额外验证 Token Ambiguity：

```powershell
uv run --no-sync sparsamp decode-local --input outputs/qwen-run.json --from-text
```

CLI 默认使用 `block_size=32`、`top_p=0.95`、`temperature=1.0`。SparSamp
在该截断并重新归一化的分布上工作，因此隐写文本的语义质量应接近同配置下
Qwen 的普通随机采样结果。

## 复现实验

GPT-2 只用于通过官方 Artifact 的一致性门禁。语义质量、有限预算完成率、
Token Ambiguity 和后续算法优化均以本地 Qwen2.5-1.5B 为主实验模型。

首轮建议按以下顺序运行：

1. Mock 测试验证算法互逆和载荷认证。
2. Qwen2.5-1.5B 单 prompt 烟雾测试。
3. `block_size={2,4,8,16,32,64,128}` 网格。
4. `top_p={0.8,0.9,0.95,1.0}` 网格，并与原生随机采样做盲评。
5. 稳定后再尝试 3B 量化模型、Token Ambiguity 和 DeepSeek API 实验。

网格实验会复用同一份模型权重：

```powershell
uv run --no-sync python scripts\run_semantic_grid.py `
  --config configs\semantic_grid.example.json `
  --output outputs\semantic-grid.jsonl
```

模型已手动放入 `models/qwen2.5-1.5b-instruct` 时，可先运行小型 GPU 网格：

```powershell
$env:SPARSAMP_SECRET_KEY = "replace-with-a-long-random-secret"
uv run --no-sync python scripts\run_semantic_grid.py `
  --config configs\qwen15_smoke_grid.json `
  --output outputs\qwen15-smoke-grid.jsonl
```

有限 token 预算实验使用可恢复 JSONL，并对更大预算下已经提前完成的确定性轨迹
生成带 `derived_from_run_id` 的记录，避免重复运行模型：

```powershell
$env:SPARSAMP_SECRET_KEY = "replace-with-a-long-random-secret"
& ".\.venv\Scripts\python.exe" scripts\run_completion_pilot.py `
  --config configs\qwen15_completion_pilot.json `
  --output outputs\qwen15-completion.jsonl

& ".\.venv\Scripts\python.exe" scripts\summarize_completion.py
```

当前 R003 烟雾实验报告见
[refine-logs/R003_PILOT_RESULTS.md](refine-logs/R003_PILOT_RESULTS.md)。该实验只有
3 个 prompt 和 2 个 payload seed，用于验证实验管线，不作为论文性能结论。

FH-SparSamp v1 的短预算消融使用：

```powershell
$env:SPARSAMP_SECRET_KEY = "replace-with-a-long-random-secret"
& ".\.venv\Scripts\python.exe" scripts\run_completion_pilot.py `
  --config configs\qwen15_fh_pilot.json `
  --output outputs\qwen15-fh-pilot-v2.jsonl

& ".\.venv\Scripts\python.exe" scripts\summarize_fh.py
```

v1 控制器没有超过固定 block 16，已按实验门禁拒绝。负面结果和下一版
tail-fragmentation 方向见
[refine-logs/R005_FH_V1_RESULTS.md](refine-logs/R005_FH_V1_RESULTS.md)。

随后执行的 tail-fragmentation 烟雾实验同样未超过固定 block 16，结果见
[refine-logs/R005_TAIL_SCHEDULE_SMOKE.md](refine-logs/R005_TAIL_SCHEDULE_SMOKE.md)。
因此当前不再继续扫描 block schedule，下一阶段转向语义收尾和有限精度重放。

算法、复杂度和安全边界见 [docs/algorithm.md](docs/algorithm.md)。

## 科研路线

- 当前研究约束与已有证据：[RESEARCH_BRIEF.md](RESEARCH_BRIEF.md)
- ARIS 方法审计：[refine-logs/REVIEW_SUMMARY.md](refine-logs/REVIEW_SUMMARY.md)
- 候选创新方向：[IDEA_REPORT.md](IDEA_REPORT.md)
- Claim-driven 实验计划：[refine-logs/EXPERIMENT_PLAN.md](refine-logs/EXPERIMENT_PLAN.md)
- RRC 数学正确性审计：[refine-logs/R019_VERIFIED_RRC_THEORY_AUDIT.md](refine-logs/R019_VERIFIED_RRC_THEORY_AUDIT.md)
- Verified-RRC 定理、反例与 Claim Matrix：[docs/verified_rrc_theory.md](docs/verified_rrc_theory.md)
- 固定长度 Verified-RRC：[docs/fixed_length_rrc.md](docs/fixed_length_rrc.md)
- Fixed-Length RRC V1 结果：[refine-logs/R020_FIXED_LENGTH_RRC_V1.md](refine-logs/R020_FIXED_LENGTH_RRC_V1.md)
- Fixed-Length matched-cover 与量化偏差审计：[refine-logs/R021_FIXED_LENGTH_MATCHED_COVER.md](refine-logs/R021_FIXED_LENGTH_MATCHED_COVER.md)
- 确定性整数概率合同：[docs/integer_probability_contract.md](docs/integer_probability_contract.md)
- R022 整数质量实验记录：[refine-logs/R022_INTEGER_MASS_V1.md](refine-logs/R022_INTEGER_MASS_V1.md)

本仓库用于授权科研、复现与防御评估。公开数据或部署前请阅读
[SECURITY.md](SECURITY.md)。

## Web 研究工作台

后端使用 FastAPI 串行执行 GPU 任务并复用已加载的 Qwen 权重，前端使用 Vue 3、
Vite、TypeScript、Pinia、Element Plus 和 ECharts。密钥只进入单次任务内存，
不会写入 operation 状态或实验 artifact。

安装并构建：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1 -Local -Api -Web
Set-Location web
npm.cmd install
npm.cmd run build
Set-Location ..
```

从项目根目录启动：

```powershell
& ".\.venv\Scripts\sparsamp-web.exe" --host 127.0.0.1 --port 8000
```

浏览器访问 `http://127.0.0.1:8000`。接口契约与本地安全边界见
[docs/api.md](docs/api.md)。
