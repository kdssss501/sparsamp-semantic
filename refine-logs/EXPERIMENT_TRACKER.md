# Experiment Tracker

| Run ID | Milestone | Purpose | System / Variant | Data | Metrics | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| R001 | M0 | Official basic reproduction | Artifact GPT-2 | Paper prompts | decode, bit/token | MUST | TODO | Block all claims if failed |
| R002 | M0 | E1-E3 subset | Artifact vs local core | Paper configs | capacity, ATST, SITR | MUST | TODO | Fixed revisions |
| R003 | M1 | Completion survival baseline | Fixed block 2/4/8/16/32 | 20 prompts x 3 seeds | success, p95 tokens | MUST | TODO | Cache prompt list |
| R004 | M1 | Runtime profile | Qwen local provider | 10 prompts | forward/sort/transfer time | MUST | TODO | Guides optimization |
| R005 | M2 | Adaptive schedule pilot | FH-SparSamp | 20 prompts x 3 seeds | success, bit/token | MUST | TODO | Go if +10 points |
| R006 | M2 | Controller ablation | entropy/budget/full | Same as R005 | success, overhead | MUST | TODO | Isolate mechanism |
| R007 | M3 | Precision replay | FP16/BF16/FP32 | 10 prompts | exact decode, support loss | MUST | TODO | Hardware permitting |
| R008 | M3 | Precision detector | mass variants | Native/stego samples | detector AUC | MUST | TODO | Reproduce published signal |
| R009 | M4 | Semantic finishing tail | stop/punctuation/EOS | 50 covers | preference, completeness | NICE | TODO | Supporting component |
| R010 | API | Repeated-query drift probe | DeepSeek top-20 | 20 prompts | churn, drift, mass, cost | NICE | BLOCKED | Needs API key |
