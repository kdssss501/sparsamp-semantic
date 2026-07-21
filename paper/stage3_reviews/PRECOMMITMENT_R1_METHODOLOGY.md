# Phase 1 Precommitment - R1 Methodology

## Contract Paraphrase

- D1 mandatory: design, computational controls, uncertainty estimates and replay checks must justify the quantitative claims.
- D2 mandatory: floating-point, stochastic-sampling and reproducibility concepts must be used correctly.
- D3 mandatory: deterministic guarantees must be separated from empirical sparsity and generalization claims.
- D4 high: methodological implications must be interpretable beyond the exact tested stack.
- D5 normal: methods and statistical estimands must be sufficiently clear to reproduce.

## D1-D5 Scoring Plan

| dimension_id | what_to_look_for | what_triggers_block | what_triggers_warn |
|---|---|---|---|
| D1 | Experimental unit, prompt/seed dependence, bootstrap, completeness, independent hardware and implementation checks | Data leakage, invalid resampling, missing primary outcome or an unreproducible guarantee | Small fixed prompt set, one hardware stack or incomplete sensitivity analysis |
| D2 | Correct treatment of precision, conditional replay, integer apportionment and divergence | A false mathematical or numerical statement underpins the method | A required divergence term or implementation boundary is not quantified |
| D3 | Separation of by-construction exactness from measured correction sparsity | Empirical data are presented as proving the deterministic invariant or vice versa | Wording occasionally conflates replay recovery with distributional agreement |
| D4 | Robustness across environments and usefulness to ML systems practice | General cross-system conclusions rest solely on same-machine evidence | Practical value is plausible but portability evidence is incomplete |
| D5 | Full protocol, software versions, stopping rules, estimands and figure intervals | Essential reproduction parameters are absent | Minor reporting details or table traces are incomplete |

[CONTRACT-ACKNOWLEDGED]
