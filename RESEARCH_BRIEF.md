# Research Brief: Precision-Hardened Probability Contracts

**Updated:** 2026-07-21  
**Reference:** SparSamp, USENIX Security 2025, arXiv:2503.19499

## Research question

Can a public discrete next-token contract make numerical-precision disagreements sparse enough that a target-specific correction certificate reconstructs a stochastic language-model trajectory exactly at substantially lower record cost than storing the full token trace?

## Current thesis

For a known model, tokenizer, prompt, public sampling configuration and target numerical environment, a canonical integer probability contract plus a complete sparse correction manifest gives exact token replay. Exactness follows from the construction; the empirical contribution is that corrections remain sparse in the tested Qwen FP16/BF16 setting and expose a measurable distribution-fidelity versus precision-stability Pareto frontier.

## Main evidence

| Evidence | Result | Boundary |
|---|---:|---|
| Official SparSamp Basic compatibility test | 105 tokens, 576 bits, 5.486 bits/token, exact decode | Unchanged artifact algorithm; modern dependency stack |
| Official R002 matrix | 1,200 configured, 1,193 complete, 7 budget exhausted | Compatibility reproduction, not strict Torch 2.2.2 |
| R002 decode gate | 846/846 completed no-TA trials exact | 347 completed TA trials reported separately |
| R002 capacity gate | 16/16 comparisons within 5%; maximum error 4.12% | Speed descriptive because hardware differs |
| Qwen main replay | 60/60 corrected, 10/60 uncorrected | One Qwen checkpoint and one GPU stack |
| Qwen correction density | 2.16%, prompt-cluster 95% CI 1.80%-2.53% | Fixed prompt set, three public seeds |
| Precision reversal | 20/20 BF16 to FP16 corrected replay | One seed, same GPU stack |
| Contract-width ablation | top-4 retains more mass but does not reduce corrections | Different reference trajectories by design |
| Serialization audit | 6.65% payload-only; 24.76% referenced package; 63.89% self-contained JSON | Three different estimands |
| Manuscript claim audit | 22/22 before R002 integration | Re-run required after every manuscript change |

## Mathematical boundary

- A complete target-specific manifest gives exact replay by induction on the reconstructed prefix.
- Sparse correction density is empirical and is not guaranteed by the induction proof.
- Conditioning on retained support contributes (D_{KL}(Q\|\widetilde P)=-\log Z).
- Removing positive source support makes the opposite KL direction infinite.
- Full-logit quantization, support truncation and integer apportionment are separate approximation layers.
- No current result supports zero KL, full-distribution preservation or target-independent determinism.

## Reproducibility boundary

- Official reproduction uses Zenodo 15025436, 100 deterministic IMDB contexts and 12 unique configurations.
- The artifact comment says 100 contexts but its script samples 10; the reproduction follows the paper-level 100-context protocol.
- Transformers 4.57.6 is incompatible with the artifact's legacy cache API; Transformers 4.41.2 succeeds.
- A strict Torch 2.2.2 CUDA environment remains unavailable because the upstream wheel download repeatedly terminated.
- Large block lengths produced seven 200-token budget exhaustions, retained as limitations rather than hidden exclusions.

## Paper state

- English submission-preparation manuscript and independent Chinese abstract exist.
- Figure 1-4 and Supplementary Figure 1 have PDF/PNG source artifacts and machine-readable source data.
- Official R002 results are incorporated into the main manuscript and Supplementary Information.
- Remaining blocking steps are Stage 2.5 integrity review, simulated peer review, author metadata and immutable archive DOI.

## Prohibited claims

- Universal cross-hardware determinism.
- Distribution preserving, zero KL, secure or undetectable.
- Semantic equivalence to native generation without human data.
- Independent hardware replication based on the same-machine R047 smoke test.
- Strict official dependency reproduction based on the compatibility environment.

## Next mandatory gate

Complete the academic-pipeline Stage 2 writing checkpoint, then run Stage 2.5 reference, citation-context, statistical-data, originality, claim and seven-mode AI research failure verification. The pipeline must not move to simulated review until the user confirms the Stage 2 deliverables.
