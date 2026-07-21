# Manuscript Integrity Audit

**Status:** PASS_WITH_AUTHOR_INPUT
**Checks:** 39 passed, 0 failed
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
| integer apportionment contract count | PASS | expected manuscript token: all 1,500 saved seed-0 contracts |
| integer apportionment TV bound | PASS | expected manuscript token: 1/32768=3.0518\times10^{-5} |
| integer apportionment KL boundary | PASS | expected manuscript token: No finite distribution-free KL bound exists |
| SPRC referenced bytes | PASS | expected manuscript token: 1,148 bytes |
| full-trace referenced bytes | PASS | expected manuscript token: 4,636 bytes |
| block-repair-4 referenced bytes | PASS | expected manuscript token: 1,408 bytes |
| unquantized top-2 correction delta | PASS | expected manuscript token: 1.123 percentage points |
| unquantized top-2 interval | PASS | expected manuscript token: 0.171-2.015 |
| unquantized top-2 package | PASS | expected manuscript token: 1,200 referenced bytes |
| unquantized top-16 correction rate | PASS | expected manuscript token: 25.454% |
| finite-precision support shortfall | PASS | expected manuscript token: One of 1,500 steps retained only five positive-probability candidates |
| citation numbering | PASS | cited=[1, 2, 3, 4, 5, 6, 7, 8, 9], references=[1, 2, 3, 4, 5, 6, 7, 8, 9] |
| no native-distribution claim | PASS | required boundary: do not establish target-independent determinism, native-distribution preservation, semantic equivalence or cross-hardware generality |
| exactness is an integrity gate | PASS | required boundary: exact replay as an integrity gate |
| no human ratings | PASS | required boundary: no human ratings were collected |
| same-machine external replay | PASS | required boundary: current 20-trial result is a same-machine smoke test |
| token-id boundary | PASS | required boundary: does not test recovery after public-text re-tokenization |
| figure input hash: scale | PASS | outputs/R044_qwen_replay_scale_analysis.json |
| figure input hash: forward | PASS | outputs/R044_qwen_replay_scale.json |
| figure input hash: top4 | PASS | outputs/R045_qwen_contract_k4.json |
| figure input hash: reverse | PASS | outputs/R046_qwen_reverse_precision.json |
| figure transformation hash | PASS | scripts/generate_manuscript_figures.py |
| figure package: 1 | PASS | {'artifact_id': 'fig-1', 'source_data': 'paper/FIGURE_PLAN.md', 'transformation': {'script': 'scripts/generate_manuscript_figures.py', 'sha256': '77ed93d8acb2e75b98db5ceed9f9431e6f1d164387dc4572c49805c13945090f', 'operation': 'conceptual workflow rendering from the documented algorithm'}, 'caption_claim': 'A target-specific sparse correction record reconstructs the selected reference trajectory under a fixed target environment.', 'supported_manuscript_claims': [{'claim': 'During replay, corrections are applied before extending the prefix, which prevents a local disagreement from cascading.', 'locator': 'Introduction'}], 'limitations': ['Conceptual workflow; not an empirical result.']} |
| figure package: 2 | PASS | {'artifact_id': 'fig-2', 'source_data': 'paper/source_data/figure_02_source.csv', 'transformation': {'script': 'scripts/generate_manuscript_figures.py', 'sha256': '77ed93d8acb2e75b98db5ceed9f9431e6f1d164387dc4572c49805c13945090f', 'operation': 'exact-replay counts and prompt-level correction-rate plotting'}, 'caption_claim': 'Certificates recovered 60 of 60 trajectories while prompt-level correction rates remained low.', 'supported_manuscript_claims': [{'claim': 'Certificate-corrected replay recovered 60 of 60 token trajectories, whereas uncorrected replay recovered 10 of 60 (Table 1 and Fig. 2a).', 'locator': 'Results: Exact replay scales across bilingual prompts'}, {'claim': 'The mean correction rate was 2.16% (prompt-cluster bootstrap 95% confidence interval, 1.80-2.53%), with a maximum trial rate of 6.15% and prompt-level variation shown in Fig. 2b.', 'locator': 'Results: Exact replay scales across bilingual prompts'}], 'limitations': ['Fixed prompt set on one model and GPU stack.']} |
| figure package: 3 | PASS | {'artifact_id': 'fig-3', 'source_data': 'paper/source_data/figure_03_source.csv', 'transformation': {'script': 'scripts/generate_manuscript_figures.py', 'sha256': '77ed93d8acb2e75b98db5ceed9f9431e6f1d164387dc4572c49805c13945090f', 'operation': 'paired prompt-cluster contract-width summary plotting'}, 'caption_claim': 'Top-four retained more source mass and reduced the truncation component but did not reduce correction density.', 'supported_manuscript_claims': [{'claim': 'The distributional improvement did not produce a reliability improvement.', 'locator': 'Results: Contract width exposes a distribution-reliability Pareto frontier'}], 'limitations': ['One public seed per contract-width condition.']} |
| figure package: 4 | PASS | {'artifact_id': 'fig-4', 'source_data': 'paper/source_data/figure_04_source.csv', 'transformation': {'script': 'scripts/generate_manuscript_figures.py', 'sha256': '77ed93d8acb2e75b98db5ceed9f9431e6f1d164387dc4572c49805c13945090f', 'operation': 'paired prompt-cluster precision-direction summary plotting'}, 'caption_claim': 'Correction density and retained mass were similar after reversing FP16 and BF16 within the tested stack.', 'supported_manuscript_claims': [{'claim': 'These data support bidirectional precision replay on the tested model and GPU stack.', 'locator': 'Results: Replay is stable in both FP16/BF16 directions within the tested environment'}], 'limitations': ['One public seed per precision direction; same GPU stack.']} |

## Boundary

This executable audit checks selected numerical tokens, source hashes, figure packages,
citation numbering and mandatory limitation statements. It does not replace source-level
citation verification, statistical review or author approval.
