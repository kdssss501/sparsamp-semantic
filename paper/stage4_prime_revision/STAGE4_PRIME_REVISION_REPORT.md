# Stage 4' Focused Re-Revision Report

## Status

**GATES_PASSED_WITH_AUTHOR_INPUT.** P0 manuscript corrections, the bounded P1 sensitivity experiment and the Stage 4' code/manuscript gates are complete; external and author-owned blockers remain.

## Changes completed

1. Methods now names correction density as the primary empirical outcome and exact replay as an integrity gate.
2. The sparse replay procedure now states construction/replay complexity and target-pass cost.
3. Code Availability points to the planned `research-v0.40-qtb-sensitivity-revision` Git tag containing the revised manuscript and R050-R053 evidence.
4. R053 completed a bounded one-factor-at-a-time sensitivity contract for `q`, `T` and `B`, with `k=4` retained from R045. All 140 analyzed baseline-plus-variant trials passed the integrity gate.
5. B=20 produced the lowest correction-density point estimate (1.721% versus 2.000% baseline) and 1,131 referenced bytes versus 1,148, but the paired correction interval included no change.

## Evidence boundaries

- No independent physical GPU result was fabricated or substituted with same-machine replay.
- R053 is a completed one-seed local sensitivity study, not evidence of a global optimum.
- The study still excludes semantic equivalence and cross-hardware generality.
- External archive DOI and author declarations remain pending.

## Verification status

- Six R053 checkpoints: 120/120 completed and 120/120 corrected exact.
- R053 analysis: 10,000 prompt-paired bootstrap resamples; deterministic signature recorded.
- Focused analyzer tests: 4 passed.
- Focused Ruff for the new analyzer and tests: PASS.
- Full-project Pytest: 252 passed, with one dependency deprecation warning.
- Full-project Ruff: PASS.
- Refreshed manuscript-integrity audit: 45 passed, 0 failed, 9 author placeholders; `PASS_WITH_AUTHOR_INPUT`.
- `git diff --check`: PASS.

## Next execution gate

R053 is frozen and analyzed. Stage 4.5 final integrity verification can begin only after the remaining author-owned placeholders are supplied or explicitly recorded as submission blockers. Independent physical-GPU replay remains necessary only for a cross-hardware claim, which the manuscript excludes.
