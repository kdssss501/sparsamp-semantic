# R044 Scale Analysis

## Material Passport

- Origin Skill: ARIS `analyze-results`
- Analysis unit: prompt cluster with three public seeds
- Bootstrap: 10,000 prompt-cluster resamples, seed 20260720
- Verification status: ANALYZED
- Source: `outputs/R044_qwen_replay_scale.json`
- Source SHA-256: `6a6eaa292e8ac490b38932969879323cc44088361ceabd20b51466a836fc3110`
- Deterministic result signature: `c9ca57129a664a4114d7c186527c176c5e898596c1549e62724d88679a30c62d`

## Main Results

| Group | Trials | Corrected exact | Uncorrected exact | Sentence complete | Mean correction rate (cluster 95% CI) |
|---|---:|---:|---:|---:|---:|
| overall | 60 | 60/60 | 10/60 | 58/60 | 0.0216 [0.0180, 0.0253] |
| english | 30 | 30/30 | 6/30 | 29/30 | 0.0194 [0.0147, 0.0242] |
| chinese | 30 | 30/30 | 4/30 | 29/30 | 0.0239 [0.0186, 0.0286] |

## Prompt-Level Raw Table

| Prompt | Lang | Seeds | Corrected | Uncorrected | Complete | Mean correction | Max correction | Mean tokens | Max rank |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | en | 3 | 3 | 1 | 3 | 0.0229 | 0.0556 | 74.00 | 2 |
| 1 | en | 3 | 3 | 1 | 3 | 0.0135 | 0.0253 | 74.00 | 2 |
| 2 | en | 3 | 3 | 0 | 3 | 0.0176 | 0.0270 | 76.67 | 2 |
| 3 | en | 3 | 3 | 1 | 3 | 0.0167 | 0.0361 | 80.00 | 2 |
| 4 | en | 3 | 3 | 1 | 3 | 0.0093 | 0.0143 | 70.00 | 2 |
| 5 | en | 3 | 3 | 0 | 3 | 0.0347 | 0.0455 | 67.00 | 3 |
| 6 | en | 3 | 3 | 1 | 2 | 0.0267 | 0.0488 | 87.33 | 1 |
| 7 | en | 3 | 3 | 0 | 3 | 0.0211 | 0.0380 | 80.00 | 2 |
| 8 | en | 3 | 3 | 0 | 3 | 0.0226 | 0.0385 | 71.67 | 2 |
| 9 | en | 3 | 3 | 1 | 3 | 0.0085 | 0.0135 | 77.33 | 2 |
| 10 | zh | 3 | 3 | 0 | 3 | 0.0324 | 0.0435 | 71.67 | 2 |
| 11 | zh | 3 | 3 | 1 | 3 | 0.0147 | 0.0312 | 70.33 | 2 |
| 12 | zh | 3 | 3 | 0 | 3 | 0.0175 | 0.0230 | 74.33 | 3 |
| 13 | zh | 3 | 3 | 1 | 3 | 0.0244 | 0.0462 | 73.67 | 1 |
| 14 | zh | 3 | 3 | 0 | 3 | 0.0294 | 0.0349 | 79.33 | 2 |
| 15 | zh | 3 | 3 | 0 | 3 | 0.0361 | 0.0615 | 64.67 | 2 |
| 16 | zh | 3 | 3 | 0 | 3 | 0.0263 | 0.0500 | 72.67 | 6 |
| 17 | zh | 3 | 3 | 1 | 3 | 0.0260 | 0.0513 | 74.67 | 2 |
| 18 | zh | 3 | 3 | 0 | 3 | 0.0247 | 0.0299 | 67.33 | 2 |
| 19 | zh | 3 | 3 | 1 | 2 | 0.0071 | 0.0109 | 93.33 | 1 |

## Key Findings

1. Corrected replay recovered 60/60 trajectories; the Wilson 95% interval is [0.9398, 1.0000].
2. Mean correction rate was 0.0216, with prompt-cluster bootstrap 95% CI [0.0180, 0.0253].
3. Without corrections, only 10/60 trajectories matched exactly.
4. Sentence completion was 58/60; failed completions remain in the primary denominator.
5. Top-4 missed one reference token, while top-8 covered every reference token in the scale run.

## Boundaries

- Seeds within a prompt are not treated as independent prompt samples; continuous-metric intervals resample prompts as clusters.
- Wilson intervals describe the 60 observed trajectories and do not establish cross-model or cross-hardware generality.
- Text completion is a structural endpoint check, not a blinded human-quality evaluation.
