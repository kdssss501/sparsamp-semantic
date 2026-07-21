# Peer Review Report - R3 Perspective

## Manuscript Information

- **Title:** Sparse correction certificates recover stochastic language generation across numerical precision
- **Manuscript ID:** SPRC-STAGE3-001
- **Review Date:** 2026-07-21
- **Review Round:** 1

## Reviewer Information

- **Role:** Peer Reviewer 3 - Perspective
- **Identity:** Research-software and ML-auditability specialist focused on artifact portability, governance and deployment.
- **Focus:** Operational usefulness, artifact boundaries, reproducibility for third parties and stakeholder costs.

## Overall Assessment

- **Recommendation:** Major Revision
- **Confidence:** 4/5

The manuscript offers a useful audit abstraction: instead of demanding bitwise agreement or storing every generated token, it records the positions at which a known target environment would depart from a reference trajectory. The package-boundary analysis is a major strength because it demonstrates how a 6.65% payload ratio becomes 24.76% with referenced metadata and 63.89% in self-contained JSON. The work also exposes correction positions as interpretable evidence of numerical divergence. Yet its practical workflow is narrower than the headline suggests. Construction requires running the target environment on every reference prefix, recipients need matching model/tokenizer/configuration state, and the frozen bundle has not been tested on an independent machine. No immutable archive exists, raw outputs remain local and user-facing quality is unmeasured. The paper can become a valuable research-software contribution, but it needs an explicit trust and cost model plus an independent artifact exercise.

## Strengths

### S1: Multiple audit boundaries are made visible

The seed-0 package audit distinguishes raw correction bytes, a referenced binary package and a self-contained JSON package. This is exactly the transparency required for responsible compression claims.

### S2: Identity and configuration are first-class

The binary header references bundle, model and target-environment SHA-256 identities, while checkpoint merging rejects configuration mismatches. These are strong research-software practices.

### S3: Checkpointed execution supports recovery

Trials are written atomically and target replay can resume. This reduces the risk of losing expensive progress and supports inspectable partial runs.

### S4: Governance limitations are explicit

The paper does not report unapproved human evaluation and marks the prepared blinded study as pending. It also discloses AI-assisted work and author responsibility.

## Weaknesses

### W1: No independent consumer has exercised the artifact

**Problem:** The package preparation and target replay were performed on the source machine.

**Why it matters:** A research artifact is portable only when an independent environment can verify identities and obtain the same outcome without hidden local state.

**Suggestion:** Conduct a clean-room replay on another physical machine; publish the command log, environment manifest, validation output and any failure.

**Severity:** Major.

### W2: Shared-state and trust assumptions are not operationalized

**Problem:** The compact package assumes a pre-shared bundle, model and target contract, while construction already has access to the target environment.

**Why it matters:** Storage, transfer, privacy and trust costs may dominate the sparse payload in realistic settings.

**Suggestion:** Add a data-flow diagram and threat/assumption table listing who holds the prompt, reference tokens, model weights, target hardware and manifest at each stage.

**Severity:** Major.

### W3: Reproducibility assets are not yet archival

**Problem:** There is no immutable DOI; the 1,200-trial checkpoint and frozen bundle are transferred separately; raw outputs are not versioned.

**Why it matters:** A Git tag alone is mutable at the hosting-account level and may not preserve large artifacts.

**Suggestion:** Deposit code, aggregate data, frozen bundles, checksums and an environment manifest in an immutable archive.

**Severity:** Major.

### W4: The user value of exact token replay is underdeveloped

**Problem:** The paper gives audit and reconstruction motivations but no worked incident, benchmark comparison or stakeholder workflow.

**Why it matters:** Readers cannot assess whether exact trajectory recovery is worth the second target pass and shared state.

**Suggestion:** Add one non-sensitive use-case walkthrough, such as reproducing a benchmark answer selected in FP16 on a BF16 evaluation service, and compare storage/compute with a full trace.

**Severity:** Major.

### W5: Metadata placeholders prevent governance review

**Problem:** Authorship, contributions, funding, conflicts and archive location are unresolved.

**Why it matters:** Accountability and conflict assessment are part of artifact governance, not merely formatting.

**Suggestion:** Complete all declarations before the next review round.

**Severity:** Minor.

## Detailed Comments

- **Abstract:** Add the assumption that certificate construction can evaluate the intended target environment.
- **Results:** Put the three package boundaries in one compact table with “pre-shared state” as a column.
- **Methods:** Specify what information is sensitive and what is public; hashes identify assets but do not provide them.
- **Data Availability:** Clarify retention policy for raw prompts/outputs and how an auditor obtains excluded artifacts.
- **Code Availability:** Pin dependency lockfiles and document a clean installation path.

## Questions for Authors

1. Who constructs a certificate in the intended deployment, and how do they access the recipient's exact target stack?
2. Which artifacts must be transferred once, per model, per prompt and per trajectory?
3. Can an auditor verify the reported result using only public immutable artifacts?
4. What privacy exposure is created by correction tokens and reference-bundle identifiers?

## Minor Issues

- Replace local experiment identifiers with stable public artifact names.
- Add license information for code, prompts, model-derived outputs and the official artifact.
- Document expected disk, GPU-memory and wall-clock requirements for the 60-trial protocol.

## Contract Dimension Status

| Dimension | Status | Rationale |
|---|---|---|
| D1 methodology_rigor | warn | Strong internal provenance, but no independent clean-room validation. |
| D2 domain_accuracy | pass | Practical boundaries and target-specific scope are accurately stated. |
| D3 argumentative_coherence | warn | Operational value depends on shared state and target access that are not foregrounded. |
| D4 cross_disciplinary_relevance | warn | Auditability use case is plausible but lacks a worked external workflow. |
| D5 writing_and_structure | warn | Availability and governance sections remain incomplete. |

## Numeric Dimension Scores

| Dimension | Score | Descriptor |
|---|---:|---|
| Originality | 69 | Adequate |
| Methodological Rigor | 73 | Strong |
| Evidence Sufficiency | 62 | Adequate |
| Argument Coherence | 75 | Strong |
| Writing Quality | 76 | Strong |
| Significance and Impact | 64 | Adequate |
| Weighted Average | 70 | Major Revision |

## Failure Conditions

- **F0:** not fired.
- **F1:** not fired.
- **F2:** candidate fired at panel aggregation because D1 and D3 are warn.
- **F3:** not fired by this review.

[CONTRACT-ACKNOWLEDGED]
