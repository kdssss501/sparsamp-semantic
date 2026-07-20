# R045-R046 Precision Replay Ablation

## Material Passport

- Origin Skill: ARIS `ablation-planner` and `analyze-results`
- Selected public seed: 0
- Prompt-cluster bootstrap: 10,000 resamples
- Deterministic analysis signature: `ed69c9654ab0b7443a16f682380c8db9b8250bb2a8ab0235e589c2ce8808d749`
- Verification status: ANALYZED

## Source Integrity

| Variant | Source SHA-256 | Result signature |
|---|---|---|
| forward_top2 | `6a6eaa292e8ac490b38932969879323cc44088361ceabd20b51466a836fc3110` | `c9ca57129a664a4114d7c186527c176c5e898596c1549e62724d88679a30c62d` |
| forward_top4 | `106d47424ed54c188053acc2709a1c80955ec8b113631d1242cd4fc5273b1b17` | `78219da2795f0beaa0a2a38ff10713f749256dd3e0b56440a5eaa6c3818f3e64` |
| reverse_top2 | `0db87168911af7e1c65274df5c5e680f1e648f20e14d5555e50b9fbbfca755fb` | `3f7389ea15417322e2f6ef46416ef3113e1cb9d12272e7b82f74dbf1c4f05c66` |

## Raw Comparison

| Variant | Direction | k | Trials | Corrected | Complete | Correction rate | Source mass | Truncation KL | Contract exact | Record ratio |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| forward_top2 | float16->bfloat16 | 2 | 20 | 20/20 | 20/20 | 0.0200 | 0.7335 | 0.3837 | 0.8447 | 0.0267 |
| forward_top4 | float16->bfloat16 | 4 | 20 | 20/20 | 16/20 | 0.0240 | 0.8446 | 0.1978 | 0.5933 | 0.0320 |
| reverse_top2 | bfloat16->float16 | 2 | 20 | 20/20 | 19/20 | 0.0211 | 0.7322 | 0.3866 | 0.8424 | 0.0282 |

## Key Findings

1. Increasing k from 2 to 4 raised retained source mass by +0.1111 (paired 95% CI [+0.0923, +0.1309]) and reduced the truncation component by -0.1859 nats/token (CI [-0.2207, -0.1522]).
2. The same k change altered correction rate by +0.0040 (CI [-0.0056, +0.0134]), so there is no detected correction-rate improvement.
3. Top-4 reduced shared-contract exactness by -0.2513 (CI [-0.2774, -0.2268]) and sentence completion by -0.2000 (CI [-0.4000, -0.0500]).
4. Reversing precision direction changed correction rate by +0.0011 (CI [-0.0088, +0.0108]) and source mass by -0.0014 (CI [-0.0182, +0.0152]); neither interval excludes zero.
5. Corrected exact recovery was 20/20 in all three controlled variants. The Wilson lower 95% bound is 0.8389 per variant.

## Decision

- Keep `contract_top_k=2` as the reproducibility default: top-4 buys a lower truncation component but does not reduce correction overhead and weakens contract agreement and structural completion in this sample.
- Treat top-4 as a distribution-fidelity operating point on the Pareto frontier, not as the default or a uniformly better method.
- Accept bidirectional FP16/BF16 replay as a stage-level result because both directions reached 20/20 corrected recovery and the paired direction effects on correction rate and source mass include zero.

## Interpretation Boundaries

- The top-k setting participates in reference token selection, so top-2 and top-4 intentionally generate different trajectories. Comparisons are paired by prompt and public seed, not by token trajectory.
- The reported `-log Z` is the truncation component for conditioning on retained support. Quantization error is separate and this study does not claim zero total divergence.
- Twenty prompts with one selected seed establish a controlled ablation, not cross-model or cross-hardware generality.
- Sentence completion is an automated structural endpoint, not a blinded semantic-quality judgment. The top-4 decrease needs multi-seed or human evaluation before becoming a general quality claim.

## Next Experiments

1. Replicate the frozen top-2 configuration on an independent GPU/CUDA stack to test hardware generality.
2. Run a blinded semantic preference study comparing native generation, top-2, and top-4 outputs.
3. Repeat top-4 with additional public seeds only if the paper makes a semantic-quality claim; it is not needed for the current precision-direction claim.
