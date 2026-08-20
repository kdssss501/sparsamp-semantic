"""Diagnose why cross-precision decode fails despite identical logit bins."""
from __future__ import annotations
import sys, json, hashlib, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import torch
import gc
from sparsamp_semantic.providers.huggingface import HuggingFaceConfig, HuggingFaceProvider
from sparsamp_semantic.rrc import RrcConfig, RotationRangeCodec

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

# Generate payload
payload = "".join(
    "1" if (hashlib.sha256(KEY + i.to_bytes(4, "big")).digest()[0] & 1) else "0"
    for i in range(PAYLOAD_BITS)
)
print(f"Payload: {payload}")

# Encode with FP16
print("\n=== Encoding with FP16 ===")
provider_fp16 = load_provider("float16")
rrc_config = RrcConfig(message_bits=PAYLOAD_BITS, max_tokens=100, termination_mode="verified")
codec = RotationRangeCodec(rrc_config)
encoded = codec.encode(provider_fp16.start(PROMPT), payload, KEY)
print(f"Encoded tokens: {encoded.token_ids}")
print(f"Token count: {len(encoded.token_ids)}")

# Decode with FP16 (same session - should work)
print("\n=== Decoding with FP16 (same precision) ===")
decoded_fp16 = codec.decode(provider_fp16.start(PROMPT), encoded.token_ids, KEY)
print(f"FP16 decode: {decoded_fp16.bits}")
print(f"Match: {decoded_fp16.bits == payload}")

# Free GPU memory
del provider_fp16
gc.collect()
torch.cuda.empty_cache()

# Decode with BF16
print("\n=== Decoding with BF16 (cross precision) ===")
provider_bf16 = load_provider("bfloat16")
decoded_bf16 = codec.decode(provider_bf16.start(PROMPT), encoded.token_ids, KEY)
print(f"BF16 decode: {decoded_bf16.bits}")
print(f"Match: {decoded_bf16.bits == payload}")

# Compare step by step
print("\n=== Step-by-step comparison ===")
provider_fp16_2 = load_provider("float16")
session_fp16 = provider_fp16_2.start(PROMPT)

provider_bf16_2 = load_provider("bfloat16")
session_bf16 = provider_bf16_2.start(PROMPT)

for i, tid in enumerate(encoded.token_ids):
    snap_fp16 = session_fp16.next_distribution()
    snap_bf16 = session_bf16.next_distribution()
    
    fp16_bins = snap_fp16.metadata.get("quantized_logit_bins", {})
    bf16_bins = snap_bf16.metadata.get("quantized_logit_bins", {})
    
    fp16_ids = {int(c.token_id) for c in snap_fp16.candidates}
    bf16_ids = {int(c.token_id) for c in snap_bf16.candidates}
    common = fp16_ids & bf16_ids
    
    fp16_native = int(snap_fp16.native_token_id) if snap_fp16.native_token_id else None
    bf16_native = int(snap_bf16.native_token_id) if snap_bf16.native_token_id else None
    
    print(f"Step {i}: token={tid}, FP16 native={fp16_native}, BF16 native={bf16_native}")
    print(f"  Common tokens: {len(common)}/{len(fp16_ids)}/{len(bf16_ids)}")
    
    # Compare probabilities for the token we're feeding
    fp16_prob = None
    bf16_prob = None
    for c in snap_fp16.candidates:
        if int(c.token_id) == int(tid):
            fp16_prob = float(c.probability)
            break
    for c in snap_bf16.candidates:
        if int(c.token_id) == int(tid):
            bf16_prob = float(c.probability)
            break
    print(f"  Token {tid}: FP16 prob={fp16_prob}, BF16 prob={bf16_prob}")
    
    tid_int = int(tid)
    fp16_bin = fp16_bins.get(tid_int)
    bf16_bin = bf16_bins.get(tid_int)
    print(f"  Token {tid} bin: FP16={fp16_bin}, BF16={bf16_bin}")
    
    session_fp16.append(tid)
    session_bf16.append(tid)

del provider_fp16_2, provider_bf16_2
gc.collect()
torch.cuda.empty_cache()
