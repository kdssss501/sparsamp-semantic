# R047 External GPU Replay Instructions

These commands construct a fresh target-side replay report from the reference-only bundle. Run
them from the repository root in PowerShell.

## Inputs

- Repository checkout containing the R047 implementation.
- `R047_reference_seed0.json`, transferred separately from the source machine.
- The complete `Qwen2.5-1.5B-Instruct` model directory.
- Python 3.11 and a CUDA-capable PyTorch installation supporting the requested dtype.

Do not use `--metadata-only-weights` for a research result. It omits the weight-file content hash
and therefore weakens model identity validation.

## Setup

```powershell
git checkout research-v0.35-external-replay-cost-audit
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1 -Local
```

Place the bundle at `outputs/R047_reference_seed0.json` and the model at
`models/qwen2.5-1.5b-instruct`. Verify the transferred bundle before running:

```powershell
Get-FileHash outputs/R047_reference_seed0.json -Algorithm SHA256
```

Expected SHA-256:

```text
3db563f6e569828689e82b06184d439cdb12cfe78d9b5bdd4b5ec3d2601ff76c
```

## Fresh Replay

```powershell
& ".\.venv\Scripts\python.exe" scripts/replay_external_bundle.py `
  --bundle outputs/R047_reference_seed0.json `
  --model models/qwen2.5-1.5b-instruct `
  --device cuda `
  --target-dtype bfloat16 `
  --output outputs/R047_external_target.json `
  --fresh
```

The script saves each completed trial atomically. If the process is interrupted, rerun the same
command without `--fresh`:

```powershell
& ".\.venv\Scripts\python.exe" scripts/replay_external_bundle.py `
  --bundle outputs/R047_reference_seed0.json `
  --model models/qwen2.5-1.5b-instruct `
  --device cuda `
  --target-dtype bfloat16 `
  --output outputs/R047_external_target.json
```

The run is complete only when the report has `phase="completed"`. Preserve the JSON report
unchanged; it contains the environment signature, per-trial timings, corrections and reference
identities needed for audit.

## Cost Analysis

```powershell
& ".\.venv\Scripts\python.exe" scripts/analyze_replay_cost.py `
  --bundle outputs/R047_reference_seed0.json `
  --target outputs/R047_external_target.json `
  --output outputs/R049_external_cost_analysis.json `
  --markdown outputs/R049_EXTERNAL_COST_ANALYSIS.md
```

Report the target environment signature and the SHA-256 of both output files when sharing the
result. Do not overwrite the source-machine report.
