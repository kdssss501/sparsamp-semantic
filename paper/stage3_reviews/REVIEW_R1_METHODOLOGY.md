# Peer Review Report - R1 Methodology

## Manuscript Information

- **Title:** Sparse correction certificates recover stochastic language generation across numerical precision
- **Manuscript ID:** SPRC-STAGE3-001
- **Review Date:** 2026-07-21
- **Review Round:** 1

## Reviewer Information

- **Role:** Peer Reviewer 1 - Methodology
- **Identity:** ML-systems methodologist specializing in floating-point nondeterminism, GPU reproducibility and cluster-aware computational experiments.
- **Focus:** Numerical contract validity, experimental unit, uncertainty, controls and reproducibility.

## Overall Assessment

- **Recommendation:** Major Revision
- **Confidence:** 5/5

The paper defines a deterministic integer next-token contract and a target-conditioned correction manifest for recovering one stochastic reference path under a second precision. The deterministic induction is sound under its stated preconditions, and the manuscript correctly treats correction density, not corrected exactness, as the empirical quantity. Prompt-cluster bootstrap intervals preserve the three within-prompt seed trajectories and paired prompt resampling is used for the one-seed ablations. These are appropriate choices for the declared fixed prompt set. The main limitations are external rather than hidden: a single GPU/software stack, only 20 prompt clusters, a single-seed direction/contract-width ablation, and no quantified divergence contribution from integer apportionment. In addition, the 60/60 corrected outcome is guaranteed by manifest completeness and should not dominate the empirical evaluation. The paper is methodologically promising and auditable, but requires an independent frozen-bundle replay and stronger sensitivity/baseline analysis before its portability and efficiency implications are secure.

## Strengths

### S1: Correct conditional proof boundary

Methods defines the manifest against the target contract on the reference prefix and proves replay by induction only when model, tokenizer, prompt, configuration, seed and target environment match. It explicitly rejects target independence and termination claims.

### S2: Experimental units are handled responsibly

The Statistical Analysis section treats prompts as bootstrap clusters and retains all three seeds within each sampled prompt. It does not falsely count the 60 trajectories as 60 independent prompt samples.

### S3: Negative and incomplete outcomes remain visible

The official reproduction retains seven budget-exhausted trials, Qwen retains two structurally incomplete outputs, and Token Ambiguity trials remain in the ledger. This reduces selection bias.

### S4: Estimands are not pooled incorrectly

The manuscript and statistical notes distinguish equal-trial rates from token-weighted summaries and separate deterministic serialization lengths from bootstrap estimands.

## Weaknesses

### W1: The primary exact-replay result is tautological unless paired with falsifiable endpoints

**Problem:** A complete manifest stores the reference token at every target disagreement, so corrected 60/60 recovery follows from the construction and implementation correctness.

**Why it matters:** Presenting 60/60 prominently can make a software invariant appear like general empirical performance.

**Suggestion:** Declare correction density or end-to-end bytes under a frozen package boundary as the primary empirical endpoint, retain exact recovery as a mandatory integrity check, and prespecify failure thresholds for unseen target environments.

**Severity:** Major.

### W2: Independent portability has not been tested

**Problem:** The R047 run reconstructs the package on the same physical GPU and software installation.

**Why it matters:** Kernel, driver, device and framework changes are exactly the sources of nondeterminism the method targets.

**Suggestion:** Freeze the reference bundle and execute the target side independently on another device and environment without regenerating reference artifacts.

**Severity:** Major.

### W3: Integer-apportionment error is omitted from the distribution audit

**Problem:** The manuscript reports full-logit quantization KL/TV and the conditioning term `-log(Z)`, but does not isolate the finite-mass approximation from largest-remainder apportionment.

**Why it matters:** The current distribution account is incomplete and cannot support a total fidelity comparison between contract widths.

**Suggestion:** Compute per-step and aggregate TV/KL where finite, plus a deterministic bound for the (2^{16}) apportionment; report truncation, quantization and integer-mass components separately.

**Severity:** Major.

### W4: Sensitivity and sampling scope are narrow

**Problem:** Grid width (q=0.5), temperature (T=1.2), mass bits (B=16) and minimum/maximum length were fixed for the main study; top-*k* and precision direction use one seed.

**Why it matters:** Correction sparsity could be specific to one hand-selected operating point.

**Suggestion:** Add a small prespecified sensitivity grid, report all trials, and use at least three seeds for the most influential ablations.

**Severity:** Major.

### W5: Uncertainty language needs tighter calibration

**Problem:** The Wilson interval over 20 prompt clusters is called conservative, but the prompt set is fixed and not sampled from a defined population.

**Why it matters:** A confidence interval cannot create population generality absent a sampling frame.

**Suggestion:** Label all intervals as descriptive resampling uncertainty for the fixed benchmark and add a sensitivity analysis over prompts or a held-out prompt collection.

**Severity:** Minor.

## Detailed Comments

- **Methods:** State the exact rounding rule for half-way negative values and verify parity between Python/Decimal and any serialized implementation.
- **Methods:** Explain whether reference generation itself uses the same quantized top-*k* contract rather than native model sampling; this affects interpretation of retained mass and semantic quality.
- **Results:** Report correction-count distribution, not only rate, and indicate whether corrections cluster after particular token ranks or sequence positions.
- **Statistics:** The absence of null-hypothesis tests is appropriate. The paper should report bootstrap method details and whether percentile intervals are stable under BCa or leave-one-prompt-out analysis.
- **Reproducibility:** Add a clean-machine invocation that verifies model fingerprint, bundle fingerprint and result signature.

## Questions for Authors

1. Was the operating point (q=0.5,T=1.2,B=16,k=2) selected before inspecting R044 outcomes, and where is that decision recorded?
2. What fraction of certificate corrections result from support mismatch, integer-count mismatch and random-boundary crossing respectively?
3. Does the certificate remain sparse if constructed on a second GPU stack from the same frozen reference tokens?
4. How large is the apportionment-only divergence for (B=16), and does increasing (B) change cross-precision agreement?

## Minor Issues

- Report model revision and complete directory fingerprint in the manuscript or supplement, not only in checkpoint metadata.
- Replace “scales” in the Results heading with “extends to 60 bilingual trajectories” unless a scaling law is tested.
- Clarify that the maximum trial correction rate of 6.15% is over variable-length trajectories.

## Contract Dimension Status

| Dimension | Status | Rationale |
|---|---|---|
| D1 methodology_rigor | warn | Good internal controls, but one environment, fixed prompts and narrow sensitivity. |
| D2 domain_accuracy | warn | Core numerical statements are correct; integer-apportionment fidelity remains incomplete. |
| D3 argumentative_coherence | pass | The manuscript separates deterministic recovery from empirical sparsity. |
| D4 cross_disciplinary_relevance | warn | Method may transfer, but portability is not independently shown. |
| D5 writing_and_structure | pass | Methods and estimands are sufficiently clear for assessment. |

## Numeric Dimension Scores

| Dimension | Score | Descriptor |
|---|---:|---|
| Originality | 70 | Strong |
| Methodological Rigor | 74 | Strong |
| Evidence Sufficiency | 64 | Adequate |
| Argument Coherence | 86 | Strong |
| Writing Quality | 82 | Strong |
| Weighted Average | 74 | Major Revision |

## Failure Conditions

- **F0:** not fired.
- **F1:** not fired.
- **F2:** candidate fired at panel aggregation because D1 and D2 are warn.
- **F3:** not fired by this review.

[CONTRACT-ACKNOWLEDGED]
