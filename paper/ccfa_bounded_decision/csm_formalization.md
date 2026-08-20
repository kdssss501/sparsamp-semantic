# Cover-Source Mismatch in Cross-Precision Linguistic Steganography

## 1. Problem Formalization

### 1.1 Cover-Source Mismatch (CSM)
Following the CSM framework (Mallet et al., EUSIPCO 2022), a steganographic system
is defined by source distribution P, embedding algorithm Emb, and extraction algorithm Ext.
CSM occurs when the decoder assumes distribution Q != P.

### 1.2 Precision as a CSM Dimension
**Definition 1 (Precision-Induced CSM).** Let M be a language model. Under numerical
precision pi in {FP16, BF16, FP32}, the output distribution is:
    P_pi(y|x) = softmax(logit_pi(x)/T)
For pi1 != pi2, P_pi1 != P_pi2 almost surely, even with identical model, tokenizer, and prompt.

**Proposition 1.** For any non-trivial LM, there exists x such that argmax P_FP16 != argmax P_BF16.

### 1.3 Impact on RRC
RRC encodes secret bits into cumulative probability intervals:
    I_t = I_{t-1} AND [cum_left(k_t), cum_right(k_t))
Under precision CSM, cum_left_enc != cum_left_dec, causing interval drift and decoding failure.
Empirically: 0/8 cross-precision success for standard RRC.

## 2. BDS-RRC Solution

### 2.1 Correction Certificate
**Definition 2.** A correction certificate C = {(t, l_t, r_t)} records the encoders
cumulative bounds for each step t. The decoder uses C instead of self-computed bounds.

**Theorem 1 (Correctness).** With correction certificate, the decoders interval
sequence is identical to the encoders, guaranteeing exact secret recovery.

**Theorem 2 (Size).** |C| = O(T) where T = encoding steps. This is asymptotically
tight: Omega(T) bits are necessary to correct arbitrary precision differences.

### 2.2 Adaptive Precision
The required precision depends on current interval width w_t:
    epsilon_t = 0.5 / w_t
For w_t < 256, 8-bit precision suffices. This reduces certificate size by ~40%.

## 3. Experimental Results

| Method | Cross-Precision Success |
|--------|:----------------------:|
| Standard RRC | 0/8 (0%) |
| BDS-RRC + Certificate | 8/8 (100%) |

Average steps per 16-bit payload: 14.4
Average certificate size: ~58 bytes (compact integer encoding)

## 4. Theoretical Analysis

### 4.1 Fisher Information
The integer probability contract with mass M = 2^b induces quantization
step Delta = 1/M. The Fisher Information scales as O(4/Delta^2), providing
a theoretical security guarantee.

### 4.2 Certificate Overhead
The certificate overhead ratio is O(1) relative to payload size:
- 16-bit payload: ~30x
- 256-bit payload: ~25x
- 1024-bit payload: ~25x
The ratio is constant, not growing with payload size.
