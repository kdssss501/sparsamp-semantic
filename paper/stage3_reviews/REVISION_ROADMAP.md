# Stage 3 Revision Roadmap

## Priority 1 - Scientific Validity and Novelty

- [ ] **R1 Independent replay:** transfer the frozen reference-only bundle to a second physical GPU stack; do not regenerate the reference side; retain per-trial atomic checkpoints and publish success/failure evidence.
- [ ] **R2 Matched baselines:** implement full trace, native target-conditioned delta and periodic checkpoint baselines under the same prompt, trajectory, target pass and package boundary.
- [ ] **R3 Primary endpoint:** make correction density or compact referenced bytes per token the empirical primary endpoint; treat corrected exactness as a protocol integrity requirement.
- [ ] **R4 Distribution audit:** quantify integer-apportionment TV/error bound in addition to full-logit quantization and support truncation; never sum incompatible KL directions.
- [ ] **R5 Sensitivity:** preregister a bounded grid for (q,T,B,k), record selection provenance and preserve all outcomes.

**Estimated effort:** 3-5 weeks plus access to one independent GPU.

## Priority 2 - External Validity and Operational Meaning

- [ ] **R6 Trust/state model:** document constructor, recipient and auditor roles; identify state transferred once, per model, per prompt and per trajectory.
- [ ] **R7 Venue fork:** choose either specialist ML-systems framing with one checkpoint or broad framing with at least a second model family and stronger external validation.
- [ ] **R8 Immutable artifact:** archive code, result summaries, frozen bundles, hashes and environment manifests; obtain DOI/accession.
- [ ] **S1 Mechanism taxonomy:** compare goals, guarantees, probability access, shared state, decoder queries, synchronization and code availability across adjacent methods.
- [ ] **S4 Quality boundary:** run an approved blinded study/native automatic baseline or remove any implication that sentence completion measures semantic quality.

**Estimated effort:** 2-4 weeks, partly parallel with Priority 1.

## Priority 3 - Submission Readiness

- [ ] Add construction/replay pseudocode and complexity.
- [ ] Replace internal experiment codes in the main narrative.
- [ ] Add Table 1 trace entry and verify all figure/table claims against source data.
- [ ] Complete authors, affiliations, CRediT contributions, funding, conflicts and acknowledgements.
- [ ] Add licenses, data-retention policy and clean-install instructions.
- [ ] Produce a marked revised manuscript and point-by-point response.

**Estimated effort:** 4-7 days after Priority 1 evidence is frozen.

## Stage 4 Entry Gate

Stage 4 manuscript revision may start only after explicit author confirmation. Recommended minimum evidence before rewriting central claims:

1. Independent replay result is frozen, including a negative result if the target contract fails.
2. Baseline definitions and package boundaries are approved.
3. The venue fork is selected.
4. No Stage 3 reviewer file is retroactively edited to match new evidence; revisions receive a new round.
