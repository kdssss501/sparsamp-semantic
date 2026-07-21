# Stage 4 Revision Tracker

## Status Vocabulary

- `RESOLVED`: evidence and manuscript change are complete.
- `PARTIAL`: a valid subset is complete; named work remains.
- `DELIBERATE_LIMITATION`: the claim is narrowed instead of adding unsupported evidence.
- `EXTERNAL_BLOCK`: completion requires author metadata, an archive service or another physical system.

## Required Revisions

| ID | Status | Action taken | Evidence or remaining work |
|---|---|---|---|
| R1 Independent replay | EXTERNAL_BLOCK | Preserved the frozen reference-only bundle and target runner; manuscript continues to call the current run same-machine | Requires a second physical GPU/software stack; do not regenerate reference artifacts |
| R2 Matched baselines | RESOLVED | Added seed-only, full-trace, block-repair-4/8/16/32 and unquantized top-2/top-16-cap deltas under one referenced-package boundary | R051-R052; paired top-2 delta versus SPRC includes a 10,000-resample prompt interval |
| R3 Falsifiable endpoint | RESOLVED | Abstract, Introduction and Discussion now treat exact replay as an integrity invariant and correction density/bytes as empirical outcomes | `paper/MANUSCRIPT_DRAFT.md` v0.3 |
| R4 Distribution audit | RESOLVED | Derived and tested TV bound (TV<2(k-1)/M); reported no finite distribution-free KL bound | R050, 1,500 saved contracts, focused tests |
| R5 Parameter sensitivity | PARTIAL | Existing top-2/top-4 paired ablation retained; no new claim of optimality | New preregistered (q,T,B,k) grid still requires GPU execution |
| R6 Trust/state model | RESOLVED | Added constructor/recipient/auditor procedure, shared-state frequency, target-access and privacy boundaries | Methods v0.3 |
| R7 Venue positioning | RESOLVED | Chose specialist ML-systems/reproducibility framing; title now says target-specific | Draft metadata, title and Abstract v0.3 |
| R8 Archive and declarations | EXTERNAL_BLOCK | Data availability now names R050/R051; no DOI or author declarations were invented | Requires authors, affiliations, CRediT, funding, conflicts and immutable archive DOI |

## Suggested Revisions

| ID | Status | Action taken |
|---|---|---|
| S1 Mechanism taxonomy | RESOLVED | Added Supplementary Note 2 comparing replay, PSS coding and tokenization layers |
| S2 Pseudocode and complexity | PARTIAL | Added five-step operational procedure; asymptotic and measured compute comparison remains concise |
| S3 Remove internal R0xx labels | PARTIAL | Removed R047/R048 from the revised Discussion; provenance labels remain in Methods/Data Availability where they identify artifacts |
| S4 Quality boundary | DELIBERATE_LIMITATION | Retained punctuation completion only as structural; no semantic-equivalence claim added |
| S5 License and retention | EXTERNAL_BLOCK | Requires author choice of code/data licenses and public archive policy |

## New Evidence

- R050: top-two, 16-bit integer-apportionment TV is strictly below `3.0517578125e-05` per step under the implemented base support-preserving allocator.
- R051: referenced SPRC is 1,148 bytes and block-repair-4 is 1,408 bytes on 1,500 frozen tokens; both recover 20/20 under the same target-conditioned contract, whereas seed-only recovers 5/20.
- R051 also makes the cost trade-off explicit: SPRC uses two logical target passes, while a full trace is target-independent and uses no target-model pass.
- R052: unquantized top-2 increased correction density by 1.123 percentage points [0.171, 2.015] and package size by 52 bytes versus SPRC; top-16-cap reached 25.454% correction density and one BF16 support-shortfall step.

## Re-review Gate

Stage 3' should not be requested until R1 is completed or explicitly accepted as a residual limitation by the author and R5 receives a bounded sensitivity decision. R8 metadata can remain pending until submission formatting, but the archive DOI is required before final integrity Stage 4.5.
