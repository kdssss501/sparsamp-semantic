# Sparse correction certificates recover stochastic language generation across numerical precision

**Authors:** AUTHOR_INPUT_NEEDED
**Affiliations:** AUTHOR_INPUT_NEEDED
**Corresponding author:** AUTHOR_INPUT_NEEDED
**Draft status:** v0.1, evidence-bounded manuscript draft
**Intended format:** Nature Communications-style computational methods article

## Abstract

Stochastic language generation is difficult to reproduce across numerical precision because small score changes can alter an early token and propagate through the autoregressive trajectory. Here we introduce sparse precision replay certificates, target-specific records for exact stochastic replay. The method quantizes relative logits onto a public grid, orders retained candidates canonically, maps their weights to a power-of-two integer mass and records a correction only when the target environment would otherwise choose a different token. In Qwen2.5-1.5B-Instruct experiments spanning 20 English and Chinese prompts and three public seeds, uncorrected FP16-to-BF16 replay reproduced 10 of 60 trajectories, whereas certificate-corrected replay reproduced 60 of 60. Corrections affected 2.16% of tokens on average (prompt-cluster bootstrap 95% confidence interval, 1.80-2.53%), and 58 of 60 outputs reached a public sentence endpoint. Reversing precision retained exact corrected recovery in 20 of 20 additional trials. Increasing contract support from two to four tokens reduced the measured truncation component by 0.184 nats per token but did not reduce correction density. These results establish compact replay for a known model and target precision; they do not establish target-independent determinism, zero distributional divergence or cross-hardware generality.

## Introduction

Reproducible inference is a prerequisite for comparing language models, auditing generated outputs and reconstructing computational experiments. This requirement is unusually difficult for stochastic autoregressive generation. Even when model weights, prompts, decoding parameters and pseudo-random seeds are held fixed, a small numerical change in one next-token distribution can move a sample across a decision boundary. The changed token then alters every subsequent conditional distribution. Recent work has documented substantial response and evaluation variability caused by batch configuration, accelerator type and reduced-precision arithmetic, including divergent reasoning paths and response lengths under nominally identical evaluation settings [1]. The practical question is therefore not only whether an implementation is deterministic on one machine, but whether a stochastic trajectory can be reconstructed when the numerical environment changes.

Existing approaches address complementary parts of this problem. Higher-precision execution can reduce numerical drift but increases memory or computational cost [1]. Verification methods can test whether an output remains plausible under a reference implementation, but verification does not itself reconstruct a chosen stochastic path [2]. Shared-randomness sampling methods developed for generative communication, including sparse sampling and range-coding approaches, demonstrate that public probability partitions can couple a message or random stream to autoregressive generation [3,4]. Their implementation, however, depends on candidate support, ordering and finite-precision probability boundaries. Finite-precision artifacts have also been shown to create detectable low-probability effects in language-model sampling pipelines [5]. Together, these findings motivate an explicit contract between probability computation and stochastic replay.

A strict bitwise contract over all model operations would be expensive and brittle. Conversely, recording the complete generated token sequence always guarantees replay but provides no compression and reveals nothing about where numerical precision actually changes a decision. We study an intermediate question: can a public discrete next-token contract make cross-precision disagreements sufficiently sparse that exact replay requires only a small correction record? This question separates two properties that are often conflated. Exact recovery is a deterministic property of applying a complete correction manifest. Sparsity is an empirical property of how often two numerical environments disagree under a specified contract.

We introduce sparse precision replay certificates (SPRCs) for target-specific stochastic reconstruction. At each generation step, relative logits are quantized to public integer bins, candidates are ranked under a fixed top-*k* envelope and contract candidates are ordered by token identifier. Their quantized weights are apportioned into an integer mass of size \(2^B\), and a public pseudo-random value selects a token. To construct a certificate, the reference trajectory is evaluated under the target environment while conditioning on the reference prefix. The certificate stores only pairs \((t,x_t)\) for steps at which the target contract choice differs from reference token \(x_t\). During replay, corrections are applied before extending the prefix, which prevents a local disagreement from cascading.

We evaluate this design first on GPT-2 and then on the instruction-tuned Qwen2.5-1.5B model [6]. The principal experiment contains 20 bilingual prompts, three public seeds and 60 FP16-to-BF16 trajectories. We measure exact token replay, correction density, correction-record size, sentence completion, candidate-envelope coverage and the distributional cost of logit quantization and support truncation. We further test a wider contract and reverse the precision direction. Across the main experiment, certificates recover all 60 reference trajectories while changing the target-side decision at 2.16% of token positions on average. The wider contract exposes a clear Pareto trade-off: it retains more source probability mass but does not reduce correction density and lowers cross-precision contract agreement. The resulting claim is deliberately bounded to a known model, tokenizer, prompt, sampling configuration and target numerical environment.

## Results

### Sparse certificates separate exact replay from numerical agreement

To test whether precision-induced disagreements are sparse, we generated a reference sequence in one numerical precision and recomputed the public contract in a second precision while forcing the second run to follow the reference prefix (Fig. 1). The local target choice was compared with the reference token at every step. A correction was emitted only for a mismatch. A fresh target run then used the same public seed and contract, applying the stored correction before appending each token.

The replay invariant is exact by construction. If the replay prefix equals the reference prefix through step \(t-1\), both certificate construction and replay evaluate the target contract on the same prefix. When the target choice equals the reference token, no correction is required; otherwise the manifest replaces the target choice with the recorded reference token. Induction therefore gives equality of the full token sequence, provided that the target model, tokenizer, prompt, contract configuration and correction manifest are unchanged. This statement does not imply that the reference and target distributions are identical. The empirical question is the number of corrections required to maintain the invariant.

In the GPT-2 pilot, six 64-token seeded trajectories were generated in FP32 and replayed in FP16. Uncorrected replay recovered two of six trajectories; corrected replay recovered all six. The mean correction rate was 2.34%, with a maximum of 6.25%, and the correction record occupied 3.52% of the corresponding full token trace. Three independent executions produced the same deterministic result signature. This pilot established that the audit pipeline could distinguish timing variability from token-level reproducibility before moving to an instruction-tuned model.

The first Qwen pilot used FP16 references and BF16 replay for six seeded 64-token trajectories. Only one uncorrected trajectory matched exactly, whereas all six corrected trajectories matched. The mean correction rate was 1.56%. The full integer contract agreed at 83.07% of shared-prefix steps, showing that contract differences were more common than final token-choice differences. None of the fixed 64-token outputs ended at a sentence boundary, so exact token reconstruction alone was insufficient as a user-facing completion criterion.

### Exact replay scales across bilingual prompts

We next evaluated the seeded policy on 20 prompts covering explanation, comparison, planning, summarization-style responses and structured lists in English and Chinese. Three public seeds were used for each prompt, giving 60 FP16 reference and BF16 replay trajectories. Generation continued for at least 64 tokens and stopped at the first public sentence endpoint, with a maximum of 96 tokens. All configured trials were retained in the analysis.

Certificate-corrected replay recovered 60 of 60 token trajectories, whereas uncorrected replay recovered 10 of 60 (Table 1). All 20 prompt clusters achieved three of three corrected replays; the Wilson 95% interval across the 20 prompt clusters was 0.839-1.000. This interval describes the finite prompt set and does not establish performance on a wider prompt population. The mean correction rate was 2.16% (prompt-cluster bootstrap 95% confidence interval, 1.80-2.53%), with a maximum trial rate of 6.15%. The mean correction-record size was 2.88% of a full token trace (95% confidence interval, 2.40-3.36%). Thus, exact reconstruction required storing a small target-specific delta rather than the complete output sequence.

The result was consistent across the two language strata. English prompts reached 30 of 30 corrected replays with a mean correction rate of 1.94% (95% confidence interval, 1.47-2.42%); Chinese prompts reached 30 of 30 with a mean rate of 2.39% (1.86-2.86%). These intervals overlap and were not used for a language-difference claim. The mean trajectory length was 75.0 tokens (cluster interval, 72.3-78.1). Without corrections, the common exact prefix averaged 39.45 tokens, illustrating how a small number of local disagreements can produce full-sequence failure.

Every reference token appeared in the target top-eight envelope across 4,500 generated positions. The top-four envelope missed one position, and the largest observed target rank of a reference token was six. This observation supports the use of a bounded validation envelope for the tested configuration, but it is not a guarantee for other models or prompts.

**Table 1 | Cross-precision replay results for Qwen2.5-1.5B-Instruct.** Continuous intervals use 10,000 prompt-cluster bootstrap resamples. Exact recovery counts retain all trials.

| Setting | Trials | Corrected exact | Uncorrected exact | Mean correction rate | Mean record/full-trace ratio | Sentence complete |
|---|---:|---:|---:|---:|---:|---:|
| FP16 to BF16, top-2, main scale | 60 | 60/60 | 10/60 | 2.16% [1.80, 2.53] | 2.88% [2.40, 3.36] | 58/60 |
| FP16 to BF16, top-2, ablation subset | 20 | 20/20 | 5/20 | 2.05% [1.24, 2.93] | 2.74% [1.69, 3.90] | 20/20 |
| FP16 to BF16, top-4 | 20 | 20/20 | 1/20 | 2.41% [1.94, 2.87] | 3.21% [2.58, 3.82] | 16/20 |
| BF16 to FP16, top-2 | 20 | 20/20 | 5/20 | 2.06% [1.33, 2.86] | 2.75% [1.76, 3.82] | 19/20 |

### A public sentence rule improves structural completion

Fixed token budgets can produce exact but visibly truncated outputs. We therefore separated token replay from structural completion. In the sentence-completion pilot, generation continued beyond token 64 until a public terminal-punctuation rule was satisfied or token 96 was reached. For six seeded trajectories, sentence completion improved from zero of six under the fixed 64-token setting to six of six under the public stopping rule, at an average cost of 9.5 additional tokens. Exact corrected replay remained six of six and the mean correction rate was 1.62%.

At scale, 58 of 60 reference trajectories satisfied the structural endpoint. Failures remained in the denominator and were not removed from replay analysis. This endpoint establishes only that the generated text ended at recognized sentence punctuation. It does not measure factuality, coherence or human preference. Blinded semantic evaluation remains required before making a text-quality claim.

### Contract width exposes a distribution-reliability Pareto frontier

Restricting the contract to the two highest-probability candidates can make decisions stable but conditions generation on a smaller fraction of the model distribution. To quantify this trade-off, we compared top-two and top-four contracts on the same 20 prompts and public seed. Because contract width participates in token selection, the two settings intentionally generated different reference trajectories; the comparison is paired by prompt and seed, not by token sequence.

Expanding the contract from two to four candidates increased retained source mass from 0.734 to 0.845, a paired increase of 0.110 (95% confidence interval, 0.090-0.131). The measured truncation component decreased from 0.382 to 0.198 nats per token, a change of -0.184 (-0.220 to -0.150). The full-logit quantization term remained much smaller: 0.00257 nats per token for top-two and 0.00247 for top-four in these runs. These components are reported separately; their numerical sum is not asserted to equal total divergence after integer apportionment.

The distributional improvement did not produce a reliability improvement. Correction density changed by +0.35 percentage points (-0.65 to +1.34), so the interval included no change. Shared-contract exactness fell by 25.14 percentage points (-27.70 to -22.72). Sentence completion decreased from 20 of 20 to 16 of 20, a paired change of -20 percentage points (-40 to -5). Because completion is an automated structural endpoint and this ablation used one seed, the decrease is treated as a bounded signal rather than a general semantic-quality result. We therefore retain top-two as the default reproducibility operating point and top-four as a lower-truncation alternative on the Pareto frontier.

### Replay is stable in both FP16/BF16 directions within the tested environment

To test whether the result depended on selecting FP16 as the reference, we reversed the direction for the 20-prompt ablation. BF16 references replayed in FP16 achieved 20 of 20 corrected trajectories, with a correction rate of 2.06% (1.33-2.86%) and 19 of 20 sentence-complete outputs. Relative to the matched FP16-to-BF16 top-two subset, the correction-rate change was +0.01 percentage points (-1.00 to +1.00), and the retained-mass change was -0.0043 (-0.0193 to +0.0104). Neither interval excluded zero.

These data support bidirectional precision replay on the tested model and GPU stack. They do not show equivalence of FP16 and BF16 distributions: only five of 20 reference trajectories were identical across the two reference precisions, and the quantization total-variation term was slightly larger in the reverse experiment. The certificate recovers a selected reference path despite distributional differences; it does not remove those differences.

## Discussion

Our results show that cross-precision stochastic language generation can be reconstructed exactly with a compact, auditable correction record when the reference and target environments are known. The decisive observation is not that a complete correction manifest guarantees replay; that follows directly from the construction. The empirical advance is that disagreements remained sparse across 4,500 Qwen token positions, 20 bilingual prompts and three public seeds, even though uncorrected full-sequence agreement was low. This converts autoregressive divergence from an all-or-nothing outcome into a measurable per-step record.

SPRCs complement approaches that suppress or detect nondeterminism. Higher-precision computation aims to prevent numerical divergence [1], whereas SPRCs permit a specified target environment to differ and record only the decisions needed to reconstruct a selected path. Token-level verification methods determine whether outputs are consistent with a trusted reference [2]; the present method instead emits enough information to recover a particular trajectory. Shared-random sampling methods such as SparSamp and range coding motivate deterministic probability partitions [3,4], while finite-precision detection results show why implementation-level probability contracts cannot be treated as ideal real arithmetic [5]. Our experiments operationalize this distinction by reporting full-logit quantization, support truncation, contract agreement and correction density separately.

The top-*k* ablation identifies a practical design rule. A wider support retains more probability mass and lowers the truncation component, but creates more opportunities for cross-precision candidate and integer-boundary disagreement. In the present sample, top-four therefore improves one distributional objective while worsening contract agreement and structural completion. This is a Pareto trade-off rather than a uniformly superior configuration. Related work on list decoding, dyadic approximation and tokenization synchronization addresses capacity or text-channel synchronization under different objectives [7-9]. Those mechanisms are relevant extensions, but they are not required for the target-specific replay claim tested here.

Several limitations define the current result. First, certificates are target-specific: construction evaluates the target precision on the reference prefix, so a certificate for BF16 is not guaranteed to work for a different accelerator, kernel, model revision or tokenizer. Second, all Qwen experiments used one RTX 3060 Laptop GPU and one software stack. Independent hardware replication is therefore required for a cross-system claim. Third, the top-two contract retains approximately three quarters of the quantized source mass on average and incurs a substantial truncation component. Exact replay must not be interpreted as distribution preservation. Integer apportionment adds a further finite-mass approximation that was not isolated as a separate divergence term in the main artifacts. Fourth, public sentence completion is not a semantic or factual-quality measure. Fifth, this study reconstructs token identifiers under a shared tokenizer and does not test recovery after public-text re-tokenization, normalization or rewriting.

Within these boundaries, sparse certificates provide a practical research instrument. They preserve the stochastic reference trajectory without forcing all inference into FP32 and expose where precision changes an actual token decision. The next decisive tests are independent replication on another GPU/CUDA stack and a blinded comparison of native, top-two and top-four outputs. These tests should precede claims of hardware generality or semantic equivalence.

## Methods

### Models and software environment

Experiments used a local Qwen2.5-1.5B-Instruct checkpoint [6] and, for the initial pilot, a local GPT-2 checkpoint. Qwen inference ran on an NVIDIA GeForce RTX 3060 Laptop GPU with 6 GB memory. The recorded environment used Python 3.11.15, PyTorch 2.7.1 with CUDA 12.6 and Transformers 4.57.6. Model weights, tokenizers and experiment outputs were loaded locally. EOS and padding tokens were excluded from sampling so that the public sentence rule, rather than model EOS, determined the evaluated stopping point.

### Prompt and trajectory design

The main Qwen experiment contained 20 fixed prompts: ten English and ten Chinese prompts. They covered explanations, comparisons, practical plans and structured responses in general educational and software topics. Each prompt was evaluated with public seeds 0, 1 and 2 under the seeded policy, producing 60 trajectories. Seeds are repeated stochastic trajectories within a prompt and were not treated as independent prompt samples for continuous-metric intervals.

Reference generation used FP16 and target replay used BF16 in the main experiment. Generation continued for at least 64 tokens and stopped at the first output satisfying the public sentence-completion predicate, with a hard maximum of 96 tokens. R046 reversed the reference and replay precision on all 20 prompts with seed 0. The top-*k* ablation compared contract widths two and four on the same prompts and seed. No completed trial was excluded.

### Quantized next-token snapshot

At generation step \(t\), the model produced logits \(\ell_{t,i}\). After blocking EOS-like tokens, logits were shifted by their finite maximum and quantized to a public grid of width \(q=0.5\):

\[
b_{t,i}=\left\lfloor\frac{\ell_{t,i}-\max_j\ell_{t,j}}{q}+\frac{1}{2}\right\rfloor.
\]

The quantized logits \(q b_{t,i}\) were divided by temperature \(T=1.2\) and normalized. Candidates were ranked with stable token-identifier tie breaking. A top-16 envelope was retained for validation. The contract then used the highest-ranked \(k\in\{2,4\}\) candidates and ordered them by integer token identifier before mass allocation. Candidate rank always refers to probability rank before canonical reordering.

We measured the Kullback-Leibler divergence from the unquantized temperature-scaled distribution to the full quantized-logit distribution and their total variation. These are logit-quantization terms. Let \(A_t\) denote retained contract support and \(Z_t\) its probability mass under the quantized full distribution. Before integer apportionment, conditioning on \(A_t\) gives

\[
D_{\mathrm{KL}}(Q_t\,\|\,\widetilde P_t)=-\log Z_t.
\]

This is the reverse-KL truncation component. It is not \(D_{\mathrm{KL}}(\widetilde P_t\,\|\,Q_t)\), which is infinite when positive source support is removed. We do not claim that the truncation and full-logit quantization numbers sum to total divergence after integer apportionment.

### Integer probability contract

For contract token identifiers \(v_1,\ldots,v_k\) and quantized bins \(b_1,\ldots,b_k\), Decimal arithmetic at precision 80 computed weights

\[
w_i=\exp\left(\frac{q(b_i-\max_j b_j)}{T}\right).
\]

The contract used a total integer mass \(M=2^{16}\). One count was reserved for each retained token. The remaining \(M-k\) counts were assigned proportionally to \(w_i\) by deterministic largest-remainder apportionment. Remainder ties were resolved by token identifier. The resulting counts are non-negative, preserve retained support and sum exactly to \(M\).

For public seeded sampling, a key was derived by hashing the public seed. HMAC-SHA256 over the model name, prompt, contract parameters, seed and step produced a rational sample that was mapped to one of the integer cumulative intervals. Greedy controls selected the largest count with token identifier as a tie breaker. The public-seed construction supports reproducible experiments; it is not a cryptographic secrecy claim.

### Sparse precision replay certificate

Let \(x_{1:n}\) be the reference token trajectory and let \(g_t(x_{<t})\) be the token selected by the target-precision contract at step \(t\) when conditioned on the reference prefix. The manifest is

\[
C=\{(t,x_t):g_t(x_{<t})\neq x_t\}.
\]

During replay, the target environment computes its local contract token on the reconstructed prefix and applies

\[
y_t=\begin{cases}
x_t, & (t,x_t)\in C,\\
g_t(y_{<t}), & \text{otherwise}.
\end{cases}
\]

If the model, tokenizer, prompt, configuration, public seed and target numerical environment match certificate construction, induction on \(t\) yields \(y_{1:n}=x_{1:n}\). This is a conditional safety property, not a termination or target-independence theorem.

The sparse record stored the step and token identifier for each correction. Record size excluded a shared configuration header. With vocabulary size \(V\), token identifiers used \(\lceil\log_2(V)/8\rceil\) bytes and step identifiers used \(\lceil\log_2(n)/8\rceil\) bytes. The full-trace comparator stored every token identifier. Reported record ratios are sparse payload bytes divided by full-trace token bytes.

### Outcome measures

The primary outcome was exact equality of corrected and reference token sequences. Secondary outcomes were uncorrected exact replay, correction count divided by token count, common exact prefix without corrections, sparse/full record-size ratio, structural sentence completion, retained source mass, truncation component, full-logit quantization KL and total variation, shared-contract exactness, and reference-token coverage within target top-four, top-eight and top-16 envelopes.

Sentence completion was evaluated by a public punctuation-based predicate. It was applied only after token 64 and did not inspect the seed or correction manifest. This measure was used as a structural endpoint, not as a human-quality score.

### Statistical analysis

The main continuous-metric analysis treated prompts as clusters and retained the three seed trajectories within each sampled prompt. Each trajectory contributed equally to the reported mean; longer trajectories were not given greater weight. Means and two-sided 95% percentile intervals were calculated from 10,000 prompt-cluster bootstrap resamples using public bootstrap seed 20260720. English and Chinese strata each contained ten prompt clusters. For the top-*k* and precision-direction comparisons, conditions were paired by prompt and public seed; bootstrap resampling preserved the paired prompt structure. Because top-*k* affects reference sampling, those comparisons were not paired token by token.

Exact counts are reported without null-hypothesis significance tests. For the main exact-replay result, all three trajectories succeeded in each of 20 prompt clusters; a Wilson interval over prompt-level success was included as a conservative descriptive interval. No multiplicity-adjusted *P* values were calculated because the study reports prespecified effect estimates and uncertainty intervals rather than a family of significance claims. Trials were saved atomically and all configured trials were included. Analysis code and deterministic result signatures are provided with the repository.

## Data availability

The fixed bilingual prompt set, aggregate analysis files, source hashes and deterministic result signatures are included in the project repository. Raw model outputs are excluded from version control and remain available as local experiment artifacts. AUTHOR_INPUT_NEEDED: provide the public archival location and accession/DOI before submission.

## Code availability

Code for probability contracts, replay certificates, checkpointed experiments and statistical analysis is available at `https://github.com/kdssss501/sparsamp-semantic` on the tagged research version `research-v0.33-qwen-replay-ablation-go`. AUTHOR_INPUT_NEEDED: create an immutable archival release and DOI before submission.

## Acknowledgements

AUTHOR_INPUT_NEEDED.

## Author contributions

AUTHOR_INPUT_NEEDED. Use CRediT roles and distinguish conceptualization, software, validation, formal analysis, investigation, visualization, writing and supervision.

## Competing interests

The authors declare AUTHOR_INPUT_NEEDED.

## References

1. Yuan, J. *et al.* Understanding and mitigating numerical sources of nondeterminism in LLM inference. *arXiv* 2506.09501 (2025).
2. Karvonen, A. *et al.* DiFR: inference verification despite nondeterminism. *arXiv* 2511.20621 (2025).
3. Wang, Y. *et al.* SparSamp: efficient provably secure steganography based on sparse sampling. In *34th USENIX Security Symposium* 6817-6835 (USENIX Association, 2025).
4. Yan, R. & Murawaki, Y. Efficient provably secure linguistic steganography via range coding. In *Proceedings of the 64th Annual Meeting of the Association for Computational Linguistics* 890-907 (Association for Computational Linguistics, 2026). https://doi.org/10.18653/v1/2026.acl-long.39.
5. Cao, W., Wang, Y. & Hu, D. Breaking the "provable security": detecting finite-precision artifacts in LLM-based steganography via low-probability vanishing. In *Findings of the Association for Computational Linguistics: ACL 2026* 20262-20274 (Association for Computational Linguistics, 2026). https://doi.org/10.18653/v1/2026.findings-acl.1013.
6. Qwen Team. Qwen2.5 technical report. *arXiv* 2412.15115 (2024).
7. Pang, K. & Bai, M. Provably secure steganography based on list decoding. *arXiv* 2604.21394 (2026).
8. Bar-Lev, D., Farnoud, F. & Gabrys, R. An additive approximation scheme for generating dyadic codings for the outputs of an LLM. *arXiv* 2605.05837 (2026).
9. Wang, Y. *et al.* ReTokSync: self-synchronizing tokenization disambiguation for generative linguistic steganography. *arXiv* 2604.25486 (2026).

## Figure legends

**Figure 1 | Sparse precision replay certificate workflow.** A reference-precision run generates a stochastic token trajectory from a public integer contract. The target precision evaluates the same contract on each reference prefix. Only target choices that differ from the reference token are stored. A fresh target run applies these corrections before extending its prefix, preventing autoregressive error propagation. The figure must distinguish the top-16 validation envelope from the top-two or top-four contract support.

**Figure 2 | Exact replay and sparse correction density across bilingual prompts.** a, Corrected and uncorrected exact-replay counts for 60 FP16-to-BF16 trajectories. b, Prompt-level correction rates for ten English and ten Chinese prompts, with three seed trajectories retained within each cluster. c, Sparse/full record-size ratios. Points represent trajectories; interval summaries use prompt-cluster bootstrap resampling.

**Figure 3 | Distribution-reliability trade-off with contract width.** Retained source mass, truncation component, contract exactness, correction rate and sentence completion for top-two and top-four contracts on 20 matched prompts. Lines join prompt-matched conditions, not identical token trajectories. The panel must report the full-logit quantization term separately from truncation.

**Figure 4 | Precision-direction stress test.** Comparison of FP16-to-BF16 and BF16-to-FP16 top-two contracts on 20 matched prompts. Panels show corrected recovery, correction density, retained mass and structural sentence completion. Confidence intervals use paired prompt-cluster bootstrap resampling.
