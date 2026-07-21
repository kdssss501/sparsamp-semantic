# R002 Official SparSamp Matrix Reproduction

## Scope

This is a compatibility reproduction of the published GPT-2 protocol using the unchanged
Zenodo 15025436 algorithm code with a modern CUDA-enabled PyTorch stack and Transformers
4.41.2. It is not a strict recreation of the artifact's Torch 2.2.2 environment.

## Results

| block | top-p | complete | budget exhausted | TA | eligible | decode | bits/token | utilization (95% CI) | paper utilization | relative error |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 1.00 | 100 | 0 | 26 | 74 | 74/74 | 1.638 | 0.272 [0.269, 0.276] | 0.275 | 0.93% |
| 4 | 1.00 | 100 | 0 | 29 | 71 | 71/71 | 2.647 | 0.443 [0.437, 0.449] | 0.447 | 0.93% |
| 8 | 1.00 | 100 | 0 | 27 | 73 | 73/73 | 3.794 | 0.625 [0.617, 0.633] | 0.645 | 3.15% |
| 16 | 1.00 | 100 | 0 | 26 | 74 | 74/74 | 4.809 | 0.793 [0.783, 0.804] | 0.788 | 0.68% |
| 32 | 1.00 | 100 | 0 | 28 | 72 | 72/72 | 5.178 | 0.872 [0.861, 0.882] | 0.873 | 0.14% |
| 64 | 0.80 | 100 | 0 | 4 | 96 | 96/96 | 3.672 | 0.963 [0.953, 0.973] | 0.953 | 1.03% |
| 64 | 0.95 | 100 | 0 | 19 | 81 | 81/81 | 5.032 | 0.953 [0.941, 0.965] | 0.949 | 0.40% |
| 64 | 1.00 | 100 | 0 | 30 | 70 | 70/70 | 5.734 | 0.943 [0.930, 0.957] | 0.974 | 3.16% |
| 128 | 1.00 | 100 | 0 | 30 | 70 | 70/70 | 5.942 | 0.986 [0.973, 0.998] | 0.980 | 0.59% |
| 256 | 1.00 | 100 | 0 | 39 | 61 | 61/61 | 5.866 | 0.973 [0.959, 0.987] | 0.985 | 1.25% |
| 512 | 1.00 | 97 | 3 | 42 | 55 | 55/55 | 6.181 | 0.989 [0.976, 1.003] | 0.987 | 0.24% |
| 1023 | 1.00 | 96 | 4 | 47 | 49 | 49/49 | 6.130 | 1.000 [0.987, 1.013] | 0.995 | 0.48% |

## Acceptance

- Decode gate: **PASS**, 846/846 eligible trials.
- Capacity gate: **PASS**, 16/16 comparisons within 5% relative error.
- Budget completion: 1193/1200 completed; 7 trials did not finish a message block within the 200-token ceiling.
- Overall: **PASS_WITH_LIMITATIONS**.

## Interpretation Boundaries

- Token Ambiguity is reported separately and excluded from the paper's no-TA decoding denominator.
- Bootstrap intervals resample IMDB contexts within each configuration.
- Sampling and throughput values are descriptive because the reproduction GPU differs from the paper.
- The unchanged algorithm source was used, but the compatibility environment does not establish strict
  byte-for-byte reproducibility under the artifact's original dependency versions.
