# R049 Complete Replay Cost Analysis

## Material Passport

- Origin Skill: academic-research-suite `experiment-agent`
- Origin Mode: validate
- Verification Status: ANALYZED
- Reference bundle: `outputs\R047_reference_seed0.json`
- Target report: `outputs\R047_local_target.json`

## Results

| Metric | Value |
|---|---:|
| Trials | 20 |
| Generated tokens | 1500 |
| Corrections | 30 |
| Corrected exact | 20/20 |
| Uncorrected exact | 5/20 |
| Mean trial correction rate | 2.0543% |
| Binary manifest payload | 247 bytes |
| Binary full token trace | 3,715 bytes |
| Payload-only ratio | 6.6487% |
| Complete certificate package | 6,136 bytes |
| Complete full-trace package | 9,604 bytes |
| Complete-package ratio | 63.8900% |
| Complete certificate cost | 32.725 bits/token |
| Referenced compact certificate | 1,148 bytes |
| Referenced compact full trace | 4,636 bytes |
| Referenced compact ratio | 24.7627% |
| Referenced compact cost | 6.123 bits/token |
| Manifest construction throughput | 11.53 tokens/s |
| Corrected replay throughput | 11.50 tokens/s |
| Uncorrected replay throughput | 11.90 tokens/s |

## Interpretation

- The payload-only ratio measures the versioned binary manifest against a varint full token trace.
- The complete-package ratio additionally includes one shared contract header and one identity header per trial in both comparators.
- The referenced compact ratio uses fixed SHA-256 identifiers for an externally shared reference bundle, model and target environment; it does not repeat the full JSON contract.
- Certificate construction and corrected replay each require one target-model pass. The uncorrected pass is an evaluation baseline and is not part of operational replay.
- Timing is hardware dependent and is not a cross-environment reproducibility metric.
