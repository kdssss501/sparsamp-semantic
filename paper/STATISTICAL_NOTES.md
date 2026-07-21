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

## Serialization estimands

R044's 2.8808% value is a mean trial-level legacy estimate based on fixed-width step and token
identifiers with no shared header. R049 uses the 20 seed-0 trials and reports three separate
deterministic byte-count estimands:

| Estimand | Certificate | Full-trace comparator | Ratio |
|---|---:|---:|---:|
| Versioned binary payload only | 247 bytes | 3,715 bytes | 6.65% |
| Self-contained JSON audit package | 6,136 bytes | 9,604 bytes | 63.89% |
| Compact binary package referencing a shared bundle | 1,148 bytes | 4,636 bytes | 24.76% |

These values do not have sampling intervals because they are exact serialization lengths for one
frozen bundle. They must not be pooled with R044's prompt-cluster interval or presented as three
estimates of the same quantity. The referenced package costs 6.123 bits per generated token and
assumes that the identified reference bundle, model and target-environment contracts are available
to the recipient.

## R050 and R051 deterministic audits

R050 reports a mathematical upper bound, not a sample estimate. For the implemented base
support-preserving allocation, \(TV<2(k-1)/M\). Every saved seed-0 contract has \(k=2\) and
\(M=2^{16}\), so the per-step bound is \(1/32768\). It receives no bootstrap interval and must not
be added to KL terms with different directions.

R051 uses the same frozen 20-trial, 1,500-token seed-0 bundle as R049. Its package byte counts are
deterministic serialization lengths under one referenced header. Seed-only, SPRC, full trace and
block-repair records are therefore paired engineering controls, not draws from a prompt
population. No inferential interval is attached. The native-softmax delta baseline is missing and
must not be imputed from integer-contract choices.

R052 recomputes BF16 target distributions on the same frozen reference prefixes using the same
HMAC fraction but no logit-bin or integer-mass contract. The top-two minus SPRC correction-rate
difference is calculated per prompt and uses 10,000 paired prompt bootstrap resamples with seed
20260721. The interval describes variation across the fixed 20 prompts; it is not a population
confidence claim. Package-byte differences remain deterministic for the frozen bundle. The
top-16 variant is a positive-support cap because one BF16 step exposed only five non-zero
candidates.
