# R043 Sentence-Complete Qwen Replay Results

## Scope

R043 combines cross-precision token replay with a public text stopping rule. Generation continues for at least 64 tokens and stops at the first complete sentence, with a hard limit of 96 tokens.

## Setup

- Model: local Qwen2.5-1.5B-Instruct
- Precision: FP16 reference, BF16 replay
- Matrix: 3 prompts x 2 public seeds x 2 policies
- Length rule: first sentence boundary after token 64, capped at token 96
- Hardware: NVIDIA RTX 3060 Laptop GPU, 6 GB
- Runtime: 364.6 seconds

## Results

| Policy | Corrected exact replay | Sentence complete | Mean tokens | Mean / max correction rate | Top-16 coverage | Sparse / full record size |
|---|---:|---:|---:|---:|---:|---:|
| Greedy | 6/6 | 6/6 | 72.67 | 2.68% / 3.70% | 100% | 3.57% |
| Seeded | 6/6 | 6/6 | 73.50 | 1.62% / 2.86% | 100% | 2.16% |

The seeded trajectory lengths were `[70,72,66,77,82,74]` and correction counts were `[2,2,1,0,1,1]`. Uncorrected BF16 replay matched the full reference in only 1/6 trials; its mean exact common prefix was 46.17 tokens.

Compared with the fixed 64-token R042 pilot, seeded sentence completion improved from `0/6` to `6/6`. The average visible-length cost was 9.5 additional tokens.

## Distribution Cost

| Policy | Mean top-2 source mass | Mean truncation KL | Shared contract exact rate |
|---|---:|---:|---:|
| Greedy | 0.7642 | 0.3251 nats | 81.08% |
| Seeded | 0.7785 | 0.3027 nats | 83.75% |

Exact replay and readable completion do not remove the top-2 truncation cost. The distribution metrics remain part of the primary report.

## Visible Text Finding

The seeded reference responses directly answered all three prompt categories and ended at natural sentence boundaries. Example topics included experiment reproducibility, reliable software releases, and personalized learning. This is a structural and manual pilot check, not a blinded human preference study.

## Artifacts

- Output: `outputs/R043_qwen_sentence_replay.json`
- Size: 483,024 bytes
- SHA-256: `353909aa4f308065208d3618c00055235a0cde6eeb89e49a3a7149b7a85c1ada`
- Deterministic result signature: `391e47790ff9ef5015a30416cfbda9b12c7b98113343dce50706228cfd05da16`

## Decision

R043 is a stage GO. It simultaneously achieved:

- 6/6 sentence-complete seeded references;
- 6/6 exact FP16-to-BF16 corrected replay;
- 100% reference-token coverage in the BF16 top-16 envelope;
- 1.62% mean and 2.86% maximum correction rate;
- a correction record averaging 2.16% of a full token trace.

The result is ready for a paper methods section and pilot-results table. Submission-level evidence still requires a larger prompt set, three or more seeds, confidence intervals by prompt, and independent text-quality evaluation.
