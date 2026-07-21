# R051 Matched Replay Baselines

## Material Passport

- Origin: Stage 4 response to EIC/domain review
- Verification status: ANALYZED
- Reference bundle: `outputs\R047_reference_seed0.json`
- Reference SHA-256: `3db563f6e569828689e82b06184d439cdb12cfe78d9b5bdd4b5ec3d2601ff76c`
- Target report: `outputs\R047_local_target.json`
- Target SHA-256: `3b0a154455968c15427a66405ab4c7fdbe6203eb017a27a127ee722ec56a6ea0`

## Results

| Method | Exact | Referenced bytes | Full-trace ratio | Bits/token | Target passes | Target-specific |
|---|---:|---:|---:|---:|---:|---|
| seed_only | 5/20 | 901 | 19.43% | 4.805 | 1 | no |
| sparse_precision_replay_certificate | 20/20 | 1,148 | 24.76% | 6.123 | 2 | yes |
| full_token_trace | 20/20 | 4,636 | 100.00% | 24.725 | 0 | no |
| block_repair_4 | 20/20 | 1,408 | 30.37% | 7.509 | 2 | yes |
| block_repair_8 | 20/20 | 1,655 | 35.70% | 8.827 | 2 | yes |
| block_repair_16 | 20/20 | 1,963 | 42.34% | 10.469 | 2 | yes |
| block_repair_32 | 20/20 | 2,553 | 55.07% | 13.616 | 2 | yes |

## Missing Baseline

- `native_softmax_target_conditioned_delta`: Requires a new GPU run that samples the unquantized native distribution on each frozen reference prefix; current artifacts do not store those choices.

## Interpretation

- All byte results use the same referenced header and per-trial identity record.
- A block baseline stores every reference token in each fixed block containing at least one SPRC correction; it is exact under the same target-conditioned assumptions but coarser than token-level repair.
- Pass counts are logical target-model passes; block repair may skip generation inside stored blocks but that optimization is not timed here.
- Seed-only is the zero-payload stochastic replay control and is not exact for most trials.
- Full trace is target-independent and exact, but it bypasses model replay; its zero-pass property must be considered alongside byte cost.
