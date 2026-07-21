# Stage 2.5 Academic Integrity Verification Report

## Verification mode

Initial verification (pre-review), completed 2026-07-21.

## Verdict

**PASS_WITH_NOTES**

The manuscript is released to the Stage 2.5 mandatory checkpoint. No fabricated
reference, bibliographic mismatch, unsupported numerical result, major claim distortion,
unverifiable claim, malformed experiment provenance entry, or unresolved AI research
failure mode was found. The notes concern author-owned metadata and reporting maturity;
they do not change the factual verdict.

## Verification summary

| Category | Total | Passed | Issues or notes |
|---|---:|---:|---|
| Reference existence | 9 | 9 | None |
| Bibliographic accuracy | 9 | 9 | Preprints retain version-sensitive metadata |
| Ghost citations | 9 cited / 9 listed | 9 / 9 | 0 orphan, 0 dangling |
| Citation context | 9 references, all citing contexts | 9 | 100% checked, above the 30% gate |
| Statistical and result claims | 12 | 12 | All traced to primary metadata or saved experiment artifacts |
| Internal numerical consistency | 4 core analyses | 4 | R002, R044, R046 and R049 recomputed |
| Figure packages | 4 | 4 | Initial trace-format failure corrected and re-verified |
| Originality screening | 21 / 59 paragraphs | 21 | 35.6%; no CLOSE_MATCH or VERBATIM result |
| Self-plagiarism | Not run | N/A | Author identity and publication list not yet supplied |
| Claim verification | 12 | 12 | 12 VERIFIED, 0 distorted or unverifiable |
| Experiment alignment | 8 | 8 | 8 ALIGNED |
| AI failure modes | 7 | 7 | 7 CLEAR |
| RAISE principle extension | 2 Stage 2.5 principles | 0 clean / 2 warn | Non-blocking for primary research |

## Correction round 1

### Resolved blocking issue

`IL-MEDIUM-1`, figure/table traceability: the original figure trace had a global
transformation hash but no per-figure `transformation` object or manuscript locator.
This failed the current Figure/Table Caption Fidelity contract.

Resolution:

- upgraded `paper/source_data/figure_trace.json` to `manuscript-figure-trace-v2`;
- added a source, operation, script SHA-256 and claim locator to every figure;
- changed `scripts/generate_manuscript_figures.py` so regeneration preserves the v2 contract;
- hardened `scripts/audit_manuscript_integrity.py` to reject missing or stale fields;
- added a regression test for the per-figure traceability requirement.

Re-verification: 4/4 figure packages pass. The current generator SHA-256 is
`77ed93d8acb2e75b98db5ceed9f9431e6f1d164387dc4572c49805c13945090f`.

## Phase A: reference verification

Every reference received an explicit primary-source verdict. Query form was
`"title" author year`, followed by DOI or arXiv identifier lookup. Live metadata was
checked on 2026-07-21.

| Ref. | Verdict | Primary result | Confirmed details |
|---:|---|---|---|
| 1 | VERIFIED | [arXiv:2506.09501v2](https://arxiv.org/abs/2506.09501v2) | Title, Jiayi Yuan et al., first published 2025, updated 2025-10-24 |
| 2 | VERIFIED | [arXiv:2511.20621v1](https://arxiv.org/abs/2511.20621v1) | Title, Adam Karvonen et al., 2025 |
| 3 | VERIFIED | [USENIX Security 2025](https://www.usenix.org/conference/usenixsecurity25/presentation/wang-yaofei) and [arXiv:2503.19499v1](https://arxiv.org/abs/2503.19499v1) | Title, Yaofei Wang et al., venue, year and pages 6817-6835 |
| 4 | VERIFIED | [DOI 10.18653/v1/2026.acl-long.39](https://doi.org/10.18653/v1/2026.acl-long.39) | Ruiyi Yan and Yugo Murawaki, ACL 2026, pages 890-907 |
| 5 | VERIFIED | [DOI 10.18653/v1/2026.findings-acl.1013](https://doi.org/10.18653/v1/2026.findings-acl.1013) | Wenzhao Cao, Yaofei Wang and Donghui Hu, Findings of ACL 2026, pages 20262-20274 |
| 6 | VERIFIED | [arXiv:2412.15115v2](https://arxiv.org/abs/2412.15115v2) | Qwen2.5 Technical Report, 2024, updated 2025-01-03 |
| 7 | VERIFIED | [arXiv:2604.21394v3](https://arxiv.org/abs/2604.21394v3) | Kaiyi Pang and Minhao Bai, 2026 |
| 8 | VERIFIED | [arXiv:2605.05837v1](https://arxiv.org/abs/2605.05837v1) | Daniella Bar-Lev, Farzad Farnoud and Ryan Gabrys, 2026 |
| 9 | VERIFIED | [arXiv:2604.25486v1](https://arxiv.org/abs/2604.25486v1) | Yaofei Wang et al., 2026 |

The audit also caught and discarded one verifier-side stale-state event: an arXiv request
for reference 3 ended with an unexpected EOF after a previous successful request, and the
PowerShell loop retained the prior XML object. Reference 3 was therefore re-requested in an
independent fail-fast process before receiving VERIFIED status. No stale response was used.

## Phase B: citation-context verification

All citation-bearing manuscript contexts were checked against official abstracts or
publisher metadata:

| Context | References | Verdict |
|---|---|---|
| Numerical configuration changes responses, reasoning paths and lengths | 1 | VERIFIED |
| Higher precision mitigates drift but has a resource trade-off | 1 | VERIFIED |
| Token-level inference verification under benign nondeterminism | 2 | VERIFIED |
| Sparse sampling and range coding define probability-based generative sampling mechanisms | 3, 4 | VERIFIED |
| Finite precision creates detectable low-probability-vanishing artifacts | 5 | VERIFIED |
| Qwen2.5 is the model family used by the local 1.5B instruction checkpoint | 6 | VERIFIED |
| List decoding, dyadic approximation and ReTokSync address capacity or synchronization objectives | 7, 8, 9 | VERIFIED |

The manuscript does not cite any of these works as proof that the proposed replay method is
secure, undetectable, zero-KL, semantically equivalent or first-of-kind.

## Phase C: data and statistical verification

### Independent re-analysis

All reruns wrote to `outputs/stage25/`; no prior result was overwritten.

| Analysis | Recomputed outcome | Reproducibility result |
|---|---|---|
| R002 official matrix | 1,193/1,200 completed; 347 ambiguous; 846/846 eligible exact; 16/16 capacity gates | Acceptance fields independently recounted from 1,200 rows |
| R044 main scale | 60/60 corrected, 10/60 uncorrected, 58/60 complete, mean correction 0.021605904154340095 | Recomputed JSON byte-identical to original, SHA-256 `281915ac...995c` |
| R046 ablations | Forward/top-four/reverse counts and paired bootstrap outputs | Recomputed JSON byte-identical to original, SHA-256 `da792588...b092` |
| R049 cost | 247/3,715 bytes, 1,148/4,636 referenced bytes, 6,136/9,604 self-contained bytes | Recomputed JSON byte-identical to original, SHA-256 `2c0e6948...c53e` |

Direct row-level recount additionally confirmed:

- R044 contains exactly 60 rows, 4,500 tokens and 96 corrections;
- every `reference_token_ids` length equals its declared `token_count`;
- every correction list length equals its declared `correction_count`;
- target top-four coverage is 4,499/4,500 and top-eight coverage is 4,500/4,500;
- R045 and R046 contain all 20 configured rows each, with no malformed sequence length;
- R002 contains only `completed` (1,193) and `budget_exhausted` (7) states;
- the seven R002 budget events are three block-512 and four block-1023 trials.

### Figure and table fidelity

Figures 1-4 pass the v2 trace contract after correction. Their source files exist, the
transformation hash matches the generator, the listed claim occurs in the manuscript, and
each limitation is visible in the figure legend, Discussion or Limitations prose.

Table 1 is internally consistent with the result artifacts. It remains a standalone
manuscript table without its own `table-1` trace entry; current protocol treats this as an
advisory trace-unavailable note, not a factual failure. A dedicated table source package
should be added before Stage 4.5.

This check verifies disclosure and claim-to-provenance fidelity. It does not judge whether the experiment was correctly designed, run, statistically adequate, or reproducible by ARS.

## Phase D: originality screening

The manuscript contains 59 eligible prose paragraphs before References. Twenty-one were
sampled across the Abstract, Introduction, Results, Discussion, Methods, availability,
ethics and AI-disclosure sections (35.6%). Each query used an 8-12 word characteristic
fragment in quotation marks and excluded the project's own GitHub namespace.

| Grade | Count | Proportion |
|---|---:|---:|
| ORIGINAL | 18 | 85.7% |
| COMMON_KNOWLEDGE | 0 | 0% |
| PARAPHRASE with citation | 3 | 14.3% |
| CLOSE_MATCH | 0 | 0% |
| VERBATIM | 0 | 0% |

No more than one AI-writing heuristic was observed: the prose maintains a uniformly formal
register. This is below the protocol's two-indicator alert threshold and is not evidence of
AI authorship.

Self-plagiarism could not be assessed because author names and prior publication lists are
not yet supplied. This remains an author-input note and must be revisited at Stage 4.5.

This originality check uses public web search as a heuristic screen. It is not Turnitin or
iThenticate, cannot search all paywalled or cross-language material, and may miss overlap.

## Phase E: claim verification

Twelve high-impact factual or quantitative claims were checked, exceeding the minimum of
ten. All were VERIFIED:

1. configuration-sensitive LLM nondeterminism;
2. R002 compatible official reproduction boundaries;
3. the conditional replay induction statement;
4. GPT-2 pilot results;
5. Qwen fixed-length pilot results;
6. main 60/60 corrected and 10/60 uncorrected counts;
7. 2.16% correction rate and 1.80-2.53% cluster interval;
8. 58/60 structural completion;
9. retained-mass and truncation change under top-four;
10. no detected correction-rate improvement under top-four;
11. 20/20 reverse-precision corrected replay;
12. all three explicitly separated R049 serialization ratios.

Verdict counts: 12 VERIFIED, 0 MINOR_DISTORTION, 0 MAJOR_DISTORTION,
0 UNVERIFIABLE and 0 UNVERIFIABLE_ACCESS.

The machine-readable experiment intake, 12 planned/executed units, eight sampled empirical
claim alignments and negative constraints are recorded in
`paper/STAGE25_MATERIAL_PASSPORT.json`. ARS's experiment-provenance schema validator and
claim/provenance cross-array consistency validator both exit 0.

## Seven-mode AI research failure checklist

| Mode | Status | Evidence |
|---:|---|---|
| 1. Implementation bug passing self-review | CLEAR | 239 tests pass; targeted Ruff passes; four analyses independently rerun; direct row recount agrees |
| 2. Hallucinated citation | CLEAR | 9/9 references verified through DOI, arXiv, ACL Anthology or USENIX |
| 3. Hallucinated experimental result | CLEAR | Every reported number maps to a saved result pointer and hash; 8/8 empirical alignments are ALIGNED |
| 4. Shortcut reliance | CLEAR | Exactness is disclosed as construction-level and target-specific; sparsity, uncorrected controls, package boundaries and top-k negative results are reported separately |
| 5. Bug reframed as insight | CLEAR | No surprise/counterintuitive language; deterministic reruns agree; negative results remain negative |
| 6. Methodology fabrication | CLEAR | Methods values match stored configs for model, precision, top-k, q=0.5, B=16, T=1.2, prompts, seeds and stopping rule |
| 7. Early frame-lock | CLEAR | The paper is framed around target-specific replay; security, semantics and cross-hardware generality are explicitly excluded rather than inferred from the original steganography goal |

## Primary-research compliance extension

RAISE officially targets evidence synthesis. Applying its principles here is an extension,
not a claim of RAISE compliance. Under the primary-research mode, findings are warn-only.

| Principle | Status | Reason |
|---|---|---|
| Human oversight | WARN | The AI disclosure states author supervision and responsibility, but author identities, qualifications and an adjudication record are not supplied |
| Fit-for-purpose | WARN | AI-assisted stages are listed generically, but tool names, versions and per-task selection rationale are incomplete |

These warnings should be resolved in the author-input and final-formatting stages. They do
not block Stage 3 under the primary-research compliance contract.

## Remaining notes

- Nine `AUTHOR_INPUT_NEEDED` placeholders remain.
- Author names are required for the Stage 4.5 self-plagiarism check.
- An immutable archive DOI is still absent.
- Independent GPU/CUDA replay is still absent; the manuscript makes no cross-hardware claim.
- R048 remains ethics-pending; the manuscript makes no human semantic-quality claim.
- A dedicated Table 1 trace package should be added before Stage 4.5.
- External originality screening should be repeated with institutional plagiarism software before submission.

## Validation commands

```powershell
& '.venv\Scripts\python.exe' -m pytest -q
.\.venv\Scripts\ruff.exe check scripts\audit_manuscript_integrity.py scripts\generate_manuscript_figures.py tests\test_manuscript_integrity.py
& '.venv\Scripts\python.exe' scripts\audit_manuscript_integrity.py
```

Observed results: 239 tests passed with one unrelated Starlette deprecation warning; Ruff
passed; manuscript machine audit returned 27 passed, 0 failed and status
`PASS_WITH_AUTHOR_INPUT`.

