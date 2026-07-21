# R050 Integer Apportionment Audit

## Material Passport

- Origin: Stage 4 response to methodology/domain review
- Verification status: ANALYZED
- Source: `outputs\R047_local_target.json`
- Source SHA-256: `3b0a154455968c15427a66405ab4c7fdbe6203eb017a27a127ee722ec56a6ea0`

## Result

- Trials: 20
- Token-level contracts: 1500
- Candidate counts: [2]
- Integer mass bits: [16]
- Maximum apportionment TV upper bound: 0.0000305176
- Mean recorded full-logit quantization TV: 0.0225753848
- Mean recorded support-truncation reverse KL: 0.3836614664 nats/token

## Interpretation

For k positive candidates and integer mass M, the base allocator reserves one count per candidate and applies largest remainder to M-k counts. Each positive coordinate error is strictly below 2/M, and at most k-1 coordinates can have positive error because coordinate errors sum to zero. Therefore TV is strictly below 2(k-1)/M.

This bound isolates the integer-apportionment component without pretending that KL components with different directions are additive. A finite distribution-free KL bound is impossible unless every pre-apportionment target probability has a public positive lower bound. The bound applies to both reference and target allocations with the same k and M; it does not measure support truncation or full-logit quantization.
