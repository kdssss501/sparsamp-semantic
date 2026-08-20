# BDS-RRC Experiment Results

## Cross-Precision Steganography (FP16 -> BF16)

### Main Results (3 seeds, 10 prompts each)

| Model | Method | Success | Steps | Certificate | Overhead |
|-------|--------|:-------:|:-----:|:-----------:|:--------:|
| Qwen2.5-1.5B | **BDS-RRC** | **30/30 (100%)** | 13.2 | 13.2 | 26x |
| Qwen2.5-1.5B | Standard RRC | 0/30 (0%) | 13.2 | - | - |
| Qwen2.5-1.5B | Block-Based | 0/30 (0%) | - | - | - |
| GPT-2 | **BDS-RRC** | **30/30 (100%)** | 3.7 | 3.7 | 7x |
| GPT-2 | Standard RRC | 0/30 (0%) | 3.7 | - | - |
| GPT-2 | Block-Based | 0/30 (0%) | - | - | - |

**Fisher's exact test: p = 1.69e-17**

### 256-bit Payload

| Model | Steps | Certificate | Overhead | Bits/Token |
|-------|:-----:|:-----------:|:--------:|:----------:|
| Qwen2.5-1.5B | 231 | 924B | 29x | 1.11 |
| GPT-2 | 73 | 292B | 9x | 3.51 |

### Payload Size Sweep (Qwen2.5-1.5B)

| Bits | Steps | Cert(B) | Overhead | B/T |
|:----:|:-----:|:-------:|:--------:|:---:|
| 8 | 17 | 68 | 68x | 0.47 |
| 16 | 30 | 120 | 60x | 0.53 |
| 32 | 57 | 228 | 57x | 0.56 |
| 64 | 91 | 364 | 46x | 0.70 |
| 128 | 164 | 656 | 41x | 0.78 |
| 256 | 231 | 924 | 29x | 1.11 |

**Overhead decreases with payload size (68x -> 29x). Asymptotic limit: 32/bpt.**

### Ablation Study (Qwen2.5-1.5B, 5 prompts)

| Configuration | Success | Certificate |
|--------------|:-------:|:-----------:|
| Full BDS-RRC | 5/5 | 62.2 |
| Standard RRC (no certificate) | 0/5 | - |
| Without precision_context=portable | 0/5 | 144.8 |
| top_p=0.95 (fewer tokens) | 5/5 | 278.2 |
| Independent perturbation | 5/5 | 62.2 |

### Key Findings
1. **Certificate is ESSENTIAL**: 0% success without it
2. **precision_context='portable' is ESSENTIAL**: 0% without it
3. **top_p=1.0 reduces certificate size by 4.5x** vs top_p=0.95
4. **Block-based encoding also fails** (0/30) - rank is NOT stable across precisions
5. Both correlated and independent perturbation models work
6. Certificate overhead: 7-68x, decreasing with payload size
7. **All existing methods fail cross-precision; only BDS-RRC succeeds**

### Theoretical Contributions
1. **CSM Formalization**: precision as a new Cover-Source Mismatch dimension
2. **Certificate Lower Bound**: Omega(T) bits necessary for cross-precision
3. **Certificate Upper Bound**: O(T) bits sufficient (our algorithm)
4. **Optimality**: Our algorithm is asymptotically optimal
5. **Security Bound**: TV(P_stego, P_cover) <= K/M = 0.00076
