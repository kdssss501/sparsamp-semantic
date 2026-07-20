# R041: Sparse Precision Replay Certificates

## Material Passport

- Origin Skill: experiment-agent
- Origin Mode: plan
- Origin Date: 2026-07-20
- Verification Status: UNVERIFIED
- Version Label: r041_replay_certificate_plan_v1

## Experiment Overview

- **Title**: Sparse Precision Replay Certificates for Cross-Precision LLM Generation
- **Objective**: Reproduce an FP32-generated stochastic token sequence under FP16 while recording only precision-induced decision corrections.
- **Hypothesis**: A shared integer next-token contract leaves few FP32/FP16 decision disagreements, so a sparse correction manifest is substantially smaller than a full token trace.
- **Type**: deterministic GPU benchmark

This stage carries no hidden payload and does not evaluate covert communication. The certificate contains explicit step indices and reference token IDs for experiment replay.

## Method

At every shared prefix, both precisions derive a top-2 integer distribution from:

```text
top_p=1.0, envelope_top_k=16, contract_top_k=2,
logit_quantum=0.5, mass_bits=16, temperature=1.2
```

Candidates are ordered by token ID. A public seed produces the same exact rational sample at both precisions. If the local FP16 choice differs from the FP32 reference choice, the manifest records `(step, reference_token_id)`. Replay applies that explicit correction and continues from the reference prefix.

Baselines:

1. Independent seeded replay without corrections.
2. Deterministic greedy selection over the same integer contract.
3. Full token trace storing every reference token.
4. Sparse correction manifest.

## Setup

- **Language/Framework**: Python 3.11, PyTorch, Transformers
- **Working Directory**: `C:\Users\41462\Documents\隐写`
- **Model**: local GPT-2
- **Hardware**: NVIDIA RTX 3060 Laptop GPU, 6 GB
- **Checkpointing**: one atomic JSON update after every prompt/seed/policy unit

## Inputs

| Input | Path | Description |
|---|---|---|
| GPT-2 | `models/gpt2` | FP32 reference and FP16 replay model |
| Prompts | experiment script | Three public reproducibility prompts |
| Seeds | `0,1` | Public sampling seeds |

## Expected Outputs

| Output | Path | Format | Success Criterion |
|---|---|---|---|
| Pilot report | `outputs/R041_gpt2_replay_certificate.json` | JSON | all configured units complete |
| Research log | `refine-logs/R041_REPLAY_CERTIFICATE.md` | Markdown | metrics and limitations recorded |

## Monitoring Configuration

- **Timeout**: 20 minutes
- **Monitor file**: `outputs/R041_gpt2_replay_certificate.json`
- **Experiment type**: deterministic benchmark
- **Progress unit**: one prompt/seed/policy row

## Analysis Plan

- **Primary metric**: corrected replay exact-sequence success.
- **Secondary metrics**: correction rate, uncorrected common-prefix length, reference-token envelope coverage, sparse/full trace byte ratio, latency, source mass, quantization KL/TV.
- **GO**: corrected replay `6/6` for seeded sampling, top-16 reference-token coverage `100%`, mean correction rate `<=10%`, and sparse payload `<50%` of full trace payload.
- **NO-GO**: any corrected replay failure or correction rate `>25%`.
- **Next gate**: only a GPT-2 GO permits Qwen FP16/BF16 semantic evaluation.

The sparse certificate guarantees exact replay only when its corrections and public configuration are available. It is not a claim that FP32 and FP16 distributions are identical, and all quantization/truncation bias remains separately reportable.
