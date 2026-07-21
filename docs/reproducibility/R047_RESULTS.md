# R047 External Replay Package

## Material Passport

- Origin Skill: academic-research-suite `experiment-agent`
- Origin Mode: validate
- Verification Status: VERIFIED_ON_SOURCE_MACHINE
- Reference bundle: `outputs/R047_reference_seed0.json`
- Target report: `outputs/R047_local_target.json`
- Bundle SHA-256: `3db563f6e569828689e82b06184d439cdb12cfe78d9b5bdd4b5ec3d2601ff76c`
- Bundle signature: `77b1f1bd8816ff26447b8070b64c1bf9dd87bca5ddc46106463ae84fcacca24d`
- Model signature: `bf744428965a3fe7a8431e6611525474af89555c4f5d8484ad003ff936378e87`

## Scope

R047 separates reference construction from target replay. The exported bundle contains the
reference token trajectories, public contract configuration, full model-directory fingerprint
and per-trial identities for the 20 seed-0 prompts. A target machine validates the model
fingerprint before constructing a fresh target-specific correction manifest and replaying it.

The bundle does not contain a precomputed target manifest. This prevents the target-side result
from being obtained by merely copying the source-machine replay output.

## Source-Machine Smoke Result

| Metric | Result |
|---|---:|
| Trials | 20 |
| Generated tokens | 1,500 |
| Corrected exact replay | 20/20 |
| Uncorrected exact replay | 5/20 |
| Corrections | 30 |
| Mean trial correction rate | 2.0543% |
| Manifest construction time | 130.06 s |
| Corrected replay time | 130.47 s |
| Uncorrected evaluation time | 126.06 s |

The result agrees with the seed-0 subset of R044. It is a packaging and fresh-replay smoke test
on the same RTX 3060 Laptop GPU and software installation. It is not independent hardware
evidence.

## Reproducibility Contract

An external result is comparable only if all of the following hold:

1. The reference bundle SHA-256 and internal bundle signature match the values above.
2. The complete local model-directory signature matches the bundle model signature.
3. The output is produced by `scripts/replay_external_bundle.py` without importing an existing
   target report.
4. Every trial has `replay_completed=true` and `corrected_exact=true`.
5. Hardware, PyTorch, CUDA, Transformers and platform metadata remain in the target report.

Different target environment signatures are expected and are the point of the external test.
Exact uncorrected replay and correction density are empirical outcomes, not acceptance gates.

## Interpretation Boundary

- Exact corrected replay is conditional on a complete target-specific manifest.
- A successful external run would support portability of the construction procedure, not a
  target-independent certificate.
- The current source-machine smoke cannot support cross-GPU or cross-software generality.
- Timing is descriptive and must not be compared across machines without reporting hardware and
  software metadata.
