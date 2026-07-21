# Peer Review Report - EIC

## Manuscript Information

- **Title:** Sparse correction certificates recover stochastic language generation across numerical precision
- **Manuscript ID:** SPRC-STAGE3-001
- **Review Date:** 2026-07-21
- **Review Round:** 1

## Reviewer Information

- **Role:** Editor-in-Chief
- **Identity:** Computational-methods editor for reproducibility, trustworthy AI and machine-learning systems at a multidisciplinary venue.
- **Focus:** Broad significance, novelty, claim-evidence alignment and journal fit.

## Overall Assessment

- **Recommendation:** Major Revision
- **Confidence:** 4/5

The manuscript introduces sparse precision replay certificates, a target-specific record that corrects stochastic token decisions when a second numerical precision would diverge from a selected reference trajectory. Its strongest evidence is internally coherent: 60/60 FP16-to-BF16 Qwen trajectories were recovered after correction versus 10/60 without correction, with a mean 2.16% correction rate, and the paper explicitly limits the result to one model and one GPU stack. The artifact audit, separation of package boundaries and conditional replay proof are unusually transparent. However, the current evidence supports a focused ML-systems reproducibility paper more readily than a broad multidisciplinary contribution. Independent hardware replay is absent, the novelty distinction from sparse delta/replay logs is argued mainly in prose rather than through a direct baseline, and no semantic-quality evidence is reported. I therefore recommend major revision, with a credible path to a strong specialist methods venue after external validation and sharper positioning.

## Strengths

### S1: Claims are unusually well bounded

The Abstract ends by excluding target-independent determinism, zero divergence and cross-hardware generality. The Discussion repeats these boundaries and explicitly calls the external replay a same-machine smoke test. This restraint materially improves editorial trust.

### S2: Exactness and sparsity are separated

The Results section distinguishes a by-construction replay invariant from the empirical observation that corrections affect 2.16% of token positions. This is the correct conceptual separation and prevents 60/60 recovery from being misrepresented as an empirical discovery by itself.

### S3: Serialization denominators are disclosed

The package audit reports 6.65% payload-only, 24.76% compact referenced-package and 63.89% self-contained JSON ratios as different estimands. That disclosure avoids a common compression-paper error in which header or shared-state costs are hidden.

### S4: Compatibility reproduction adds artifact credibility

The unchanged SparSamp implementation achieved 846/846 exact no-ambiguity decodes and all 16 capacity checks within 5% of published values. The dependency mismatch is disclosed as a limitation rather than ignored.

## Weaknesses

### W1: Broad-significance evidence is not yet established

**Problem:** All Qwen evidence comes from one 1.5B checkpoint, one RTX 3060 Laptop GPU and one software stack; the only external-package run is same-machine.

**Why it matters:** The title and Nature Communications-style positioning imply a phenomenon of wider computational significance, while the data establish a target-specific local result.

**Suggestion:** Run the frozen R047 bundle on at least one genuinely independent accelerator/software stack, ideally with a second model family, or retarget the paper explicitly to a specialist reproducibility venue.

**Severity:** Major.

### W2: Novelty versus sparse replay logs is under-demonstrated

**Problem:** The paper asserts an intermediate contribution between strict determinism and full token traces, but provides no direct empirical or formal comparison with delta encoding, periodic checkpointing or deterministic replay-log baselines.

**Why it matters:** A skeptical reader can describe the certificate as a target-conditioned sparse delta trace plus an integer sampler.

**Suggestion:** Add a mechanism comparison table and a matched baseline experiment that equalizes recipient state, construction passes and package boundary.

**Severity:** Major.

### W3: Practical value is not separated from construction cost

**Problem:** Certificate construction evaluates the target precision on every reference prefix and corrected replay requires another target pass. The paper reports throughput, but the intended workflow and when the construction cost is amortized remain vague.

**Why it matters:** A method that requires access to the exact target before transfer may be useful for audit snapshots but not for arbitrary portability.

**Suggestion:** Define two concrete use cases, their trust/shared-state assumptions and an end-to-end cost model.

**Severity:** Major.

### W4: Submission readiness is incomplete

**Problem:** Author metadata, funding, contributions, competing interests and archival DOI are unresolved; no independent semantic evaluation exists.

**Why it matters:** These omissions prevent formal submission and weaken the claim that recovered trajectories remain useful language outputs.

**Suggestion:** Resolve metadata and archive provenance; either collect an approved blinded evaluation or keep all quality claims out of the main contribution.

**Severity:** Minor for scientific validity, major for submission readiness.

## Detailed Comments

- **Title and Abstract:** Accurate within the target-specific caveat, but the title could add “target-specific” if external validation remains absent.
- **Introduction:** The gap is clear. A direct comparison with replay logging and deterministic execution should appear before the contribution statement.
- **Results:** Table 1 is informative, but the number of corrections and package bytes should be shown together for the main 60-trial set or the seed-0 limitation highlighted in the table title.
- **Discussion:** The limitations are strong. The broad-use paragraph should foreground recipient access to the shared bundle and exact target contract.
- **Data/Code Availability:** An immutable release and DOI are required before submission.

## Questions for Authors

1. Which real workflow permits certificate construction against the recipient's exact target environment, and what state is shared before the certificate is sent?
2. What result would distinguish SPRC scientifically from a compact delta log generated by running reference and target trajectories on the same prefix?
3. Can the frozen package be replayed on a second physical GPU without regenerating the reference bundle?
4. Is the intended venue broad multidisciplinary or specialist ML systems, and which evidence supports that choice?

## Minor Issues

- Replace internal labels such as `R047`, `R048` and `ETHICS_PENDING` with reader-facing artifact identifiers or move them to the supplement.
- Add a conventional algorithm box for certificate construction and replay.
- Add the missing independent trace entry for Table 1.

## Contract Dimension Status

| Dimension | Status | Rationale |
|---|---|---|
| D1 methodology_rigor | warn | Internally rigorous, but no independent hardware validation and limited model/prompt scope. |
| D2 domain_accuracy | warn | Accurate bounded language, but novelty against direct replay baselines is incomplete. |
| D3 argumentative_coherence | pass | The central target-specific claim follows from the proof and measurements. |
| D4 cross_disciplinary_relevance | block | Broad multidisciplinary significance is not substantiated beyond one model and stack. |
| D5 writing_and_structure | warn | Clear draft, but metadata, archival record and reader-facing algorithm are incomplete. |

## Numeric Dimension Scores

| Dimension | Score | Descriptor |
|---|---:|---|
| Originality | 68 | Adequate |
| Methodological Rigor | 76 | Strong |
| Evidence Sufficiency | 61 | Adequate |
| Argument Coherence | 84 | Strong |
| Writing Quality | 78 | Strong |
| Weighted Average | 72 | Major Revision |

## Failure Conditions

- **F0:** not fired.
- **F1:** not fired; no mandatory dimension is blocked.
- **F2:** candidate fired at panel aggregation because this review has two mandatory warnings.
- **F3:** fired; D4 is blocked, requiring at least Major Revision.

[CONTRACT-ACKNOWLEDGED]
