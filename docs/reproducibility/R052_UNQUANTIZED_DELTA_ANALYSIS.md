# R052 Unquantized Delta Analysis

## Material Passport

- Origin: Stage 4 direct mechanism baseline
- Verification status: ANALYZED
- SPRC target report: outputs\R047_local_target.json
- SPRC SHA-256: 3b0a154455968c15427a66405ab4c7fdbe6203eb017a27a127ee722ec56a6ea0
- Unquantized report: outputs\R052_unquantized_delta.json
- Unquantized SHA-256: f3fa225acd686cfcc81062b68633625fc136e22fb0eec64c976aab3f4f5a1a52
- Paired prompt bootstrap: 10,000 resamples
- Bootstrap seed: 20260721

## Results

| Method | Exact | Mean correction rate | Delta vs SPRC [95% CI] | Referenced bytes | Bits/token | Support shortfall |
|---|---:|---:|---:|---:|---:|---:|
| SPRC | 20/20 | 2.054% | reference | 1,148 | 6.123 | 0 |
| top-16 | 20/20 | 25.454% | +23.400 pp [+21.149, +25.938] | 2,371 | 12.645 | 1 |
| top-2 | 20/20 | 3.178% | +1.123 pp [+0.171, +2.015] | 1,200 | 6.400 | 0 |

## Interpretation

- Removing logit-bin and integer-mass contracts while retaining top-2 increased mean correction rate by 1.123 percentage points; its paired interval is [+0.171, +2.015].
- The unquantized top-2 package was +52 bytes relative to SPRC under the same referenced boundary.
- Expanding to a positive-support top-16 cap increased correction density to 25.454% and produced 1 finite-precision support-shortfall step.
- Exact recovery remains a manifest integrity property for every method and is not used to claim statistical superiority.
- This is one BF16 target stack and one public seed per prompt; the interval describes the frozen prompt set.
