# Citation Audit

**Search date:** 2026-07-21
**Scope:** direct scholarly literature for numerical LLM reproducibility, inference verification, probability-contract sampling and finite-precision effects. Nature/CNS journal filtering was not applied because the user requested Nature writing style rather than Nature-only sources.
**Metadata sources:** arXiv API, Crossref DOI records, ACL Anthology and the USENIX official proceedings page.

## Claim-to-source mapping

| Segment | Manuscript claim | Reference | Support | Verification note |
|---|---|---|---|---|
| S001 | Hardware, batch and numerical configuration can change LLM responses and evaluation outcomes. | Yuan et al., arXiv:2506.09501 | Strong support | Abstract directly studies numerical nondeterminism across GPU and batch configurations. Full-text details should be rechecked at submission. |
| S002 | Inference verification can compare output tokens with a trusted seeded reference despite benign nondeterminism. | Karvonen et al., arXiv:2511.20621 | Strong support | Abstract directly describes Token-DiFR and nondeterministic inference verification. |
| S003 | Sparse sampling couples pseudo-random values to generative-model sampling under a probability-preservation objective. | Wang et al., USENIX Security 2025 | Strong support | Publication metadata, pages and abstract verified on USENIX official page. |
| S004 | Range coding provides an efficient shared-random sampling construction for linguistic generation. | Yan and Murawaki, ACL 2026 | Strong support | Title, DOI and pages verified through ACL Anthology. Detailed theorem wording should follow the paper, not the local audit. |
| S005 | Finite-precision artifacts can create low-probability-vanishing signals in LLM sampling pipelines. | Cao et al., Findings of ACL 2026 | Strong support | Title, DOI and pages verified through ACL Anthology. |
| S006 | Qwen2.5 is an open-weight instruction-model family. | Qwen Team, arXiv:2412.15115 | Background support | Official arXiv metadata verified; manuscript uses the local 1.5B checkpoint. |
| S007 | List decoding targets higher-capacity provably secure language-model sampling. | Pang and Bai, arXiv:2604.21394 | Strong support | Abstract directly states list decoding, suffix matching and capacity objective. Preprint status. |
| S008 | Rate-constrained dyadic approximation trades coding rate against total variation. | Bar-Lev et al., arXiv:2605.05837 | Strong support | Abstract directly states the rate-TV optimization. Preprint status. |
| S009 | ReTokSync addresses re-tokenization ambiguity through sparse corrective resets. | Wang et al., arXiv:2604.25486 | Strong support | Abstract directly states tokenization synchronization mechanism. Preprint status. |

## Excluded or deferred citations

- ANStega was not added because its full text, authorship and final venue metadata were not verified in this pass.
- Broad claims about all LLM inference stacks were avoided; available evidence supports configuration-sensitive nondeterminism, not universal failure.
- No paper is cited as evidence that SPRCs are novel. A formal novelty claim requires a broader systematic search and code-level comparison.
- Preprints dated 2026 must be rechecked for revised versions, peer-reviewed publication and corrections before submission.

## Reference-manager export

The verified metadata used in this draft is exported to `paper/references.enw`. Missing DOI, volume, issue or page fields are intentionally left absent for arXiv-only records.
