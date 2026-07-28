# Claim-evidence map

## Primary research question

Can a finite public integer perturbation contract certify local sampling decisions conservatively enough to recover FP16/BF16 language-model trajectories while using less payload than an earlier dual-barrier certificate?

## Supported claims

- **Finite-model soundness.** If every target bin lies in the declared interval, the target pair is represented by the envelope/tail condition, and both parties use identical public discrete rules, a singleton bounded decision set implies the target chooses the reference token. Evidence: theorem and implementation contract in `main.tex` and `docs/reproducibility/R058_BOUNDED_DECISION_SET_CONTRACT.md`.
- **Exact trajectory replay.** Applying every unresolved reference token before prefix extension recovers the reference sequence by induction. Evidence: theorem in `main.tex`; exact-trial checks in R058/R059.
- **Independent-seed confirmation.** Frozen thresholds recovered 40/40 seed-1/2 trials across 3,000 token decisions with zero observed false-safe step. Evidence: `outputs/R059_independent_bounded_decision.json`, result signature `404459fea3e77645a42c5ef900667e0e12b04c79828494ddf07280bddeecaa60`.
- **Matched cost improvement.** R059 BDS payload was 4,916 bytes versus 5,804 bytes for R056 and 9,000 bytes for the full trace, giving 84.7002% and 54.6222%, respectively. Evidence: R059 pooled JSON fields.
- **Finite computation.** With envelope size `m` and integer-bin radius `Delta`, enumeration is `O(m^2(2Delta+1)^2)` and terminates. Evidence: finite loop bounds in the algorithm and implementation.

## Claims requiring more evidence

- Cross-hardware coverage requires a frozen run on a genuinely independent GPU/kernel stack.
- Prompt-population reliability requires more prompts and prompt-cluster uncertainty intervals.
- Semantic quality requires blinded human or validated automatic evaluation.
- Public text reconstruction requires a separate retokenization synchronization experiment.
- Communication capacity requires integration with a coder on identical integer counts.

## Prohibited wording

- “Universal floating-point guarantee” or “deterministic on arbitrary hardware.”
- “Zero KL,” “native-distribution preserving,” or “undetectable.”
- “Semantically equivalent” or “human preferred.”
- “First method” without a completed novelty and citation-network review.
- “CCF-A paper” as an acceptance claim; this artifact is a CCF-A-style working paper.

## Artifact identifiers

- Frozen implementation commit: `33d14df`.
- R058 result signature: `ac2e945cfdcee73f043013b6c645901fb32c6e33532afa4bbe8c7b09cda9e069`.
- R059 trace SHA-256: `5111bf261d8f9593f2d5c299fbd5470863e871ffa1e3bbe14683aa5e86002959`.
- R059 result signature: `404459fea3e77645a42c5ef900667e0e12b04c79828494ddf07280bddeecaa60`.
