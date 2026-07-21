# Editorial Decision Package

## Manuscript Information

- **Title:** Sparse correction certificates recover stochastic language generation across numerical precision
- **Manuscript ID:** SPRC-STAGE3-001
- **Decision Date:** 2026-07-21
- **Review Round:** 1
- **Evaluation target:** Nature Communications-level standard, with specialist ML-systems venue calibration

## Part 1: Editorial Decision Letter

Dear Author(s),

Thank you for submitting this manuscript for simulated independent review. Four balanced reviewers and one bounded Devil's Advocate examined the paper under the frozen ARS `reviewer_full/v1` contract.

### Decision: Major Revision

The panel finds the target-specific replay result internally credible and unusually well audited. The conditional induction is coherent, all configured Qwen trials remain in the ledger, correction sparsity is reported separately from guaranteed corrected recovery, and package-size denominators are explicit. These strengths justify revision rather than rejection.

The present evidence does not yet support broad publication-level generality. All Qwen results come from one checkpoint and one physical GPU/software stack; the nominal external replay is a same-machine smoke test. The method also lacks direct, matched comparisons against native sparse delta logs, periodic checkpoints and complete traces. Consequently, the paper has not isolated whether its scientific contribution lies in the integer probability contract, sparse serialization, or simply target-conditioned delta recording. Distributional fidelity is incomplete because top-two retains only part of the source mass and the integer-apportionment term is not separately quantified. Finally, the practical workflow requires access to the intended target environment and pre-shared state, which must be included in any end-to-end efficiency claim.

The decision is mechanically required by the Sprint Contract. F2 fires because a majority, in fact all five panel members, recorded two or more mandatory dimensions at `warn` or worse. F3 also fires because D4 received `block` from the EIC and Devil's Advocate. No mandatory dimension received `block`, so the paper is reparable and F1 does not require rejection.

### Reviewer Summary

| Reviewer | Role | Recommendation | Confidence | Central concern |
|---|---|---|---:|---|
| EIC | Multidisciplinary computational-methods editor | Major Revision | 4 | Broad significance and direct novelty baseline |
| R1 | ML-systems methodology | Major Revision | 5 | Independent hardware, falsifiable endpoints and apportionment error |
| R2 | Sampling/steganography domain | Major Revision | 4 | Delta-log novelty, prior-work taxonomy and full distribution cost |
| R3 | Research software and auditability | Major Revision | 4 | Clean-room portability, shared state and archival readiness |
| DA | Bounded adversarial stress test | No vote | N/A | Strongest explanation is target-conditioned sparse delta encoding |

### Consensus Analysis

#### Points of Agreement

1. **[CONSENSUS-4] Internal result is credible but target-specific.** EIC cites bounded claims and serialization disclosure; R1 accepts the conditional proof and cluster-aware analysis; R2 finds the KL direction and claim boundaries correct; R3 finds the package identity/checkpoint design credible.
2. **[CONSENSUS-4] Independent target replay is required.** Every balanced reviewer identifies the absence of a second physical GPU/software stack as a major limitation.
3. **[CONSENSUS-4] Exact corrected recovery must not be the sole empirical contribution.** The panel agrees that manifest completeness guarantees recovery; correction density, end-to-end bytes, distribution cost and portability are the falsifiable outcomes.
4. **[CONSENSUS-3] End-to-end assumptions need matched baselines.** EIC, R2 and R3 explicitly require equalized target access, shared state and package boundaries. R1 focuses instead on primary-endpoint and numerical sensitivity, but does not oppose the baseline request.
5. **[CONSENSUS-3] Submission artifacts are incomplete.** EIC, R1 and R3 require immutable/provenance-complete public artifacts or a clean-machine invocation. R2 treats archival readiness as secondary to domain novelty.

#### Points of Disagreement

**Disagreement 1: Is the contribution already methodologically strong?**

- R1 gives D5 `pass` and regards the conditional method as sufficiently specified for assessment.
- EIC, R2 and R3 give D5 `warn` because a reader-facing algorithm, taxonomy, archive and governance metadata are incomplete.
- **Type:** Severity difference.
- **Editor's resolution:** The mathematics is assessable, but submission readiness remains a required revision. R1's methodological judgment is preserved; the presentation issues are classified separately under P2/P3.

**Disagreement 2: Are the domain claims accurate enough?**

- R3 gives D2 `pass`, emphasizing honest operational boundaries.
- EIC, R1 and R2 give D2 `warn`, emphasizing the missing direct replay baseline and integer-apportionment fidelity term.
- **Type:** Perspective difference.
- **Editor's resolution:** Defer domain-mechanism assessment to R2 and numerical fidelity to R1. D2 remains `warn` until the comparison matrix and apportionment audit are added.

**Disagreement 3: Is broad venue fit reparable without a second model?**

- EIC and DA block D4 at the present evidence scale.
- R1-R3 warn rather than block because a specialist reproducibility contribution remains credible.
- **Type:** Severity and venue-standard difference.
- **Editor's resolution:** Independent hardware is mandatory for any submission. A second model family is mandatory only if retaining a broad multidisciplinary target; otherwise the manuscript should explicitly target TMLR or Machine Learning: Science and Technology.

### Devil's Advocate Disposition

The DA reports no CRITICAL foundation-collapse finding. Its strongest counter-argument, that SPRC is target-conditioned sparse delta encoding, is corroborated by EIC and R2 as an unresolved novelty risk. The editor considers this major but reparable: the author must add matched baselines and identify which measured gain is attributable to the probability contract rather than to sparse storage alone.

## Part 2: Required Revisions

| ID | Revision item | Source | Severity | Acceptance criterion |
|---|---|---|---|---|
| R1 | Run the frozen bundle on an independent physical GPU/software stack | EIC, R1, R2, R3 | Major | No regenerated reference artifacts; publish fingerprints, command log, exact recovery and correction/byte outcomes, including failures |
| R2 | Add matched full-trace, native-delta and checkpoint/replay baselines | EIC, R2, DA | Major | Equal target access, shared-state boundary, sequence set and metadata; report bytes, passes, time and recovery |
| R3 | Reframe corrected exactness as an integrity gate and choose a falsifiable empirical primary endpoint | R1, EIC, DA | Major | Abstract, Results and Methods consistently prioritize correction/byte/portability outcomes |
| R4 | Complete the distribution audit | R1, R2, DA | Major | Isolate full-logit quantization, support truncation and integer-apportionment components; state directions and infinities correctly |
| R5 | Add prespecified parameter sensitivity | R1, DA | Major | At minimum vary (q,T,B,k) around the chosen point with all trials retained and decision provenance stated |
| R6 | Define the operational trust, state and cost model | EIC, R3, DA | Major | Data-flow diagram/table lists actors, target access, shared artifacts, per-model/per-prompt/per-trajectory costs and privacy exposure |
| R7 | Resolve venue positioning | EIC | Major | Add second model/broader evidence for multidisciplinary claim, or retarget title/framing to specialist ML systems |
| R8 | Freeze submission artifacts and declarations | EIC, R1, R3 | Major | Immutable archive/DOI, public checksums, install/replay command, authorship, contributions, funding and conflicts completed |

## Part 3: Suggested Revisions

| ID | Revision item | Source | Priority | Expected improvement |
|---|---|---|---|---|
| S1 | Add a prior-work mechanism table spanning replay logs, SparSamp, range coding, list decoding, dyadic coding and ReTokSync | R2 | P2 | Makes novelty and composability auditable |
| S2 | Add reader-facing pseudocode and complexity | EIC, R2 | P2 | Separates construction, transmission and replay |
| S3 | Replace internal R0xx labels in the main paper with stable artifact names | EIC, R3 | P3 | Improves readability and publication style |
| S4 | Add native generation quality evidence or keep quality entirely outside the contribution | EIC, R2 | P2 | Prevents punctuation completion from serving as a semantic proxy |
| S5 | Add license and retention/access statements for code, prompts, outputs and bundles | R3 | P2 | Completes governance and reuse information |

### Revision Deadline

- **Recommended period:** 6-8 weeks
- **Re-review required:** Yes

The revised manuscript should include a point-by-point response and a machine-readable mapping from every required revision to the new artifact, analysis and manuscript location.

Sincerely,

Simulated Editorial Panel
