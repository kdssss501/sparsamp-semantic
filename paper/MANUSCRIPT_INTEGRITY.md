# Manuscript Integrity Audit

**Status:** PASS_WITH_AUTHOR_INPUT
**Checks:** 27 passed, 0 failed
**Author placeholders:** 9

| Check | Status | Detail |
|---|---|---|
| corrected recovery | PASS | expected manuscript token: 60 of 60 |
| uncorrected recovery | PASS | expected manuscript token: 10 of 60 |
| mean correction rate | PASS | expected manuscript token: 2.16% |
| correction interval | PASS | expected manuscript token: 1.80-2.53% |
| sentence completion | PASS | expected manuscript token: 58 of 60 |
| payload ratio | PASS | expected manuscript token: 6.65% |
| referenced package ratio | PASS | expected manuscript token: 24.76% |
| self-contained package ratio | PASS | expected manuscript token: 63.89% |
| official eligible decoding | PASS | expected manuscript token: All 846 completed trials without Token Ambiguity decoded exactly |
| official capacity checks | PASS | expected manuscript token: All 16 capacity comparisons were within 5% relative error |
| official budget boundary | PASS | expected manuscript token: Of 1,200 configured trials, 1,193 completed |
| official status | PASS | expected manuscript token: PASS_WITH_LIMITATIONS |
| official raw checkpoint hash | PASS | outputs\official\R002_official_matrix_compat.json |
| citation numbering | PASS | cited=[1, 2, 3, 4, 5, 6, 7, 8, 9], references=[1, 2, 3, 4, 5, 6, 7, 8, 9] |
| no zero-divergence claim | PASS | required boundary: do not establish target-independent determinism, zero distributional divergence or cross-hardware generality |
| no human ratings | PASS | required boundary: no human ratings have been collected |
| same-machine external replay | PASS | required boundary: same-machine smoke test rather than independent hardware evidence |
| token-id boundary | PASS | required boundary: does not test recovery after public-text re-tokenization |
| figure input hash: scale | PASS | outputs/R044_qwen_replay_scale_analysis.json |
| figure input hash: forward | PASS | outputs/R044_qwen_replay_scale.json |
| figure input hash: top4 | PASS | outputs/R045_qwen_contract_k4.json |
| figure input hash: reverse | PASS | outputs/R046_qwen_reverse_precision.json |
| figure transformation hash | PASS | scripts/generate_manuscript_figures.py |
| figure package: 1 | PASS | {'artifact_id': 'fig-1', 'source_data': None, 'caption_claim': 'A target-specific sparse correction record reconstructs the selected reference trajectory under a fixed target environment.', 'supported_manuscript_claims': ['Corrections are applied before prefix extension, preventing local disagreements from cascading.'], 'limitations': ['Conceptual workflow; not an empirical result.']} |
| figure package: 2 | PASS | {'artifact_id': 'fig-2', 'source_data': 'paper/source_data/figure_02_source.csv', 'caption_claim': 'Certificates recovered 60 of 60 trajectories while prompt-level correction rates remained low.', 'supported_manuscript_claims': ['Certificate-corrected replay recovered 60 of 60 token trajectories, whereas uncorrected replay recovered 10 of 60.', 'The mean correction rate was 2.16 percent across the main 60 trajectories.'], 'limitations': ['Fixed prompt set on one model and GPU stack.']} |
| figure package: 3 | PASS | {'artifact_id': 'fig-3', 'source_data': 'paper/source_data/figure_03_source.csv', 'caption_claim': 'Top-four retained more source mass and reduced the truncation component but did not reduce correction density.', 'supported_manuscript_claims': ['Increasing contract support improves retained-mass fidelity but not replay sparsity in the controlled ablation.'], 'limitations': ['One public seed per contract-width condition.']} |
| figure package: 4 | PASS | {'artifact_id': 'fig-4', 'source_data': 'paper/source_data/figure_04_source.csv', 'caption_claim': 'Correction density and retained mass were similar after reversing FP16 and BF16 within the tested stack.', 'supported_manuscript_claims': ['The data support bidirectional precision replay on the tested model and GPU stack.'], 'limitations': ['One public seed per precision direction; same GPU stack.']} |

## Boundary

This executable audit checks selected numerical tokens, source hashes, figure packages,
citation numbering and mandatory limitation statements. It does not replace source-level
citation verification, statistical review or author approval.
