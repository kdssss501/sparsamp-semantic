# Response to Reviewers - Revision Round 1

## Manuscript

**Revised title:** Target-specific sparse correction certificates recover stochastic language trajectories across numerical precision

We thank the panel for distinguishing internal correctness from external validity. We accepted the central criticism that complete-manifest recovery is an integrity invariant rather than the empirical performance endpoint. The revised manuscript foregrounds correction density, matched package bytes, target passes and distributional cost. No independent-hardware or semantic-quality result has been invented.

## Required Revisions

### R1: Independent physical-target replay

**Response:** Agreed. The current target report was generated on the source RTX 3060 Laptop GPU and cannot satisfy this request. The revised title, Abstract and Discussion now consistently say target-specific and one-stack. The frozen bundle and instructions remain ready for an external run.

**Status:** `EXTERNAL_BLOCK`.

**Acceptance evidence still required:** A second physical GPU/software stack must consume the unchanged bundle, verify its SHA-256 and model identity, and publish all trial outcomes.

### R2: Matched replay baselines

**Response:** Accepted. R051 adds seed-only, full trace and fixed block-repair baselines under the same 101-byte referenced header and per-trial identity records. R052 then evaluates the same HMAC fraction and frozen reference prefixes after removing logit bins and integer mass. At top-two, correction density increased by 1.123 percentage points (paired prompt 95% interval, 0.171-2.015) and the referenced package increased from 1,148 to 1,200 bytes. The positive-support top-16 cap reached 25.454% correction density and 2,371 bytes. One BF16 step retained only five positive-probability candidates; this is reported rather than silently dropping the trial.

**Status:** `RESOLVED`.

**Locations:** Results, “Matched replay baselines isolate sparse-record cost”; Table 2; `docs/reproducibility/R051_REPLAY_BASELINES.md`; `docs/reproducibility/R052_UNQUANTIZED_DELTA_ANALYSIS.md`.

### R3: Reframe the empirical primary endpoint

**Response:** Accepted. The Abstract now says exact corrected replay is a protocol invariant. The Introduction declares correction density as the primary empirical endpoint, with exact replay as an integrity gate. The Discussion no longer presents 60/60 as an accuracy advance.

**Status:** `RESOLVED`.

### R4: Complete the integer probability audit

**Response:** Accepted. For (k) support-preserved candidates and integer mass (M), the revised Methods derives (TV(p,r)<2(k-1)/M). For (k=2,M=2^{16}), the bound is (1/32768=3.0518\times10^{-5}) per step. R050 validates the applicable contract shape over 1,500 saved steps. The revision explicitly states that no finite distribution-free KL bound follows without a lower probability bound and does not add KL components with incompatible directions.

**Status:** `RESOLVED`.

**Locations:** Methods, “Integer probability contract”; `docs/reproducibility/R050_INTEGER_APPORTIONMENT.md`.

### R5: Prespecified parameter sensitivity

**Response:** Partially accepted. The existing top-2/top-4 ablation is retained and the paper no longer claims optimality. A new (q,T,B,k) grid requires GPU execution and remains pending.

**Status:** `PARTIAL`.

### R6: Trust, state and cost model

**Response:** Accepted. Methods now identifies constructor, recipient and auditor actions; separates per-study, per-trial-set and per-trajectory state; states that construction requires access to the intended target; and notes correction-token privacy exposure. Table 2 reports target passes beside bytes.

**Status:** `RESOLVED`.

### R7: Venue positioning

**Response:** Accepted. With no second model or independent hardware, the revision selects a specialist ML-systems/reproducibility framing. The title adds “Target-specific,” and the draft no longer identifies Nature Communications as its intended format.

**Status:** `RESOLVED`.

### R8: Immutable artifacts and declarations

**Response:** Agreed but requires author action. The revision names the new R050/R051 artifacts and retains all author/DOI placeholders rather than guessing metadata.

**Status:** `EXTERNAL_BLOCK`.

## Suggested Revisions

- **Mechanism taxonomy:** Accepted. Supplementary Note 2 separates full trace, seed-only, SPRC, block repair, SparSamp, range coding, list decoding, dyadic approximation and ReTokSync by objective and state.
- **Pseudocode:** Partially accepted. Methods now includes an explicit five-step construction/replay procedure.
- **Internal experiment labels:** Partially accepted. Reader-facing prose removes R047/R048 labels; provenance-oriented locations retain stable artifact identifiers.
- **Semantic quality:** Addressed by limitation. No human-quality or semantic-equivalence conclusion is made.
- **Licensing:** Pending author selection and archive policy.

## Residual Risks

The revision remains unsuitable for a cross-hardware or broad multidisciplinary claim until an external target run is complete. The matched unquantized experiment supports a small contract advantage on this frozen stack, but does not establish globally optimal (q,T,B,k) settings. These boundaries are presented as unresolved limitations, not hidden in package accounting.
