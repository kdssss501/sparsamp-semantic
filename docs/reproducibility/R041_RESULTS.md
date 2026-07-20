# R041 Cross-Precision Replay Results

## Scope

R041 evaluates ordinary LLM experiment reproducibility across numerical precision. An FP32 run produces a stochastic reference sequence. An FP16 run uses the same public configuration and records explicit `(step, token_id)` corrections only when its local choice differs.

## Setup

- Model: local GPT-2
- Precision: FP32 reference, FP16 replay
- Matrix: 3 prompts x 2 public seeds x 2 policies
- Length: 64 tokens per trajectory
- Contract: top-2 integer mass derived inside a top-16 validation envelope
- Policies: public seeded sampling and deterministic greedy selection

## Results

| Policy | Corrected exact replay | Uncorrected exact replay | Mean / max correction rate | Top-16 coverage | Sparse / full record size |
|---|---:|---:|---:|---:|---:|
| Greedy | 6/6 | 4/6 | 0.52% / 1.56% | 100% | 0.78% |
| Seeded | 6/6 | 2/6 | 2.34% / 6.25% | 100% | 3.52% |

The seeded correction counts were `[1, 0, 1, 3, 4, 0]` over six 64-token trajectories. Without corrections, its mean exact common prefix was 30.33 tokens.

## Distribution Cost

| Policy | Mean top-2 source mass | Mean truncation KL | Full-logit quantization KL | Full-logit quantization TV |
|---|---:|---:|---:|---:|
| Greedy | 0.5651 | 0.8759 nats | 0.00339 | 0.02550 |
| Seeded | 0.4980 | 1.0020 nats | 0.00391 | 0.02948 |

The method improves exact replay, not distribution fidelity. Top-2 truncation remains the dominant quality cost and must be reported separately.

## Reproducibility Validation

Three independent GPU executions produced the same deterministic result signature:

```text
911d8427499e08d0e776ec276ad9fb489591438288005f066f8f3dd49952be25
```

GPU timing differed and is excluded from this signature. The final bias-audit output is `outputs/R041B_gpt2_replay_certificate_bias.json`, 413,945 bytes, SHA-256 `9acc5aac04ec36793d3f9e2cbf716f6c22ca0fa7614bb1acbb85b9621634b901`.

## Validation Boundaries

- All 12 configured units completed; there was no result filtering.
- The sample is too small for population-level inference or p-values.
- Prompt-level heterogeneity is retained in the JSON rows.
- Results currently apply only to local GPT-2, one GPU, and one software environment.
- Exact replay does not imply identical FP32 and FP16 probability distributions.

## Decision

R041 passes its pilot gate: corrected replay is exact in 6/6 seeded trials, all reference choices remain in the FP16 top-16 envelope, mean correction rate is below 10%, and the sparse record is below 50% of a full token trace.

The next stage evaluates Qwen2.5-1.5B-Instruct with FP16 reference and BF16 replay, focusing on readable text, exact token replay, correction rate, and the distribution-quality tradeoff.
