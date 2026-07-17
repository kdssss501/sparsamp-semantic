# ARIS Research Audit

**Date**: 2026-07-17
**Mode**: Local critical-review fallback. The ARIS-required Codex reviewer MCP was unavailable,
so no external-review claim is made.

## Verdict

The project is a credible engineering prototype and a useful negative-results platform, but it is
not yet a paper-quality SparSamp reproduction. The strongest path is not another tokenizer fix or
another entropy coder. It is a finite-horizon and finite-precision audit of provably secure
sampling, with a black-box API branch if provider access becomes available.

## Major Findings

### 1. Reproduction claim is premature

The implementation has mathematical tests and working Qwen examples, but it has not run the
official artifact's GPT-2 Basic Test and E1-E3 suite. Until those results match, the code should be
described as an independent implementation and semantic extension, not a faithful reproduction.

**Minimum fix**: reproduce the official artifact with fixed revisions and compare decoding,
capacity, ATST, SITR, and speed under the paper's configurations.

### 2. Evaluation is underpowered

One prompt and one encrypted payload cannot establish that block size 8 is better than 32. Payload
nonce, key, prompt entropy, and model response shape all affect finite-run length.

**Minimum fix**: at least 20 prompts x 3 payload seeds for the pilot, then 100 prompts x 5 seeds for
the final primary result. Report confidence intervals and failure-censored token budgets.

### 3. Token Ambiguity is real but no longer novel by itself

The observed ambiguous artifact differs at an internal BPE merge, not only at stripped whitespace.
However, ReTokSync (arXiv:2604.25486) already targets self-synchronizing token disambiguation and
reports above 99.7% extraction accuracy.

**Implication**: use ReTokSync as a baseline or compatible component. Do not make generic token
ambiguity correction the dominant contribution.

### 4. Capacity-only optimization is crowded

ANStega (NDSS 2026) claims optimal capacity, efficiency, and security using ANS. List-decoding PSS
(arXiv:2604.21394) also targets high capacity, and dyadic approximation work
(arXiv:2605.05837) optimizes rate-detectability tradeoffs.

**Implication**: a new coder must address a different bottleneck and beat these strong baselines.

### 5. Finite precision is now a first-class security threat

The 2026 ACL work on low-probability vanishing reports detectability caused by finite-precision
artifacts. Current `1e-15` probability quantization is a reproducibility mechanism, not a complete
security defense.

**Minimum fix**: measure token support loss, low-probability selection rates, cross-device replay,
and detector AUC under FP16/BF16/FP32 and alternative integer mass allocation.

### 6. Practical text quality needs a completion objective

Stopping exactly when encrypted bits finish can truncate a sentence. A semantic finishing tail is
valuable engineering and a necessary evaluation control, but is unlikely to be a standalone paper
contribution.

### 7. Black-box API remains differentiated

The top-20 API setting introduces unavailable tail mass, repeated-query drift, model version
changes, cost, and rate limits. These constraints are not solved by a full-logit local coder.

**Opportunity**: treat API-SparSamp as a separate bounded-bias protocol, with erasures, guard bands,
fingerprints, and explicit cost/KL accounting.

## Claim Matrix

| Outcome | Allowed Claim | Forbidden Claim |
|---|---|---|
| Official artifact matches within tolerance | Faithful local reproduction | General LLM superiority |
| Adaptive method improves completion with no detector increase | Better finite-horizon practicality | Zero KL without proof |
| Integer method replays across hardware and resists precision detector | Precision-hardened PSS | Universal undetectability |
| API method survives measured drift with bounded KL/cost | Robust black-box extension | Equivalent SparSamp reproduction |
| Public-text recovery fails but token IDs recover | Tokenization is the bottleneck | End-to-end real-channel reliability |
| Fixed-length stego and matched cover have similar pilot entropy | No stable visible-entropy shift in the measured 4 pairs | Practical undetectability or detector resistance |

## Closest Recent Work

- SparSamp: https://arxiv.org/abs/2503.19499
- ReTokSync: https://arxiv.org/abs/2604.25486
- ANStega: https://doi.org/10.14722/ndss.2026.240605
- List-decoding PSS: https://arxiv.org/abs/2604.21394
- LLM seed channel: https://arxiv.org/abs/2606.09135
- Finite-precision detection: https://aclanthology.org/2026.findings-acl.1013/
- Robust LLM steganography: https://arxiv.org/abs/2504.08977
- Dyadic coding approximation: https://arxiv.org/abs/2605.05837
- CMDP rate/security optimization: https://arxiv.org/abs/2502.01827

These references were checked from metadata and abstracts during this audit. Full-text claim
verification remains required before paper submission.
