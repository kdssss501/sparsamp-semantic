# R053 Bounded q/T/B Sensitivity

## Material Passport

- Verification status: ANALYZED
- Selected public seed: 0
- Prompt bootstrap: 10,000 resamples
- Analysis signature: `29b2d9cae6d9f2c5ca3502f826106d23c745d3ed59e6a28b5ca83b8c4898c192`

## Results

| Variant | q | T | B | Exact | Correction rate | Delta vs baseline (95% CI) | Source mass | Referenced bytes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 0.5 | 1.2 | 16 | 20/20 | 0.0200 | reference | 0.7335 | 1,148 |
| q025 | 0.25 | 1.2 | 16 | 20/20 | 0.0250 | +0.0050 [-0.0061, +0.0155] | 0.7465 | 1,178 |
| q100 | 1.0 | 1.2 | 16 | 20/20 | 0.0206 | +0.0006 [-0.0090, +0.0101] | 0.7517 | 1,141 |
| t100 | 0.5 | 1.0 | 16 | 20/20 | 0.0307 | +0.0107 [-0.0025, +0.0236] | 0.8163 | 1,212 |
| t140 | 0.5 | 1.4 | 16 | 20/20 | 0.0236 | +0.0036 [-0.0080, +0.0143] | 0.6783 | 1,168 |
| b12 | 0.5 | 1.2 | 12 | 20/20 | 0.0307 | +0.0107 [-0.0040, +0.0251] | 0.7516 | 1,212 |
| b20 | 0.5 | 1.2 | 20 | 20/20 | 0.0172 | -0.0028 [-0.0116, +0.0054] | 0.7468 | 1,131 |

## Decision

- All 140 analyzed trials passed the corrected-exact integrity gate.
- The lowest observed correction density was `b20` at 1.7207%.
- Its paired change from baseline was -0.2793% (prompt-bootstrap 95% CI -1.1592% to +0.5372%).
- Baseline referenced size was 1,148 bytes; byte differences include changed trajectory lengths and manifests.
- This bounded one-seed OFAT study identifies local sensitivity, not a global optimum.

## Interpretation Boundary

Parameter changes participate in reference sampling, so comparisons are paired by prompt and public seed rather than by identical token trajectory. Exact recovery remains a protocol gate. Correction density, retained mass and package bytes are empirical outcomes for one model and GPU stack.
