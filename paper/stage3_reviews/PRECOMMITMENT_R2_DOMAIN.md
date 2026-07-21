# Phase 1 Precommitment - R2 Domain

## Contract Paraphrase

- D1 mandatory: experiments and artifact comparisons must support the sampling and replay claims.
- D2 mandatory: SparSamp, PSS, range coding, finite precision, dyadic coding and tokenization work must be represented accurately.
- D3 mandatory: the paper must distinguish a new scientific mechanism from a repackaged sparse trace.
- D4 high: the connection to language-model sampling and reproducibility communities must be substantive.
- D5 normal: definitions, notation and comparison tables must permit domain evaluation.

## D1-D5 Scoring Plan

| dimension_id | what_to_look_for | what_triggers_block | what_triggers_warn |
|---|---|---|---|
| D1 | Fair baselines, fixed contracts, token-level evidence and compatibility reproduction | Baselines are incomparable or the main replay experiment cannot support its outcome | Baselines omit direct replay/logging alternatives or scale is narrow |
| D2 | Accuracy and completeness of prior-work positioning and probability claims | Security/distribution claims are false or a direct predecessor is misrepresented | Related work is cited but mechanism-level comparison is shallow |
| D3 | Novelty of target-conditioned corrections versus delta encoding/checkpointing | The central contribution collapses entirely to an unacknowledged known mechanism | The method is useful but its novel scientific component is not isolated |
| D4 | Relevance to stochastic decoding, audit and reproducibility | The paper invokes adjacent fields without a real transferable insight | Relevance exists but is not demonstrated outside Qwen FP16/BF16 |
| D5 | Formal definitions, notation, terminology and result organization | Ambiguity prevents mathematical assessment | A comparison table or explicit algorithm is missing |

[CONTRACT-ACKNOWLEDGED]
