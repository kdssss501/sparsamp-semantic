# Stage 4 Major Revision Report

## Decision

**PASS_WITH_RESIDUALS**. The v0.3 specialist ML-systems manuscript is ready for Stage 3' focused re-review. It is not ready for final submission.

## Scientific Changes

1. **Primary endpoint corrected.** Exact corrected replay is now an integrity invariant. Correction density, referenced bytes, target passes and portability are the empirical outcomes.
2. **R050 mathematical closure.** For the implemented base support-preserving allocator, (TV<2(k-1)/M). At top-two and 16 bits this is below `3.0517578125e-05` per step across all 1,500 audited contracts. No finite distribution-free KL bound is claimed.
3. **R051 matched storage baselines.** SPRC uses 1,148 referenced bytes, compared with 1,408 for four-token block repair and 4,636 for a full token trace. The table reports target passes and target specificity alongside bytes.
4. **R052 direct mechanism baseline.** Removing logit bins and integer mass at matched top-two support increases correction density by 1.123 percentage points, paired prompt 95% interval `[0.171, 2.015]`, and package size by 52 bytes. Positive-support top-16-cap reaches 25.454% correction density and exposes one BF16 support-shortfall step.
5. **Operational boundary added.** Constructor, recipient and auditor roles, shared state, target access, compute passes and correction-token privacy are explicit.
6. **Venue claim narrowed.** The title says target-specific and the draft targets a specialist reproducibility venue rather than a broad multidisciplinary journal.

## Reviewer Resolution

| Revision | Status |
|---|---|
| R1 independent physical GPU replay | EXTERNAL_BLOCK |
| R2 matched replay and unquantized-delta baselines | RESOLVED |
| R3 falsifiable empirical endpoint | RESOLVED |
| R4 integer-apportionment audit | RESOLVED |
| R5 full (q,T,B,k) sensitivity | PARTIAL / bounded limitation |
| R6 trust, state and cost model | RESOLVED |
| R7 venue positioning | RESOLVED |
| R8 immutable archive and author declarations | EXTERNAL_BLOCK |

## Quality Gates

- Full Ruff: PASS.
- Full Pytest: PASS.
- Manuscript integrity: `39/39`, `PASS_WITH_AUTHOR_INPUT`.
- Citation numbering: 1-9 matched.
- `git diff --check`: PASS.
- R052 raw execution: 20/20 trials completed with per-trial atomic checkpoints.
- Archived R052 pilots: retained as `.bak` files after two finite-support protocol corrections.

## Material Hashes

| Material | SHA-256 |
|---|---|
| v0.3 manuscript | `5510cf05dbfa6732f53e93be128eceb045537c62a64684bc867d80e5c25bf3a8` |
| R050 aggregate JSON | `ccdb2fced2119adec6bb272b73bc944aeca2636715b3dbb73d8ef99765fb2453` |
| R051 aggregate JSON | `514ed85e279ab703fc38b2309dfd043e8f194d53cac9079cd6983239bc778a67` |
| R052 aggregate JSON | `68c993d67c69ced9b579bbee7ad371173f51755228647d858e1c1b7dfe315e1d` |

## Residual Boundaries

- No independent physical GPU was available in this workspace. The manuscript excludes cross-hardware generality.
- Parameter evidence now covers top-*k*, finite-mass theory and quantization on/off, but not a full temperature/quantum grid. No global optimum is claimed.
- No human ratings were collected. Semantic equivalence remains excluded.
- Nine author/archival placeholders remain and must be supplied by the author before Stage 4.5 can pass without notes.

## Pipeline State

Stage 4 is complete with declared residuals. Explicit author confirmation is required before Stage 3' re-review.
