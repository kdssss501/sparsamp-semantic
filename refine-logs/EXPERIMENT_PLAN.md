# Experiment Plan

**Problem**: Practical finite-budget reliability and finite-precision security for SparSamp  
**Method Thesis**: Public-state adaptive blocks plus deterministic integer probability mass improve
authenticated-message completion under a token budget without message-dependent distribution
control.  
**Date**: 2026-07-17

## Claim Map

| Claim | Why It Matters | Minimum Convincing Evidence | Blocks |
|---|---|---|---|
| C1: FH-SparSamp improves finite-budget completion | Real channels have length limits | >=10 point completion gain at matched text/security metrics across 3+ models or 2 models + broad prompts | B1, B2 |
| C2: Integer mass is more precision-robust | FP artifacts can be detected and break replay | Cross-precision recovery gain and no detector-AUC regression >0.02 | B3 |
| Anti-claim: gains are only longer text or lower quality | Rules out an easy tradeoff | Matched token budget, perplexity, semantic rating, and native tail ablation | B2, B4 |

## Paper Storyline

Main paper must prove:

- official SparSamp reproduction is correct;
- completion probability improves at fixed budgets;
- finite-precision behavior is measured against a current detector;
- public-text and token-ID reliability are reported separately.

Appendix can support:

- additional prompt domains, block schedules, and tokenizer diagnostics;
- DeepSeek API drift pilot if a key becomes available.

Experiments intentionally cut:

- generic larger-model comparisons without a mechanism hypothesis;
- weak legacy baselines added only to increase table size;
- claiming Token Ambiguity correction as the main novelty.

## Experiment Blocks

### B0: Faithful Reproduction Gate

- Claim tested: the independent implementation matches SparSamp.
- Compared systems: official artifact vs this codec on GPT-2.
- Configurations: paper block sizes and top-p values, fixed model revision.
- Metrics: decode accuracy, bit/token, utilization, ATST, SITR, generation speed.
- Success criterion: 100% decode on ambiguity-free cases and capacity error <=5%.
- Failure interpretation: stop method research and repair reproduction first.
- Target: Appendix reproduction table, mandatory gate.

### B1: Finite-Horizon Reliability

- Claim tested: adaptive blocks reduce completion failures and tail latency.
- Data: 20-prompt pilot, then 100 prompts across QA, explanation, summary, and structured lists.
- Systems: fixed SparSamp, FH-SparSamp, strongest available list-decoding/ANS baseline.
- Budgets: 128, 256, 512, 1024 tokens.
- Metrics: complete-message success, survival curve, unconditional bit/token, p50/p95 tokens,
  authenticated BER, failures per payload bit.
- Seeds: 3 pilot, 5 final.
- Success criterion: >=10 point completion gain at 512 tokens and lower p95 length.
- Target: Main Figure 1 and Main Table 1.

### B2: Mechanism and Simplicity Ablation

- Claim tested: adaptive scheduling itself matters.
- Variants: fixed 2/4/8/16/32, entropy-only, budget-only, full controller, overbuilt predictor.
- Metrics: completion, bit/token, runtime, controller overhead.
- Success criterion: full controller beats best fixed block; overbuilt model adds no material gain.
- Target: Main Table 2.

### B3: Finite-Precision Security and Replay

- Claim tested: integer mass improves support preservation and deterministic extraction.
- Precision: FP16, BF16, FP32; repeat on available CPU/GPU combinations.
- Systems: current decimal quantization, integer largest-remainder, randomized unbiased residual.
- Metrics: support loss, low-probability token rate, cross-mode decode, TV/KL bounds, detector AUC.
- Detector: reproduce low-probability-vanishing features where feasible.
- Success criterion: higher cross-mode recovery with detector AUC within 0.02 of native sampling.
- Target: Main Figure 2.

### B4: Semantic Completion and Human Quality

- Claim tested: native finishing tail fixes truncation without explaining C1 gains.
- Variants: immediate stop, punctuation stop, EOS tail with 16/32/64 token caps.
- Metrics: sentence completeness, perplexity, blinded pairwise preference, added latency/tokens.
- Success criterion: >=70% preference for tail variant with unchanged embedded-prefix metrics.
- Target: Qualitative figure and appendix table.

### B5: Black-Box API Pilot

- Priority: Nice-to-have until an API key exists.
- Systems: native API, top-20 arithmetic coding, SparSamp-20, DriftGuard.
- Metrics: recovery, bit/token, request/token, cost/kbit, observed mass, candidate churn, logprob drift,
  model fingerprint changes, bounded truncation KL.
- Gate: continue only if repeated-query stability supports >=0.2 useful bit/token.

## Run Order and Milestones

| Milestone | Goal | Runs | Decision Gate | Cost | Risk |
|---|---|---|---|---:|---|
| M0 | Reproduction correctness | Official Basic + E1-E3 subset | <=5% capacity error | 1-2 GPU h | Artifact differences |
| M1 | Measure current failure distribution | 20 prompts x 3 seeds x fixed blocks | Stable metrics and failure logging | 2 GPU h | Long tails |
| M2 | Adaptive pilot | 20 prompts x 3 seeds x 2 variants | >=10 point completion gain | 2 GPU h | No signal |
| M3 | Precision pilot | 10 prompts x precision/mass variants | Replay or detector improvement | 1-2 GPU h | Hardware limits |
| M4 | Scale selected method | 100 prompts x 5 seeds | Paper-level confidence intervals | 8+ GPU h | Only after go decision |

## Compute and Data Budget

- Initial decision budget: <=8 GPU-hours.
- Final scale budget: estimate after M1 throughput profiling.
- Human evaluation: 30-50 paired samples per main variant for pilot; power analysis before final.
- Biggest bottleneck: full-vocabulary sorting and repeated model replay during decoding.

## Risks and Mitigations

- Closest work overlaps adaptive coding: perform full-text novelty check before implementation.
- Completion gain trades off security: match output budgets and run steganalysis.
- Token Ambiguity dominates all other errors: report separately and integrate ReTokSync baseline.
- One GPU limits scale: cache logits/distribution snapshots for codec-only ablations where valid.

## First Three Runs

1. Official GPT-2 Basic Test with exact artifact configuration.
2. Qwen 20-prompt x 3-seed fixed-block completion survival pilot.
3. Provider profile separating model forward, full sort, candidate transfer, and codec time.

## Final Checklist

- [ ] Main reproduction gate passed
- [ ] Completion success uses confidence intervals
- [ ] Novelty isolated from stronger existing coders
- [ ] Precision detector and cross-mode replay included
- [ ] Public-text and token-ID recovery separated
- [ ] Nice-to-have API work does not delay the core evidence
