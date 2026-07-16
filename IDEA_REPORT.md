# ARIS Idea Discovery Report

**Direction**: Practical, high-performance SparSamp extensions  
**Date**: 2026-07-17

## Executive Summary

The recommended direction is **Finite-Horizon Precision-Hardened SparSamp (FH-SparSamp)**: replace
fixed-size, floating-probability interval progression with a public, message-independent adaptive
schedule and deterministic integer probability mass allocation. The target is not merely higher
conditional bit/token, but higher authenticated-message completion probability under a fixed token
budget while resisting finite-precision detection.

The best backup direction is **DriftGuard API-SparSamp**, a bounded-bias protocol for black-box
top-20 APIs with probability drift, erasures, fingerprints, and cost-aware coding.

## Ranked Ideas

### 1. FH-SparSamp: Finite-Horizon, Precision-Hardened Sampling

**Status**: Recommended for local pilot  
**Hypothesis**: A block schedule derived only from public next-token distribution statistics and
remaining token budget can reduce the long tail of payload completion, while deterministic integer
mass allocation improves replay across precision modes and reduces low-probability-vanishing
artifacts.

Core components:

1. Estimate per-step min-entropy and a conservative completion-risk score.
2. Choose the next block size from `{2,4,8,16,32}` using only public state.
3. Convert probabilities to a fixed integer mass with deterministic residual allocation.
4. Record the exact quantization contract and model fingerprint in the artifact.
5. After payload completion, sample a short native tail until a sentence boundary or EOS.

Why it may be novel:

- Existing capacity work optimizes asymptotic or average rate; this idea centers authenticated
  completion probability under a hard token budget.
- Existing precision attacks motivate a constructive, bit-exact defense rather than only detection.

Novelty risks:

- ANStega and list decoding may already cover part of the finite-state efficiency story.
- Bit-exact inference work may provide stronger primitives that should be reused rather than
  reimplemented.

Fast pilot:

- 20 prompts x 3 payload seeds.
- Compare fixed block 8/16/32 against adaptive schedule at 256/512/1024 tokens.
- Stop if completion gain is below 10 percentage points or detector AUC worsens by more than 0.02.

### 2. DriftGuard API-SparSamp

**Status**: Strong backup, blocked on API key  
**Hypothesis**: Guard-banded probability buckets, erasure-aware coding, and model fingerprinting can
achieve useful end-to-end recovery on top-20 APIs while reporting a defensible truncation-bias and
cost budget.

Core components:

- Measure repeated-query candidate churn and logprob drift.
- Embed only when observed mass and bucket margins exceed thresholds.
- Treat unstable positions as erasures rather than hard errors.
- Use short fountain/LDPC-style outer coding instead of simple repetition.
- Bind every frame to provider fingerprint, timestamp window, prompt hash, and tokenizer revision.

Success target:

- At least 95% complete-message recovery on 100 prompts under the same model fingerprint.
- Explicitly bounded observed-mass KL and fewer than 2 API requests per emitted token.

### 3. Prompt Capacity Controller

**Status**: Supporting component, not a standalone paper  
**Hypothesis**: A cheap native-generation probe can predict whether a prompt will sustain enough
entropy and response length for a payload, reducing failed or truncated covers.

Use public features only: early entropy trajectory, EOS hazard, response-format class, punctuation
rate, and requested answer length. Optimize completion probability and semantic completeness, not
payload-dependent prompt selection.

### 4. Semantic Finishing Tail

**Status**: Must-have engineering ablation  
After payload completion, continue native sampling to a sentence boundary. This should improve human
ratings and reduce obvious truncation without changing the already emitted steganographic prefix.

### 5. Canonical Token Filtering

**Status**: Eliminated as dominant contribution  
The problem is real, but ReTokSync is a stronger and more recent direct baseline. Retain only as a
simple baseline and diagnostic.

### 6. Replace SparSamp with ANS

**Status**: Eliminated  
ANStega already occupies this contribution space. Reimplement only for comparison if code is
available.

## Recommended Paper Framing

**Primary claim**: finite-horizon authenticated-payload completion can be improved without using
message-dependent control decisions.  
**Supporting claim**: deterministic integer probability contracts improve cross-precision replay and
reduce finite-precision steganalysis signals.

Do not combine the DeepSeek API story into the same primary paper unless it produces strong data;
otherwise it should be a separate systems/security extension.
