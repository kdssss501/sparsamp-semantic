# Stage 3' Focused Verification Review

## Scope and Inputs

This re-review verifies only the issues raised in the Stage 3 Editorial Decision and Revision Roadmap. It does not repeat the five-reviewer first-round review or introduce a new publication standard.

Reviewed materials:

- `paper/stage3_reviews/EDITORIAL_DECISION.md`
- `paper/stage3_reviews/REVISION_ROADMAP.md`
- `paper/stage4_revision/RESPONSE_TO_REVIEWERS.md`
- `paper/stage4_revision/REVISION_TRACKER.md`
- `paper/stage4_revision/STAGE4_REVISION_REPORT.md`
- `paper/MANUSCRIPT_DRAFT.md` (v0.3)
- `paper/MANUSCRIPT_INTEGRITY.json` (39/39 checks passed; 9 author placeholders)

## Decision

**Major Revision.** The bounded, specialist ML-systems contribution is now scientifically coherent, and the central novelty concern has been materially reduced by matched baselines and the integer-apportionment audit. The original acceptance criteria are not yet all satisfied, however. Independent physical-target replay remains absent, the requested parameter sensitivity is incomplete, the manuscript contains one primary-endpoint inconsistency, and archival/author declarations remain unfinished.

This decision does not reverse the positive scientific assessment. It means the manuscript has moved from an under-isolated mechanism claim to a credible target-specific research result, but it is not yet a submission-complete article under the first-round contract.

## Revision Response Checklist

### Priority 1 - Required Revisions

| ID | Original requirement | Status | Revision evidence | Quality assessment |
|---|---|---|---|---|
| R1 | Independent physical GPU/software replay of the frozen bundle | PARTIALLY_ADDRESSED | Title, Abstract and Discussion now restrict the result to one model and GPU stack; the frozen external bundle and runner are preserved | The unsupported cross-hardware claim was removed, but the requested independent execution was not performed. The original empirical acceptance criterion remains unmet. |
| R2 | Matched full-trace, native-delta and checkpoint/repair baselines | FULLY_ADDRESSED | Results Table 2; R051 seed-only, full-trace and block-repair controls; R052 unquantized top-two and positive-support top-16-cap controls | Package boundary, target passes, recovery and byte cost are reported. The top-two comparison isolates a small probability-contract advantage rather than attributing all sparse-delta gains to the contract. |
| R3 | Treat exact recovery as an integrity gate and use a falsifiable empirical primary endpoint | PARTIALLY_ADDRESSED | Abstract and Introduction identify correction density and bytes as empirical outcomes; Discussion rejects exactness as an accuracy advance | Methods, "Outcome measures", still calls exact equality the primary outcome and correction density secondary. This contradicts the revised framing and the response letter. |
| R4 | Separate quantization, support truncation and integer-apportionment error | FULLY_ADDRESSED | Methods derives `TV(p,r) < 2(k-1)/M`; R050 checks 1,500 contracts; no distribution-free finite KL bound is claimed | The directions and support-related infinity are stated correctly, and incompatible divergence components are not summed. |
| R5 | Prespecified sensitivity over `(q,T,B,k)` | PARTIALLY_ADDRESSED | Existing top-two/top-four paired analysis; finite-mass theory; quantized versus unquantized comparison | Evidence now covers `k`, finite-mass behavior and quantization on/off, but not a bounded `q`, `T` and `B` grid. The manuscript appropriately avoids an optimality claim, but the original acceptance criterion is unmet. |

### Priority 2 - External Validity and Operational Meaning

| ID | Original requirement | Status | Revision evidence | Quality assessment |
|---|---|---|---|---|
| R6 | Define actors, shared state, target access, cost and privacy exposure | FULLY_ADDRESSED | Methods, "Sparse precision replay certificate" operational procedure and package-boundary discussion | Constructor, recipient and auditor roles are explicit; per-study/per-trial/per-trajectory state, two target passes and correction-token exposure are disclosed. |
| R7 | Broaden the evidence or retarget to a specialist venue | FULLY_ADDRESSED | Revised title begins "Target-specific"; intended format is a specialist ML-systems/reproducibility article; Abstract and Discussion exclude cross-hardware generality | The venue fork is clear and consistent with the available evidence. |
| R8 | Freeze an immutable artifact and complete declarations | PARTIALLY_ADDRESSED | Public Git tag, material hashes, source-data packages, replay instructions and integrity audit exist | Immutable archive/DOI, authorship, affiliations, CRediT roles, funding and competing-interest declarations remain author-owned blockers. Code Availability also points to an earlier tag than the Stage 4 evidence package. |

### Priority 3 and Suggested Revisions

| ID | Original requirement | Status | Notes |
|---|---|---|---|
| S1 | Mechanism taxonomy | FULLY_ADDRESSED | Supplementary Note 2 separates replay, PSS coding and tokenization layers and explicitly describes SPRC as a target-conditioned sparse delta format. |
| S2 | Reader-facing pseudocode and complexity | PARTIALLY_ADDRESSED | A five-step procedure is present; a compact algorithm block and explicit asymptotic/compute statement would improve submission readability. |
| S3 | Remove internal R0xx labels from the main narrative | PARTIALLY_ADDRESSED | Results prose is improved, but artifact identifiers remain in Methods and availability sections. Their provenance role is defensible. |
| S4 | Add semantic evidence or remove quality implications | FULLY_ADDRESSED | Sentence completion is explicitly structural; no semantic-equivalence or human-preference claim remains. |
| S5 | Add licenses and retention/access statements | PARTIALLY_ADDRESSED | Access boundaries are described, but final licenses and archival retention policy require author selection. |

## New Issues Introduced by Revision

Only revision-caused or revision-revealed inconsistencies were considered.

| ID | Type | Location | Description |
|---|---|---|---|
| NEW-1 | Internal consistency | Methods, "Outcome measures" | Exact equality is still named the primary outcome, contradicting the Abstract, Introduction, Discussion and response letter. Resolve by naming correction density as the empirical primary endpoint and exact equality as the protocol integrity gate. |
| NEW-2 | Artifact identity | Code Availability | The manuscript cites `research-v0.36-official-matrix-reproduction`, while the Stage 4 evidence was frozen later. Finalization must cite one immutable release containing R050-R052 and the revised manuscript. |

## Residual Issues

1. Execute the unchanged frozen bundle on an independent physical GPU/software stack, or obtain explicit editorial agreement that one-stack validation is sufficient for the selected venue.
2. Correct the Methods primary-endpoint inconsistency.
3. Run a bounded, preregistered `q/T/B` sensitivity study, or negotiate a formally narrowed acceptance criterion that treats it as future work.
4. Create the immutable archive and complete all author-owned declarations before final integrity review.
5. Add a compact algorithm/complexity presentation if required by the target venue.

## Positive Verification Finding

The first-round Devil's Advocate concern is no longer unanswered. Under the matched 1,500-token referenced-package boundary, SPRC used 1,148 bytes and 2.054% corrections; the unquantized top-two delta used 1,200 bytes and 3.178% corrections, a paired increase of 1.123 percentage points with a prompt-bootstrap 95% interval of 0.171-2.015. This is a small, bounded mechanism contribution rather than a claim of global optimality.
