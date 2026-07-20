# R042 Qwen FP16/BF16 Replay Results

## Scope

R042 transfers the R041 cross-precision replay method from GPT-2 to Qwen2.5-1.5B-Instruct. It measures exact token reproducibility, sparse correction rate, distribution cost, and visible response quality.

## Setup

- Model: local Qwen2.5-1.5B-Instruct
- Precision: FP16 reference, BF16 replay
- Matrix: 3 prompts x 2 public seeds x 2 policies
- Length: 64 tokens per trajectory
- Policies: public seeded sampling and deterministic greedy selection
- Hardware: NVIDIA RTX 3060 Laptop GPU, 6 GB
- Runtime: 255.6 seconds

## Results

| Policy | Corrected exact replay | Uncorrected exact replay | Mean / max correction rate | Top-16 coverage | Sparse / full record size |
|---|---:|---:|---:|---:|---:|
| Greedy | 6/6 | 0/6 | 3.13% / 4.69% | 100% | 4.17% |
| Seeded | 6/6 | 1/6 | 1.56% / 3.13% | 100% | 2.08% |

The seeded correction counts were `[1, 2, 1, 0, 1, 1]`. Its uncorrected mean exact common prefix was 44 tokens. The full integer contract matched at 83.07% of shared-prefix steps, while only 1.56% of token decisions required correction; distribution mismatch does not imply a token-choice mismatch at every step.

## Distribution Cost

| Policy | Mean top-2 source mass | Mean truncation KL |
|---|---:|---:|
| Greedy | 0.7704 | 0.3133 nats |
| Seeded | 0.7888 | 0.2864 nats |

Qwen retains substantially more top-2 source mass than the GPT-2 pilot on these trajectories. This is an observed model/prompt difference, not yet a population-level comparison.

## Visible Text

The sampled answers were coherent and directly addressed the prompts. Mean whitespace-delimited length was 55.7 words for seeded and 53.3 for greedy. However, none of the 64-token references ended at a sentence boundary (`0/6` for each policy), so fixed-length output is not sufficient for polished user-facing responses.

## Artifacts

- Output: `outputs/R042_qwen_fp16_bf16_replay.json`
- Size: 424,352 bytes
- SHA-256: `6df08f8860a49de43eec846a5aeef08b8313a749cae6c6f6421e5e0d6b807431`
- Deterministic result signature: `1aa8e9bf47cc02b659b9dcd3570e7b09d692c196e16271f65dd86d463d89f10b`

## Decision

R042 is a pilot GO for numerical reproducibility: corrected seeded replay reached 6/6, top-16 coverage was 100%, and correction-record size was 2.08% of a full trace.

It is not yet a user-facing text-quality GO because fixed 64-token generation truncated every response. R043 will keep the same replay method but continue each reference until the first public sentence boundary after 64 tokens, capped at 96 tokens. The replay length is taken from the reference record, so exact-token verification remains well-defined.
