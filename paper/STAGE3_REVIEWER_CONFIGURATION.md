# Stage 3 Reviewer Configuration

## Paper basic information

- Title: Sparse correction certificates recover stochastic language generation across numerical precision
- Abstract length: 225 words
- Full manuscript length: approximately 5,564 words
- References: 9
- Review input: manuscript v0.2, Supplementary Information, Stage 2.5 integrity report and Material Passport
- Review mode: full, read-only, balanced spectrum

## Field analysis

| Dimension | Classification |
|---|---|
| Primary discipline | Machine-learning systems and reproducible stochastic inference |
| Secondary disciplines | Numerical computing; generative-model sampling; research software and artifact reproducibility |
| Research paradigm | Constructive computational method with controlled empirical validation |
| Methodology type | Systems experiment, paired ablation, artifact compatibility reproduction and conditional proof |
| Current target tier | Strong specialized Q1/Q2 methods venue; Nature Communications remains aspirational rather than demonstrated fit |
| Paper maturity | Pre-submission draft requiring external-validity and positioning revisions |

The current claim is methodologically bounded and internally well audited. The principal
editorial risk is not fabrication or internal inconsistency; it is whether one Qwen
checkpoint and one GPU stack provide enough evidence for the significance expected by a
broad, high-selectivity venue.

## Recommended venue calibration

1. Transactions on Machine Learning Research - strongest current fit for a transparent methods and reproducibility contribution, provided the novelty comparison is strengthened.
2. Machine Learning: Science and Technology - suitable for a computational reproducibility method with open artifacts and bounded systems evidence.
3. Journal of Machine Learning Research - aspirational field-top option requiring deeper theory, broader systems validation and stronger baselines.

Nature Communications is retained as the manuscript's formatting and ambition reference,
but the EIC will explicitly test whether the evidence clears its broad-significance bar.

## Reviewer Configuration Card 1

**Role:** Editor-in-Chief

**Identity:** A computational-methods editor handling reproducibility, trustworthy AI and
machine-learning systems submissions at a Nature Communications-level multidisciplinary
venue.

**Review focus:**

1. Whether sparse correction certificates are a broadly significant method rather than a narrowly engineered replay format.
2. Whether the main contribution is distinct from delta encoding, deterministic replay logs and existing inference-verification work.
3. Whether the title, abstract and discussion match the evidence scale and intended readership.

**Will particularly care about:** A clear editorial answer to "why this belongs in a broad
venue now" and whether missing independent hardware evidence is fatal or reparable.

**Possible blind spots:** Will not deeply rederive bootstrap calculations or inspect every
finite-precision implementation detail; Reviewer 1 covers those.

## Reviewer Configuration Card 2

**Role:** Peer Reviewer 1 - Methodology

**Identity:** A machine-learning systems methodologist specializing in floating-point
nondeterminism, GPU inference reproducibility, paired computational experiments and
cluster-aware uncertainty estimation.

**Review focus:**

1. Validity of the target-specific replay construction and separation of guaranteed exactness from empirical sparsity.
2. Experimental unit, bootstrap design, one-seed ablations, stopping rules and treatment of all configured trials.
3. Reproducibility of model fingerprints, integer probability contracts, serialization boundaries and runtime measurements.

**Will particularly care about:** Whether the analysis distinguishes equal-trial from
token-weighted estimands and whether any result is tautological, circular or insufficiently
controlled.

**Possible blind spots:** May underweight field novelty and practical communication value;
Reviewers 2 and 3 compensate.

## Reviewer Configuration Card 3

**Role:** Peer Reviewer 2 - Domain

**Identity:** A senior researcher in provably secure generative sampling and linguistic
steganography, familiar with SparSamp, range coding, list decoding, dyadic approximation,
finite-precision attacks and tokenization synchronization.

**Review focus:**

1. Whether the nine-reference literature frame is sufficient to establish the nearest-neighbour gap.
2. Whether the probability-contract contribution is technically distinct from PSS coders, seed channels and general checkpoint/replay mechanisms.
3. Accuracy of distributional language around top-k truncation, quantization, KL and total variation.

**Will particularly care about:** Any hidden migration from a steganography contribution to
a replay contribution without a complete novelty audit against adjacent systems literature.

**Possible blind spots:** May overemphasize steganography lineage and underweight deployment
ergonomics; Reviewer 3 covers operational value.

## Reviewer Configuration Card 4

**Role:** Peer Reviewer 3 - Cross-disciplinary and practical perspective

**Identity:** A research-software and ML auditability specialist who evaluates artifact
portability, provenance packages, model governance and reproducible evaluation workflows.

**Review focus:**

1. Whether certificates solve a real audit workflow compared with seeds, full traces, deterministic kernels or conventional event logs.
2. Operational costs, privacy exposure, target-environment enrollment and lifecycle handling when models or kernels change.
3. Reuse potential beyond the tested Qwen precision pair, without assuming unsupported generalization.

**Will particularly care about:** A credible user and deployment story, explicit threat and
trust boundaries, and whether the referenced-bundle cost is practically meaningful.

**Possible blind spots:** Will not adjudicate PSS theorem lineage or fine statistical choices.

## Reviewer Configuration Card 5

**Role:** Devil's Advocate

**Identity:** An adversarial ML-systems reviewer tasked with constructing the strongest
reject case, especially against methods whose exactness follows by storing correction data.

**Review focus:**

1. Test the claim that the work is more than sparse delta encoding of a known trajectory.
2. Search for circular evaluation, favorable denominator choices, hidden shared-state costs and target-specific overfitting.
3. Ask whether the observed 2.16% correction rate survives different hardware, kernels, models, prompts and decoding configurations.

**Will particularly care about:** The strongest alternative explanation for every headline
result and whether negative results undermine the claimed contribution.

**Possible blind spots:** Intentionally discounts incremental engineering value; the EIC and
synthesizer must distinguish a fatal objection from a scope-limited but useful method.

## Independence contract

- Each reviewer receives the same verified manuscript package.
- Reviewers do not see or cite each other's reports during Phase 1.
- The manuscript remains read-only throughout Stage 3.
- Every criticism must identify the affected section, explain the consequence and propose a concrete remedy.
- The editorial synthesizer may only combine findings that appear in a named reviewer report.

## Phase 0 checkpoint

Reviewer identities are fixed after approval. Later changes require restarting Stage 3 so
the panel is not selected in response to its own findings.
