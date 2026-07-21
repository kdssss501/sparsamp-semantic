# Devil's Advocate Review

## Manuscript Information

- **Title:** Sparse correction certificates recover stochastic language generation across numerical precision
- **Manuscript ID:** SPRC-STAGE3-001
- **Review Date:** 2026-07-21

## Scope

The manuscript deserves credit for preserving failed trials, exposing three serialization boundaries and explicitly rejecting target-independent, zero-KL and semantic-equivalence claims. This review nevertheless adopts the strongest defensible skeptical position. It does not issue a balanced recommendation or numeric score.

## Strongest Counter-Argument

The proposed certificate can be described more simply as target-conditioned sparse delta encoding. The constructor already possesses the complete reference token trajectory and runs the intended target model on every reference prefix. Whenever the target's deterministic seeded choice differs, it writes the correct reference token and position. Exact recovery is then inevitable if replay uses the same target function and complete delta list; it is not evidence that the integer probability contract solved cross-precision nondeterminism. The only nontrivial result is that the delta list happened to be sparse for one Qwen2.5-1.5B checkpoint, one RTX 3060 Laptop stack, one quantization grid, one temperature, a heavily truncated top-two generator and 20 hand-fixed prompts. That operating point retains only 0.734 of source probability mass in the reported ablation, so stability may have been purchased by changing the generator rather than by robustly coupling native stochastic inference. The compact 24.76% package further assumes that the bundle, model and environment identity are already shared, while construction itself requires target access. A conventional full token trace is simpler, target-independent and costs only a few kilobytes for these short outputs. Until the paper compares against native delta logs, checkpoints and full traces under identical end-to-end assumptions, the most parsimonious interpretation is a careful audit format with narrow empirical compression, not a broadly new replay method.

## Issue List

### CRITICAL

No foundation-collapse finding is established from the current manuscript. The bounded claim “a complete target-specific manifest reconstructs the tested trajectories with sparse corrections” remains logically valid.

### MAJOR

| # | Dimension | Issue Description | Location |
|---|---|---|---|
| 1 | Core thesis | Corrected exactness is guaranteed because the certificate stores every discrepant reference token; the paper needs a falsifiable primary empirical endpoint. | Abstract; Results, “Sparse certificates separate exact replay” |
| 2 | Alternative path | No native delta-log, periodic-checkpoint or full-trace workflow is compared under the same target-access and package-boundary assumptions. | Introduction; Replay-package Results |
| 3 | Confirmation bias | The main operating point fixes top-two, (q=0.5), (T=1.2), (B=16), but the draft does not show that these choices were frozen before outcome inspection. | Methods, “Quantized next-token snapshot” |
| 4 | Overgeneralization | Broad stochastic-language-generation wording is supported by one small model, one GPU and one software stack. | Title; Abstract; Discussion |
| 5 | Stronger counter-narrative | The 2.16% correction rate may be primarily a consequence of top-two truncation, which removes roughly one quarter of source mass, rather than precision hardening. | Results, “Contract width” |
| 6 | Evidence gap | Integer apportionment divergence and native-generation quality are unmeasured, so the fidelity cost is incomplete. | Methods, “Integer probability contract”; Discussion |
| 7 | Deployment logic | Construction requires the intended target environment, limiting portability to environments known in advance. | Methods, “Sparse precision replay certificate” |

### MINOR

| # | Dimension | Issue Description | Location |
|---|---|---|---|
| 1 | So what | For 75-token outputs, a full trace is already small; the paper does not identify the sequence length or reuse point at which certification becomes materially valuable. | Replay-package Results |
| 2 | Naming | “Certificate” may imply third-party verifiability, while the object is a correction manifest conditional on trusted identities. | Title; Introduction |
| 3 | Evidence selection | The literature set is small and lacks a systematic search or direct deterministic-replay/logging review. | Introduction; References |
| 4 | Stakeholder | Privacy leakage from correction tokens and prompt/bundle identities is not discussed. | Data availability; Discussion |

## Ignored Alternative Explanations and Paths

1. **Truncation-induced stability:** top-two sampling reduces the number of decision boundaries and may explain sparsity without the integer contract being uniquely effective.
2. **Native sparse delta:** running the target choice on the reference prefix and recording mismatches may yield similar sparsity without quantized probability counts.
3. **Periodic checkpoints:** storing occasional full-prefix checkpoints plus deterministic suffix replay may offer a better compute/storage trade-off for long sequences.
4. **Full trace:** for short outputs, direct token storage is target-independent, simple and potentially preferable once all metadata is included.

## Missing Stakeholder Perspectives

- An independent artifact consumer who does not share the source machine's model cache or exact kernel stack.
- A benchmark maintainer deciding whether exact stochastic trajectories are necessary versus output-level score reproducibility.
- A privacy reviewer assessing what the sparse corrections reveal about the hidden reference output.
- A systems operator accounting for the extra target pass during construction and replay.

## Contract Risk Status

These are risk flags, not balanced reviewer scores.

| Dimension | Status | Rationale |
|---|---|---|
| D1 methodology_rigor | warn | The invariant is implemented convincingly, but the empirical operating point and portability are narrowly tested. |
| D2 domain_accuracy | warn | Statements are careful, yet the closest replay/logging alternatives are not established. |
| D3 argumentative_coherence | pass | The narrow target-specific reconstruction conclusion follows when all preconditions hold. |
| D4 cross_disciplinary_relevance | block | A field-wide impact claim cannot survive the one-model, one-stack and target-access constraints. |
| D5 writing_and_structure | pass | Assumptions and limitations are mostly visible, despite the potentially inflated “certificate” framing. |

## Failure Conditions

- **F0:** not fired.
- **F1:** not fired; no mandatory risk is blocked.
- **F2:** candidate fired at panel aggregation because D1 and D2 are warn.
- **F3:** fired; D4 is blocked.

## Observations (Non-Defects)

- Even if the algorithmic novelty is reduced, the artifact may remain valuable as a benchmark and audit format for finite-precision divergence.
- The manuscript's explicit negative claims make a constructive revision possible without retracting the central same-stack result.

[CONTRACT-ACKNOWLEDGED]
