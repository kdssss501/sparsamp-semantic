# Experiment Tracker

| Run ID | Milestone | Purpose | System / Variant | Data | Metrics | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| R001 | M0 | Official basic reproduction | Artifact GPT-2 | Paper prompts | decode, bit/token | MUST | DONE-COMPAT | 105 tokens, 576 bits, 5.486 bit/token, exact decode; Torch 2.2.2 strict environment still pending |
| R002 | M0 | E1-E3 subset | Artifact vs local core | Paper configs | capacity, ATST, SITR | MUST | TODO | Fixed revisions |
| R003 | M1 | Completion survival baseline | Fixed block 2/4/8/16/32 | 20 prompts x 3 seeds | success, p95 tokens | MUST | PILOT-DONE | Qwen smoke: 3 prompts x 2 seeds x blocks 8/16/32, 18 independent trajectories, 100% token-ID decode; scale and short budgets pending |
| R004 | M1 | Runtime profile | Qwen local provider | 10 prompts | forward/sort/transfer time | MUST | TODO | Guides optimization |
| R005 | M2 | Adaptive schedule pilot | FH-SparSamp v1 | 3 prompts x 2 seeds x 4 budgets | success, bit/token | MUST | REJECTED-V1 | Capacity-ratio controller underperformed fixed-16 at 96/128/160 and only tied at 192; replace with tail fragmentation |
| R006 | M2 | Tail schedule mechanism probe | fixed-16 vs two tail splits and mixed schedule | 1 prompt x 2 seeds | success, tokens | MUST | REJECTED-SMOKE | No schedule beat fixed-16; stop block scheduling and move to observed semantic/precision failures |
| R007 | M3 | Precision replay | FP16/BF16/FP32 | 10 prompts | exact decode, support loss | MUST | NEXT | Highest-priority research claim after schedule rejection |
| R008 | M3 | Precision detector | mass variants | Native/stego samples | detector AUC | MUST | TODO | Reproduce published signal |
| R009 | M4 | Semantic finishing tail | stop/punctuation/EOS | 50 covers | preference, completeness | MUST | NEXT | Directly addresses observed truncated Qwen sentences; keep capacity prefix metrics separate |
| R010 | API | Repeated-query drift probe | DeepSeek top-20 | 20 prompts | churn, drift, mass, cost | NICE | BLOCKED | Needs API key |
| R011 | M3 | ACL 2026 RRC termination audit | Paper Algorithm 3/4 clean-room | Mock deterministic distributions | exact decode, modular wrap | MUST | COUNTEREXAMPLE | 500 samples show 5%-9% decode failure; implement verified termination before Qwen scale |
| R012 | M3 | Verified-RRC reliability/capacity | Reverse-verified termination | Mock then Qwen | exact decode, extra tokens, bit/token, speed | MUST | MOCK-PASS | 500/500 exact; mean overhead 0.04-0.15 token, max 2; proceed to Qwen smoke |
| R013 | M3 | Verified-RRC semantic pilot | Fixed-16/64 vs Verified-RRC | Qwen 1.5B, 3 Chinese prompts x 2 seeds | completion, bits/token, ambiguity, readable cover | MUST | PILOT-DONE | At 128 tokens all variants 3/6; at 160 all 6/6. RRC entropy utilization 0.980, ambiguity 0/6; no completion win |
