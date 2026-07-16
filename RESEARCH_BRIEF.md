# Research Brief: Practical SparSamp for Instruction LLMs

**Date**: 2026-07-17
**Reference**: SparSamp, USENIX Security 2025, arXiv:2503.19499

## Problem Anchor

Reproduce SparSamp faithfully, then study whether provably secure sampling can become a
practical text channel for instruction-tuned LLMs under finite token budgets, finite-precision
inference, tokenizer ambiguity, and black-box API constraints.

## Current System

- Model-independent sparse interval codec with HMAC-SHA256 sampling state.
- ChaCha20-Poly1305 payload framing and optional repetition coding.
- Full-distribution local Hugging Face provider and top-20 DeepSeek provider.
- Qwen2.5-1.5B-Instruct FP16 on an RTX 3060 Laptop GPU with 6GB VRAM.
- FastAPI + Vue research workbench with separate token-ID and public-text decode modes.

## Evidence Available

| Evidence | Result | Strength |
|---|---:|---|
| Unit/API tests | 21 passing | Engineering evidence |
| Qwen block grid, one prompt/payload | 0.985-1.208 bit/token | Pilot only |
| Best pilot block size | 8, 1.208 bit/token | Not statistically established |
| Web artifacts | 264-428 tokens, 0.991-1.269 bit/token | Four samples only |
| Token-ID artifact decode | Exact recovery of `A-17` | Verified |
| Public-text decode | At least one failure from mid-sequence retokenization | Verified failure mode |
| Real model semantics | Coherent Chinese explanatory text | Qualitative only |

## Known Weaknesses

1. The official GPT-2 artifact experiments E1-E3 have not yet been reproduced and compared.
2. The current Qwen evidence uses too few prompts, keys, payload nonces, and seeds.
3. Distribution preservation is argued from the algorithm but not audited against finite-precision
   detectors or empirical steganalysis.
4. Token-ID recovery is not a realistic public-text channel; it is only a reproducibility oracle.
5. Generation stops immediately when the payload completes, so cover text can end mid-sentence.
6. The API extension has mock coverage but no paid DeepSeek drift study yet.

## Constraints

- One RTX 3060 Laptop GPU, 6GB VRAM.
- Primary local model: Qwen2.5-1.5B-Instruct FP16.
- Pilot budget: at most 8 GPU-hours before selecting the paper direction.
- No DeepSeek key is currently committed or assumed.
- Model weights, keys, outputs, caches, and recordings must remain outside Git.

## Threat Model

- Sender and receiver share a secret key, prompt contract, model revision, tokenizer, and decoding
  parameters unless an experiment explicitly removes one assumption.
- The warden observes surface text and may run statistical or learned steganalysis.
- Public channels may retokenize, normalize, or lightly rewrite text.
- Black-box providers may change top-k candidates, probabilities, or model fingerprints over time.

## Research Non-Goals

- Claiming that a top-20 API reproduces full-distribution SparSamp.
- Claiming zero KL under truncation, filtering, finite quantization, or API drift without proof.
- Treating larger language models alone as a research contribution.
- Rebranding token synchronization or ANS coding already covered by 2026 work.

## Candidate Paper Thesis

Instruction LLM steganography needs a finite-horizon reliability objective in addition to
asymptotic distribution preservation: a practical scheme should complete authenticated payloads
within a fixed token budget, remain bit-exact under finite precision, and report public-text
recoverability separately from token-ID recovery.
