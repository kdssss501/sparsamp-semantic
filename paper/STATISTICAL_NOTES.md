# Statistical Estimand Notes

## Primary estimand used in the manuscript

The manuscript reports the mean of trial-level rates. Prompts are the resampling clusters, and all seed trajectories inside a sampled prompt are retained. This gives every trajectory equal weight rather than weighting longer outputs more heavily.

For the one-seed top-*k* and precision-direction ablations, the paired effect is the mean prompt-level difference. Its interval is obtained by resampling matched prompts 10,000 times with replacement.

## Why these values differ slightly from R046 analysis JSON

`docs/reproducibility/R046_ABLATION_ANALYSIS.json` reports token-weighted aggregate rates for its compact Pareto audit. The manuscript uses equal-trial means to match the R044 scale analysis and the declared prompt-cluster experimental unit. Both estimands are valid but answer slightly different questions; they must not be mixed in one table.

## Equal-trial ablation estimates used in the manuscript

| Comparison | Metric | Difference | Prompt-cluster 95% CI |
|---|---|---:|---:|
| top-4 minus top-2 | correction rate | +0.003538 | [-0.006502, +0.013429] |
| top-4 minus top-2 | retained source mass | +0.110041 | [+0.089649, +0.130794] |
| top-4 minus top-2 | truncation component, nats/token | -0.184030 | [-0.219891, -0.149524] |
| top-4 minus top-2 | shared-contract exact rate | -0.251365 | [-0.276987, -0.227156] |
| top-4 minus top-2 | sparse/full record ratio | +0.004717 | [-0.008748, +0.017625] |
| top-4 minus top-2 | sentence-completion rate | -0.200000 | [-0.400000, -0.050000] |
| reverse minus forward top-2 | correction rate | +0.000105 | [-0.009953, +0.010027] |
| reverse minus forward top-2 | retained source mass | -0.004347 | [-0.019285, +0.010385] |
| reverse minus forward top-2 | truncation component, nats/token | +0.007755 | [-0.020418, +0.036529] |
| reverse minus forward top-2 | shared-contract exact rate | -0.000827 | [-0.014956, +0.014300] |
| reverse minus forward top-2 | sparse/full record ratio | +0.000140 | [-0.013629, +0.013534] |
| reverse minus forward top-2 | sentence-completion rate | -0.050000 | [-0.150000, 0.000000] |

## Interpretation

- Intervals that include zero are described as "no detected change", not equivalence.
- The fixed prompt set is not a random sample from a formally defined prompt population.
- Seeds are repeated stochastic trajectories, not independent prompt samples.
- No null-hypothesis significance tests or multiplicity-adjusted *P* values are used.
