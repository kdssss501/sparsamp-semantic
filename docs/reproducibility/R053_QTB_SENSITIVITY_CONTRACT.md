# R053 Bounded q/T/B Sensitivity Contract

## Purpose

This contract addresses the residual Stage 3' request for parameter sensitivity without claiming a global optimum. It is a one-factor-at-a-time extension around the frozen Qwen2.5-1.5B-Instruct reference configuration.

## Frozen baseline

| Parameter | Baseline |
|---|---:|
| reference/replay dtype | FP16/BF16 |
| `contract_top_k` | 2 |
| `logit_quantum` (`q`) | 0.5 |
| `temperature` (`T`) | 1.2 |
| `mass_bits` (`B`) | 16 |
| prompts | 20 bilingual prompts in `configs/reproducibility/r044_prompts.json` |
| seed | 0 |
| maximum tokens | 96 |
| minimum sentence-stop tokens | 64 |

The already completed R044 result is the baseline. Existing R045 supplies the `k=4` comparison.

## Prespecified variants

Each row changes exactly one parameter and retains all other baseline values:

| Variant family | Values |
|---|---|
| `q` | 0.25, 1.0 |
| `T` | 1.0, 1.4 |
| `B` | 12, 20 |

The six variants contain 20 prompts each and use one public seed. Every trial is written to its own resumable output file. No variant is selected or discarded based on an intermediate result.

## Primary and secondary outcomes

- Primary empirical outcome: correction density.
- Integrity gate: corrected token sequence must equal the reference sequence.
- Secondary outcomes: exact success count, retained source mass, truncation component, referenced bytes, target passes, sentence endpoint, target candidate coverage and runtime.

Results will be reported as descriptive estimates with prompt-cluster bootstrap intervals where the checkpoint contains complete trials. No global optimum or causal effect across the full parameter space will be claimed.

## Reproducibility and stopping rule

The runner must preserve the exact experiment signature, model fingerprint, prompt hash, command line and per-trial atomic checkpoint. A configuration mismatch is a hard error. A stopped process is resumed from its existing checkpoint; `--fresh` is prohibited for an existing variant unless the old file is archived first. The study ends after all six variants and the frozen baseline are complete, including failures and budget exhaustion.
