# Figure and Table Plan

## Figure 1: Method overview

**Message:** A full target-side trajectory can be reconstructed by applying corrections only at precision-induced decision disagreements.

**Panels:**

- a, Reference trajectory through the top-16 validation envelope and public top-*k* contract.
- b, Target-side canonical ordering, integer mass allocation and sparse manifest construction.
- c, Fresh target replay with corrections applied before prefix extension.

**Source:** algorithm and code in `src/sparsamp_semantic/replay_certificate.py` and `src/sparsamp_semantic/probability_contract.py`.

**Status:** complete: `figures/fig1_method_overview.pdf` and 300 DPI PNG. Component source table is `figures/source_data/figure1_components.csv`.

## Figure 2: Main-scale exact replay

**Message:** Full-sequence agreement is low without certificates although token corrections are sparse.

**Panels:**

- a, Corrected exact 60/60 versus uncorrected exact 10/60.
- b, Prompt-level correction-rate distributions, preserving three seeds per prompt.
- c, English and Chinese prompt-cluster correction intervals.
- d, Trial-level legacy fixed-width payload/full-trace ratio.

**Source:** `outputs/R044_qwen_replay_scale.json` and `outputs/R044_qwen_replay_scale_analysis.json`.

**Statistics:** 10,000 prompt-cluster bootstrap resamples; points are trajectories, clusters are prompts.

**Status:** complete: `figures/fig2_main_scale.pdf` and 300 DPI PNG. Trial and language-summary CSVs are in `figures/source_data/`.

## Figure 3: Contract-width Pareto frontier

**Message:** Top-four improves retained-mass fidelity but does not reduce correction density.

**Panels:** retained source mass, truncation component, correction rate, shared-contract exactness, structural completion and uncorrected exact replay.

**Source:** `outputs/R044_qwen_replay_scale.json`, seed-0 subset, and `outputs/R045_qwen_contract_k4.json`.

**Statistics:** paired prompt-cluster bootstrap. Do not connect tokens because top-*k* changes the reference trajectory.

**Status:** complete: `figures/fig3_contract_width.pdf` and 300 DPI PNG. Frozen variant values and intervals are in `figures/source_data/figure3_contract_width.csv`.

## Figure 4: Precision-direction stress test

**Message:** Corrected exact replay remains 20/20 after reversing FP16 and BF16 within the same stack.

**Panels:** corrected exact replay, correction rate, retained source mass and sentence completion.

**Source:** `outputs/R046_qwen_reverse_precision.json` and `docs/reproducibility/R046_ABLATION_ANALYSIS.json`.

**Status:** complete: `figures/fig4_precision_direction.pdf` and 300 DPI PNG. Source values are in `figures/source_data/figure4_precision_direction.csv`.

## Table 1: Main numerical results

The draft table should be converted to `booktabs` style for LaTeX or a border-minimal Word table. Report metric directions and confidence-interval method in the caption. Do not mark values as statistically significant; report paired interval estimates.

## Missing figure evidence

- Independent hardware replay outcome.
- Blinded semantic preference outcomes; R048 materials exist but remain `ETHICS_PENDING`.
