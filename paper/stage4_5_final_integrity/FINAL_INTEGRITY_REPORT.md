# Stage 4.5 Final Academic Integrity Report

## Verification mode

Final verification after Stage 4' re-revision, completed 2026-07-26.

## Verdict

**PASS_WITH_NOTES.** No fabricated reference, bibliographic mismatch, ghost citation, unsupported numerical result, major claim distortion, unverifiable claim, stale evidence hash, unmatched Table 1 row, close source match or verbatim source match was found. The notes concern the bounded local originality corpus, author-name ambiguity, missing submission declarations and absent external archive metadata. They do not alter the factual research verdict.

## Verification summary

| Category | Coverage | Result | Notes |
|---|---:|---:|---|
| Reference existence and metadata | 9/9 | PASS | Fresh arXiv, Crossref and USENIX checks on 2026-07-26 |
| Ghost citations | 9 cited / 9 listed | PASS | 0 orphan, 0 dangling |
| Citation context | All citation-bearing contexts | PASS | Checked against nine locally extracted full texts |
| Numerical, provenance and boundary checks | 50/50 | PASS | Executable audit, including R053 and Table 1 |
| Figure packages | 4/4 | PASS | Source, transformation hash, claim and limitation checks |
| Table packages | 1/1 | PASS | Four frozen inputs, generated CSV and exact manuscript-row matching |
| Local originality screen | 65/65 eligible paragraphs | PASS_WITH_SCOPE_LIMITATION | 64 ORIGINAL, 1 COMMON_KNOWLEDGE, 0 CLOSE_MATCH, 0 VERBATIM |
| Self-overlap attribution | Lei Ke | NOTE | Crossref returned multiple unrelated same-name records; no affiliation or ORCID was supplied |
| Claim verification | All major external and empirical claim families | PASS | 0 MAJOR_DISTORTION, 0 UNVERIFIABLE |
| Full code gate | 256 tests + full Ruff | PASS | One dependency deprecation warning |

## Phase A: fresh reference verification

Each reference was re-requested independently. arXiv metadata was read through the export API; ACL records were checked through their DOI/Crossref metadata; the USENIX presentation page returned HTTP 200. Downloaded full texts were stored only as local audit inputs under `outputs/stage45_sources/` and are not part of the committed paper package.

| Ref. | Verdict | Fresh primary record | Confirmed fields |
|---:|---|---|---|
| 1 | VERIFIED | https://arxiv.org/abs/2506.09501 | Title, Jiayi Yuan et al., 2025, current revision metadata |
| 2 | VERIFIED | https://arxiv.org/abs/2511.20621 | Title, Adam Karvonen et al., 2025 |
| 3 | VERIFIED | https://www.usenix.org/conference/usenixsecurity25/presentation/wang-yaofei and https://arxiv.org/abs/2503.19499 | Title, Yaofei Wang et al., USENIX Security 2025 |
| 4 | VERIFIED | https://doi.org/10.18653/v1/2026.acl-long.39 | Title, Ruiyi Yan and Yugo Murawaki, pages 890-907 |
| 5 | VERIFIED | https://doi.org/10.18653/v1/2026.findings-acl.1013 | Title, Wenzhao Cao, Yaofei Wang and Donghui Hu, pages 20262-20274 |
| 6 | VERIFIED | https://arxiv.org/abs/2412.15115 | Qwen2.5 Technical Report and Qwen author group |
| 7 | VERIFIED | https://arxiv.org/abs/2604.21394 | Title, Kaiyi Pang and Minhao Bai, 2026 |
| 8 | VERIFIED | https://arxiv.org/abs/2605.05837 | Title, Daniella Bar-Lev, Farzad Farnoud and Ryan Gabrys, 2026 |
| 9 | VERIFIED | https://arxiv.org/abs/2604.25486 | Title, Yaofei Wang et al., 2026 |

## Phase B: citation-context verification

The downloaded source text confirms the manuscript's bounded uses: Ref. 1 concerns configuration- and precision-sensitive inference nondeterminism; Ref. 2 token-level verification under nondeterminism; Refs. 3-4 sparse sampling and range coding; Ref. 5 finite-precision low-probability-vanishing artifacts; Ref. 6 the Qwen2.5 family; and Refs. 7-9 list decoding, dyadic coding and tokenization synchronization. The manuscript does not use these papers to claim target-independent determinism, zero divergence, semantic equivalence or cross-hardware generality.

## Phase C: data, table and provenance verification

`scripts/audit_manuscript_integrity.py` returned 50 passed and 0 failed. Its checks cover the main R044 counts and intervals, R049 package boundaries, R002 official compatibility limits, R050 integer-apportionment bound, R051 matched controls, R052 unquantized deltas, R053 sensitivity values, mandatory limitation language, source hashes and every figure/table package.

The new Table 1 package closes the advisory issue from Stage 2.5. `scripts/generate_manuscript_table1.py` derives four rows from the frozen R044-R046 inputs using 10,000 prompt-cluster bootstrap resamples and public seed 20260720. The trace records all four input hashes and the transformation hash; the executable audit requires every generated Markdown row to occur exactly in the manuscript.

## Phase D: originality and author-name check

Sending unpublished manuscript phrases to a public search engine was rejected because it would disclose the draft to an external service. The safer replacement downloaded only the nine already-public cited sources and compared all 65 eligible manuscript paragraphs locally. The screen found no contiguous 12-word or 20-word source match; one eight-token match was the public block-size sequence `2 4 8 16 32 64 128 256`, classified as common knowledge.

This is a full local-corpus screen, not a global plagiarism determination. It cannot detect overlap with uncollected literature or semantic paraphrase. Turnitin or iThenticate remains recommended before formal submission.

Crossref search for `Lei Ke` returned unrelated records in wireless interference, computer vision and other fields. Without an affiliation, ORCID or prior-publication list, no record can be attributed to this author. The self-overlap check is therefore recorded as identity-not-disambiguated, not silently passed.

## Phase E: claim verification

All major external and empirical claim families were checked. External claims match the nine source texts. Empirical claims match the saved R002, R044-R046 and R049-R053 analyses. The R053 conclusion remains deliberately negative: B=20 had the lowest point estimate, but its paired interval included no change and it is only a replication candidate. Exact replay remains an integrity gate rather than the empirical endpoint.

Verdict counts: VERIFIED claim families only; 0 MINOR_DISTORTION, 0 MAJOR_DISTORTION, 0 UNVERIFIABLE and 0 UNVERIFIABLE_ACCESS.

## Remaining non-scientific and external-validity notes

- The manuscript displays only the author name `Lei Ke`, as requested.
- Affiliation, corresponding contact, CRediT roles, funding and competing-interest declarations were not supplied and are omitted from the draft.
- No external archival DOI has been created.
- Independent physical-hardware replay has not been performed; the manuscript excludes cross-hardware generality.
- No human semantic-quality study has been performed; the manuscript excludes semantic-equivalence claims.
- Local originality screening does not replace institutional similarity checking.

## Reproducible gate commands

```powershell
& '.venv\Scripts\python.exe' scripts\generate_manuscript_table1.py
& '.venv\Scripts\python.exe' scripts\audit_local_originality.py
& '.venv\Scripts\python.exe' scripts\audit_manuscript_integrity.py
& '.venv\Scripts\python.exe' -m pytest
& '.venv\Scripts\ruff.exe' check .
```

## Stage decision

Stage 4.5 scientific integrity is complete with explicit scope notes. The paper may enter Stage 5 working-paper formatting after the mandatory user checkpoint. It must not be described as journal-submission-ready until the omitted declarations and archive metadata are supplied.
