# Peer Review Report - R2 Domain

## Manuscript Information

- **Title:** Sparse correction certificates recover stochastic language generation across numerical precision
- **Manuscript ID:** SPRC-STAGE3-001
- **Review Date:** 2026-07-21
- **Review Round:** 1

## Reviewer Information

- **Role:** Peer Reviewer 2 - Domain
- **Identity:** Researcher in provably secure sampling, linguistic steganography, range coding, list decoding and tokenization synchronization.
- **Focus:** Domain accuracy, mechanism novelty and comparison with adjacent probability-partition methods.

## Overall Assessment

- **Recommendation:** Major Revision
- **Confidence:** 4/5

The manuscript repurposes deterministic probability partitioning ideas into a target-specific replay contract: a reference path is sampled from an integerized top-*k* distribution and only target-side token disagreements are stored. The paper is careful not to claim secrecy, zero KL or full-distribution preservation, and its SparSamp compatibility reproduction is credible within the disclosed dependency limitations. The result is relevant to stochastic inference reproducibility, but the scientific distinction from sparse delta encoding is not yet isolated. SparSamp, range coding, list decoding, dyadic approximation and ReTokSync are cited, yet the paper does not provide a mechanism-level comparison of their objectives, shared state, guarantees, complexity and failure modes. Top-two retains only 0.734 source mass in the key ablation, making the method a replay mechanism for a substantially truncated generator rather than a drop-in reproduction layer for native generation. I recommend major revision to clarify novelty, add direct replay baselines and quantify the complete distributional cost.

## Strengths

### S1: Security and replay claims are not conflated

The Methods explicitly says the public-seed construction is not a cryptographic secrecy claim, while the Claim-Evidence Map prohibits “secure” or “undetectable.” This is essential given the paper's SparSamp lineage.

### S2: Finite-precision direction of KL is handled correctly

The paper identifies `-log(Z)` as (D_{KL}(Q\|\widetilde P)) after conditioning and notes that the opposite direction is infinite when source support is removed. This is technically correct and appropriately limited to the pre-apportionment distribution.

### S3: Token Ambiguity is reported rather than hidden

The official reproduction reports 347 completed Token Ambiguity trials separately and restricts exact-decoding denominators consistently with the original paper's condition.

### S4: Top-*k* is presented as a trade-off

The manuscript reports that top-four raises retained mass by 0.110 and lowers the truncation component by 0.184 nats/token while worsening shared-contract exactness. It does not call top-four uniformly better.

## Weaknesses

### W1: Direct novelty baseline is missing

**Problem:** No baseline stores target-reference disagreement positions under native sampling, quantized sampling without canonical mass, periodic checkpoints or ordinary delta encoding.

**Why it matters:** The certificate may be a compact trace representation rather than a new sampling or replay principle.

**Suggestion:** Compare against at least full trace, native-token delta, periodic checkpoint plus suffix replay and deterministic integer-contract replay without sparse correction. Equalize target access and metadata.

**Severity:** Major.

### W2: Prior-work integration remains citation-level

**Problem:** List decoding, dyadic approximation and ReTokSync appear mainly in one Discussion paragraph; their threat models and objectives are not compared.

**Why it matters:** Readers cannot determine whether the contribution is orthogonal, subsumed or composable.

**Suggestion:** Add a structured table covering channel goal, probability access, distribution guarantee, shared secret/state, decoder queries, Token Ambiguity handling and public code.

**Severity:** Major.

### W3: The generated distribution is heavily altered

**Problem:** Top-two retains 0.734 source mass and has a 0.382-nat/token truncation component in the one-seed ablation. Integer apportionment adds unreported error.

**Why it matters:** Exact replay of the contract generator does not establish replay of native Qwen behavior or language quality.

**Suggestion:** Add native Qwen sampling as a quality/distribution baseline and report full (Q\) versus original (P\) divergence bounds, clearly separating infinite forward KL from finite TV or reverse KL.

**Severity:** Major.

### W4: The relation to SparSamp is conceptually unclear

**Problem:** The paper begins with an official SparSamp reproduction but the proposed certificate neither embeds a secret message nor preserves SparSamp's security objective.

**Why it matters:** The reproduction may look like inherited validation for a different method.

**Suggestion:** State exactly which primitives are inherited (shared partitions, canonical sampling) and which claims are discarded; consider moving the reproduction to the supplement unless it validates shared code paths.

**Severity:** Major.

### W5: No public-text synchronization experiment

**Problem:** Recovery is evaluated only over token identifiers under a shared tokenizer.

**Why it matters:** Linguistic channels commonly fail when rendered text is normalized or re-tokenized.

**Suggestion:** Keep this outside the central claim, but include a small ReTokSync-style on/off probe or explicitly rename the output as a token-trace certificate.

**Severity:** Minor.

## Detailed Comments

- **Introduction:** Replace “shared-randomness sampling methods” with a taxonomy that separates message coding, distribution coupling and replay.
- **Results:** Report native Qwen completion/quality beside top-two and top-four; punctuation completion is not enough.
- **Methods:** Provide pseudocode and computational complexity for construction and replay.
- **Discussion:** Explain whether list decoding could reduce correction payload without changing the integer contract.
- **References:** Nine references are insufficient for a paper whose novelty spans sampling, replay, deterministic inference and research artifacts.

## Questions for Authors

1. What component of SPRC is not equivalent to delta-encoding the reference token trace against a target-generated trace evaluated on the reference prefix?
2. Why is top-two the appropriate default when it discards roughly one quarter of the quantized source mass?
3. Does the official SparSamp reproduction share executable primitives with SPRC, or is it contextual validation only?
4. How would ANS/range/list coding change certificate payload if all methods received the same integer counts?

## Minor Issues

- Define “shared-contract exactness” at first use in Results.
- Avoid “capacity” when discussing replay package ratios; no hidden-message capacity is measured.
- Use one notation for the quantized full distribution throughout the text and supplement.

## Contract Dimension Status

| Dimension | Status | Rationale |
|---|---|---|
| D1 methodology_rigor | warn | Main experiment is internally valid, but direct replay baselines and native quality controls are missing. |
| D2 domain_accuracy | warn | Individual statements are careful; prior-work and full-distribution positioning are incomplete. |
| D3 argumentative_coherence | warn | The target-specific claim holds, but the unique scientific mechanism is not isolated from delta encoding. |
| D4 cross_disciplinary_relevance | warn | Strong potential connection, not yet demonstrated beyond token-ID replay. |
| D5 writing_and_structure | warn | Clear prose, but a taxonomy, algorithm and comparison table are needed. |

## Numeric Dimension Scores

| Dimension | Score | Descriptor |
|---|---:|---|
| Originality | 61 | Adequate |
| Methodological Rigor | 72 | Strong |
| Evidence Sufficiency | 60 | Adequate |
| Argument Coherence | 72 | Strong |
| Writing Quality | 80 | Strong |
| Literature Integration | 58 | Adequate |
| Weighted Average | 67 | Major Revision |

## Failure Conditions

- **F0:** not fired.
- **F1:** not fired.
- **F2:** candidate fired at panel aggregation because all three mandatory dimensions are warn.
- **F3:** not fired by this review.

[CONTRACT-ACKNOWLEDGED]
