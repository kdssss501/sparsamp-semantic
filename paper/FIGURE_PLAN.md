# Figure and Table Plan

## Figure 1: Method overview

**Message:** A full target-side trajectory can be reconstructed by applying corrections only at precision-induced decision disagreements.

**Panels:**

- a, Reference and target next-token distributions under different precision.
- b, Relative-logit binning, canonical token-ID ordering and integer mass allocation.
- c, Manifest construction on the reference prefix.
- d, Fresh replay with sparse corrections preventing autoregressive divergence.

**Source:** algorithm and code in `src/sparsamp_semantic/replay_certificate.py` and `src/sparsamp_semantic/probability_contract.py`.

**Status:** schematic required; no empirical values.

## Figure 2: Main-scale exact replay

**Message:** Full-sequence agreement is low without certificates although token corrections are sparse.

**Panels:**

- a, Corrected exact 60/60 versus uncorrected exact 10/60.
- b, Prompt-level correction-rate distributions, preserving three seeds per prompt.
- c, English and Chinese prompt-cluster correction intervals.
- d, Sparse/full record-size distribution.

**Source:** `outputs/R044_qwen_replay_scale.json` and `outputs/R044_qwen_replay_scale_analysis.json`.

**Statistics:** 10,000 prompt-cluster bootstrap resamples; points are trajectories, clusters are prompts.

## Figure 3: Contract-width Pareto frontier

**Message:** Top-four improves retained-mass fidelity but does not reduce correction density.

**Panels:** retained source mass, truncation component, shared-contract exactness, correction rate and structural completion.

**Source:** `outputs/R044_qwen_replay_scale.json`, seed-0 subset, and `outputs/R045_qwen_contract_k4.json`.

**Statistics:** paired prompt-cluster bootstrap. Do not connect tokens because top-*k* changes the reference trajectory.

## Figure 4: Precision-direction stress test

**Message:** Corrected exact replay remains 20/20 after reversing FP16 and BF16 within the same stack.

**Panels:** correction rate, retained source mass, quantization TV and sentence completion.

**Source:** `outputs/R046_qwen_reverse_precision.json` and `docs/reproducibility/R046_ABLATION_ANALYSIS.json`.

## Table 1: Main numerical results

The draft table should be converted to `booktabs` style for LaTeX or a border-minimal Word table. Report metric directions and confidence-interval method in the caption. Do not mark values as statistically significant; report paired interval estimates.

## Missing figure evidence

- Blinded semantic preference outcomes.
- Independent hardware replication.
- Source data package with one row per trial and prompt-cluster identifiers.
