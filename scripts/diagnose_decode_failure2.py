"""Test cross-precision with integer mass allocation."""
from __future__ import annotations
import sys, json, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import torch, gc
from sparsamp_semantic.providers.huggingface import HuggingFaceConfig, HuggingFaceProvider
from sparsamp_semantic.rrc import RrcConfig, RotationRangeCodec
from sparsamp_semantic.bds_enhanced_rrc import BdsRrcConfig, BdsEnhancedRotationRangeCodec

MODEL = "models/qwen2.5-1.5b-instruct"
PROMPT = "hello world"
KEY = hashlib.sha256(b"test-key").digest()
PAYLOAD_BITS = 16

def load_provider(dtype):
    config = HuggingFaceConfig(
        model_name=MODEL, device="cuda", dtype=dtype,
        logit_quantum=0.5, top_p=0.95, temperature=1.0,
    )
    return HuggingFaceProvider(config)

payload = "".join(
    "1" if (hashlib.sha256(KEY + i.to_bytes(4, "big")).digest()[0] & 1) else "0"
    for i in range(PAYLOAD_BITS)
)
print(f"Payload: {payload}")

# Test 1: Standard RRC with probability_mass_bits
print("\n=== Test 1: Standard RRC with integer mass (probability_mass_bits=16) ===")
provider_fp16 = load_provider("float16")
rrc_config = RrcConfig(
    message_bits=PAYLOAD_BITS, max_tokens=100, termination_mode="verified",
    probability_quantum=None, probability_mass_bits=16,
)
codec = RotationRangeCodec(rrc_config)
encoded = codec.encode(provider_fp16.start(PROMPT), payload, KEY)
print(f"Encoded tokens: {len(encoded.token_ids)}")

# Decode FP16
decoded_fp16 = codec.decode(provider_fp16.start(PROMPT), encoded.token_ids, KEY)
print(f"FP16 decode: {decoded_fp16.bits}, Match: {decoded_fp16.bits == payload}")

del provider_fp16; gc.collect(); torch.cuda.empty_cache()

# Decode BF16
provider_bf16 = load_provider("bfloat16")
decoded_bf16 = codec.decode(provider_bf16.start(PROMPT), encoded.token_ids, KEY)
print(f"BF16 decode: {decoded_bf16.bits}, Match: {decoded_bf16.bits == payload}")

del provider_bf16; gc.collect(); torch.cuda.empty_cache()

# Test 2: BDS-RRC with integer mass
print("\n=== Test 2: BDS-RRC with integer mass ===")
provider_fp16 = load_provider("float16")
bds_config = BdsRrcConfig(
    message_bits=PAYLOAD_BITS, max_tokens=100, termination_mode="verified",
    probability_quantum=None, probability_mass_bits=16,
    bin_shift_radius=1, envelope_top_k=3,
    vulnerable_step_policy="record",
)
bds_codec = BdsEnhancedRotationRangeCodec(bds_config)
encoded_bds = bds_codec.encode(provider_fp16.start(PROMPT), payload, KEY)
print(f"Encoded tokens: {len(encoded_bds.token_ids)}")
if hasattr(encoded_bds, "_bds_enabled") and encoded_bds._bds_enabled:
    print(f"Vulnerable steps: {len(encoded_bds._bds_vulnerable_steps)}")
    print(f"Vulnerable indices: {encoded_bds._bds_vulnerable_steps}")

decoded_fp16_bds = bds_codec.decode(provider_fp16.start(PROMPT), encoded_bds.token_ids, KEY)
print(f"FP16 decode: {decoded_fp16_bds.bits}, Match: {decoded_fp16_bds.bits == payload}")

del provider_fp16; gc.collect(); torch.cuda.empty_cache()

provider_bf16 = load_provider("bfloat16")
decoded_bf16_bds = bds_codec.decode(provider_bf16.start(PROMPT), encoded_bds.token_ids, KEY)
print(f"BF16 decode: {decoded_bf16_bds.bits}, Match: {decoded_bf16_bds.bits == payload}")

del provider_bf16; gc.collect(); torch.cuda.empty_cache()

# Test 3: Compare bin differences at each step
print("\n=== Test 3: Bin comparison at each step ===")
provider_fp16 = load_provider("float16")
provider_bf16 = load_provider("bfloat16")
session_fp16 = provider_fp16.start(PROMPT)
session_bf16 = provider_bf16.start(PROMPT)

bin_diffs = []
for i, tid in enumerate(encoded_bds.token_ids):
    snap_fp16 = session_fp16.next_distribution()
    snap_bf16 = session_bf16.next_distribution()
    
    fp16_bins = snap_fp16.metadata.get("quantized_logit_bins", {})
    bf16_bins = snap_bf16.metadata.get("quantized_logit_bins", {})
    
    tid_int = int(tid)
    fp16_bin = fp16_bins.get(tid_int)
    bf16_bin = bf16_bins.get(tid_int)
    
    diff = None
    if fp16_bin is not None and bf16_bin is not None:
        diff = bf16_bin - fp16_bin
    
    bin_diffs.append(diff)
    
    if diff != 0:
        print(f"Step {i}: token={tid}, FP16 bin={fp16_bin}, BF16 bin={bf16_bin}, diff={diff}")
    
    # Also check all common tokens
    common = set(fp16_bins.keys()) & set(bf16_bins.keys())
    for t in common:
        if fp16_bins[t] != bf16_bins[t]:
            print(f"  Token {t}: FP16 bin={fp16_bins[t]}, BF16 bin={bf16_bins[t]}, diff={bf16_bins[t] - fp16_bins[t]}")
    
    session_fp16.append(tid)
    session_bf16.append(tid)

print(f"\nBin diffs: {bin_diffs}")
print(f"Non-zero diffs: {sum(1 for d in bin_diffs if d != 0)}")

del provider_fp16, provider_bf16
gc.collect(); torch.cuda.empty_cache()
