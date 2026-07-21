# R048 Blinded Quality-Study Materials

## Material Passport

- Origin Skill: academic-research-suite `experiment-agent`
- Origin Mode: manage
- Verification Status: MATERIALS_VERIFIED
- Ethics Status: `ETHICS_PENDING`
- Native source: `outputs/R048_native_top16_seed0.json`
- Participant package: `outputs/R048_participant_package.json`
- Private mapping: `outputs/R048_blinding_key.private.json`

## Generated Materials

The checkpointed native baseline generated one FP16 top-16 response for each of the 20 frozen
R044 prompts using public seed 0, temperature 1.2, a minimum of 64 tokens and a maximum of 96
tokens. All 20 trials completed and all 20 reached the public structural sentence endpoint. Mean
length was 78.3 tokens. Total recorded generation time was 123.34 seconds on the source machine.

The preparation script matched these responses by prompt and seed against the R044 top-two and
R045 top-four reference outputs. Each prompt received an independently HMAC-derived permutation
of labels A, B and C. The participant package contains no method names, secret key or reveal map.

| Item | Value |
|---|---:|
| Matched prompts | 20 |
| Conditions per prompt | 3 |
| Native structural completion | 20/20 |
| Participant package signature | `158eb1f8517d30febb6e75586ae564e3ee02c97ee31b228d44768fffdb8cd4ba` |
| Ethics status | `ETHICS_PENDING` |

## Blinding And Data Boundary

- The 256-bit blinding key and A/B/C method mapping are stored only under `outputs/`, which is
  excluded from Git.
- Re-running without `--fresh-key` reuses the existing private key and produces the same mapping.
- The offline evaluator disables rating controls and export unless a reviewed participant package
  explicitly carries `ethics_status="READY"`.
- The current generator emits only `ETHICS_PENDING`; changing study status requires a separate
  ethics and protocol review, not a command-line convenience flag.

## Scientific Boundary

R048 is not a human-evaluation result. It establishes matched materials, deterministic blinding,
source separation and an offline data-minimizing interface. No participant was recruited and no
rating was collected. Native top-16 structural completion cannot be interpreted as semantic
equivalence or preference.
