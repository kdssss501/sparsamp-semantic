# Claim-Evidence Map

## One-sentence argument

In stochastic autoregressive language generation, we show that a canonical integer next-token contract combined with target-specific sparse correction certificates reconstructs Qwen token trajectories across FP16 and BF16, supported by 60/60 exact corrected replays with a 2.16% mean correction rate, while limiting the claim to one model, one GPU stack and known replay environments.

## Major claims

| ID | Claim | Evidence | Status | Boundary or required action |
|---|---|---|---|---|
| C0 | The unchanged official SparSamp algorithm reproduces the published GPT-2 capacity trend and no-TA decoding property in a compatible modern environment. | R001 Basic exact decode; R002 846/846 no-TA exact decode and 16/16 capacity checks within 5%, maximum relative error 4.12%. | Supported with limitations | Seven large-block trials exhausted the 200-token ceiling. PyTorch 2.7.1 + Transformers 4.41.2 is a compatibility environment, not strict Torch 2.2.2. Absolute speed is not a fidelity gate. |
| C1 | A shared public seed alone does not reliably reproduce a stochastic Qwen trajectory across FP16 and BF16. | R044: uncorrected exact replay 10/60; mean common exact prefix 39.45 tokens. | Supported in tested setting | Do not generalize to all models, kernels or decoding modes. |
| C2 | A complete target-specific sparse correction manifest yields exact token replay. | Inductive construction in `replay_certificate.py`; R041 6/6, R044 60/60, R045 20/20 and R046 20/20. | Supported conditionally | Requires identical model, tokenizer, prompt, public configuration and the target environment used during certificate construction. |
| C3 | Cross-precision disagreements are sparse for the tested Qwen configuration. | R044 mean correction rate 2.1606%, prompt-cluster 95% CI 1.8014-2.5277%; maximum 6.1538%. | Supported | Evidence is one Qwen checkpoint and one GPU stack. |
| C4 | A compact certificate can be smaller than the matching full-token trace when the package boundary is explicit. | R044 legacy fixed-width payload ratio 2.8808% [2.3960, 3.3571%]; R049 seed-0 versioned payload ratio 6.65%, referenced compact package ratio 24.76%, self-contained JSON package ratio 63.89%. | Supported for the audited bundle | The figures are different estimands. The compact ratio assumes an externally shared reference bundle; none may be described as total end-to-end transfer cost without naming its boundary. |
| C5 | Corrected replay is stable in both FP16/BF16 directions in the tested environment. | Forward and reverse top-two ablations each 20/20; equal-trial correction-rate delta +0.00010, paired cluster CI -0.00995 to +0.01003. | Partially supported | Only one public seed in the direction ablation and no independent hardware. |
| C6 | Increasing contract support improves retained-mass fidelity but not replay sparsity. | Equal-trial paired analysis, top-four minus top-two: source mass +0.1100 [0.0896, 0.1308], truncation component -0.1840 [-0.2199, -0.1495], correction rate +0.00354 [-0.00650, 0.01343]. | Supported for controlled ablation | Top-*k* changes the generated trajectory; pairing is by prompt/seed, not token. |
| C7 | Top-four reduces semantic quality. | Structural sentence completion 16/20 versus 20/20, paired difference -0.20 [-0.40, -0.05]; R048 has prepared blinded native/top-two/top-four materials but collected no ratings. | Needs evidence | Sentence punctuation is not semantic quality. R048 remains `ETHICS_PENDING`; no human-quality claim is permitted. |
| C8 | The method preserves the full model distribution or has zero KL divergence. | Top-two retained mass approximately 0.75 and truncation component approximately 0.353 nats/token; integer apportionment error not separately isolated. | Unsupported and contradicted | Prohibit zero-KL or distribution-preservation wording. |
| C9 | Certificates generalize to unseen hardware, kernels or model revisions. | R047 source-machine target smoke reproduced 20/20, but used the same RTX 3060 Laptop GPU and software installation. | Needs evidence | The external bundle and runner are ready; run the frozen top-two protocol on a genuinely independent GPU/CUDA stack. |
| C11 | The external replay package can reconstruct the frozen seed-0 subset without copying a target manifest. | R047 reference-only bundle plus fresh target construction reproduced 20/20 corrected and 5/20 uncorrected trajectories; full model-directory SHA-256 was verified before replay. | Supported as a source-machine packaging smoke | This validates package separation and checkpoint/resume, not cross-system portability. |
| C10 | Public surface text can be re-tokenized and still reconstruct the trajectory. | Current study replays token identifiers under a shared tokenizer. | Unsupported | ReTokSync-style evaluation is a separate future experiment. |

## Claim wording allowed in the manuscript

- "Recovered all 60 tested FP16-to-BF16 Qwen trajectories with a mean correction rate of 2.16%."
- "The official GPT-2 compatibility matrix achieved 846/846 exact no-ambiguity decodes, with all 16 capacity comparisons within 5% of the published values."
- "The certificate provides exact replay conditional on a fixed target environment and a complete correction manifest."
- "Top-four retained more source mass but did not reduce correction density in the 20-prompt ablation."
- "The results support bidirectional FP16/BF16 replay on the tested software and hardware stack."
- "For the seed-0 bundle, the compact referenced certificate was 24.76% of the matching referenced full trace; the self-contained JSON audit package was 63.89%."

## Claim wording prohibited before additional evidence

- "Universally deterministic across hardware."
- "Distribution preserving" or "zero KL."
- "Semantically equivalent to native generation."
- "Secure" or "undetectable" on the basis of replay experiments.
- "The first method" without a completed novelty review.
- "Strict reproduction of the official dependency environment."
- "Statistically identical" when a confidence interval merely includes zero.

## Paragraph architecture

1. Context: stochastic LLM evaluation needs reproducible trajectories.
2. Gap: seed synchronization and higher precision do not provide compact cross-precision reconstruction.
3. Method: public discrete contract plus sparse target-specific corrections.
4. Main evidence: 60/60 corrected versus 10/60 uncorrected; 2.16% correction density.
5. Mechanism: candidate coverage and contract agreement explain sparsity.
6. Trade-off: top-four improves retained mass but weakens agreement and completion.
7. Generalization test: reverse precision direction succeeds in the same stack.
8. Boundary: one checkpoint, one GPU, token-ID channel and no blinded quality study.
