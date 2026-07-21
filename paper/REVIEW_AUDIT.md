# Nature-Style Reviewer Audit

**Draft reviewed:** `paper/MANUSCRIPT_DRAFT.md` v0.1
**Audit date:** 2026-07-21
**Verdict:** coherent full draft; not submission-ready

## Contribution

| Question | Status | Evidence or action |
|---|---|---|
| Does the paper give new knowledge? | Pass with boundary | It shows that cross-precision token-choice disagreements can remain sparse even when full stochastic trajectories diverge, and quantifies a top-*k* fidelity/reliability trade-off. |
| Is the method more than storing a full output? | Pass empirically with explicit boundary | R049 reports 6.65% payload-only, 24.76% compact referenced-package and 63.89% self-contained JSON-package ratios against matching full traces. The compact result assumes a transferred shared bundle. |
| Could the method be dismissed as delta encoding? | Needs revision | Exactness follows from the manifest. The paper must emphasize that the discrete contract is designed to make the delta sparse and must add component ablations or compare against seed-only and full trace in one primary figure. |
| Is novelty established against all close work? | Needs new literature audit | Direct sources are verified, but no systematic novelty review has been completed. Avoid "first" or universal novelty language. |

## Writing clarity

| Question | Status | Evidence or action |
|---|---|---|
| Is the central claim explicit? | Pass | Abstract and final Introduction paragraph state target-specific exact replay and its boundary. |
| Is exactness separated from sparsity? | Pass | Results state the induction argument and identify sparsity as the empirical endpoint. |
| Are terms stable? | Pass | "reference", "target", "contract", "manifest", "correction density" and "truncation component" are used consistently. |
| Is the method reproducible? | Partial, improved | R047 adds a full model-directory fingerprint, reference-only bundle, exact CLI and checkpointed fresh target replay. Driver and independent target metadata still need preservation in an external result. |

## Experimental strength

| Question | Status | Evidence or action |
|---|---|---|
| Is the primary result strong in absolute terms? | Pass within scope | 60/60 corrected trajectories at 2.16% mean corrections; uncorrected exact replay is 10/60. |
| Are multiple settings tested? | Partial | Two languages, three seeds and both precision directions are included, but only one Qwen checkpoint and one GPU stack are tested. |
| Are negative findings retained? | Pass | Top-four completion and contract-agreement decreases are reported; no failed trial was excluded. |
| Is practical cost fully measured? | Partial | R049 consolidates payload, self-contained and referenced-package bytes plus separate construction/replay throughput. A matched FP32 cost comparison and independent-hardware timing remain missing. |

## Evaluation completeness

| Question | Status | Evidence or action |
|---|---|---|
| Are key design choices ablated? | Partial | Top-two/top-four and precision direction are covered. Add no-quantization, no-canonical-order and seed-only rows from frozen configurations or clearly move them to supplementary evidence. |
| Are strong baselines included? | Needs new experiment | Current baseline is uncorrected seed replay and full trace. Add higher-precision execution and, where feasible, deterministic-kernel or replay-verification comparisons. |
| Is semantic quality evaluated? | Materials ready, data absent | R048 generated 20 matched native-top-16/top-two/top-four sets and an offline blinded evaluator. Ethics status remains `ETHICS_PENDING`; no ratings exist. |
| Is cross-hardware generality evaluated? | Needs new experiment | Run the frozen top-two configuration on a second GPU/CUDA stack. |

## Method soundness

| Question | Status | Evidence or action |
|---|---|---|
| Are assumptions disclosed? | Pass | Target-specific construction, shared model/tokenizer/prompt and one-stack scope are explicit. |
| Is distribution accounting correct? | Pass with unresolved term | Reverse-KL truncation and full-logit quantization are separate. Integer-apportionment divergence remains unisolated and is disclosed. |
| Does top-*k* introduce a problematic quality trade-off? | Needs new experiment | Top-four lowers the truncation component but reduces structural completion in one seed. Human evaluation is needed to interpret net value. |
| Does the method survive public-text re-tokenization? | Not tested | Current claim is token-ID replay only; keep text-channel synchronization outside the principal claim. |

## Statistical audit

- Independent unit for continuous inference: prompt cluster (`n=20`), with three public seeds retained within each cluster.
- Main intervals: 10,000 prompt-cluster bootstrap resamples with public seed 20260720.
- Ablation comparisons: paired by prompt and seed; not paired by token trajectory.
- No trial exclusions and no null-hypothesis significance claims.
- The prompt set is fixed rather than randomly sampled; confidence intervals quantify internal prompt heterogeneity, not a defined population sampling process.
- The top-*k* and reverse-direction ablations use one seed, which limits claims about stochastic variability.

## Citation audit

- USENIX and ACL publication records were checked on official pages.
- arXiv references were checked through the official API on 2026-07-20.
- References 1, 2 and 7-9 remain preprints in the current draft and require version/status checks before submission.
- No citation currently supports a priority claim, and the manuscript makes none.

## Required before submission

1. Independent hardware/CUDA replication of the frozen top-two protocol.
2. Blinded semantic comparison against native generation.
3. Matched FP32 runtime/cost comparison; R049 already supplies target construction/replay and serialization boundaries.
4. Component ablations or a precise supplementary mapping to R022-R023 evidence.
5. Immutable code/data archive and author metadata.
6. Full novelty search followed by a second reviewer audit.
