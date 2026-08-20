"""Diagnose FP16 vs BF16 logit differences on the same token sequence."""
from __future__ import annotations
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import torch
from sparsamp_semantic.providers.huggingface import (
    HuggingFaceConfig, HuggingFaceProvider,
    quantize_relative_logits,
)

MODEL = "models/qwen2.5-1.5b-instruct"
PROMPT = "hello world"

def run_dtype(dtype: str):
    config = HuggingFaceConfig(
        model_name=MODEL,
        device="cuda",
        dtype=dtype,
        logit_quantum=0.5,
        top_p=0.95,
        temperature=1.0,
    )
    provider = HuggingFaceProvider(config)
    session = provider.start(PROMPT)
    
    results = []
    for step in range(10):
        snap = session.next_distribution()
        bins = snap.metadata.get("quantized_logit_bins", {})
        # Get top-5 tokens and their bins
        top5 = sorted(snap.candidates, key=lambda c: int(c.rank))[:5]
        top5_data = []
        for c in top5:
            tid = int(c.token_id)
            top5_data.append({
                "token_id": tid,
                "logit_bin": bins.get(tid, None),
                "probability": float(c.probability),
                "rank": int(c.rank),
            })
        results.append({
            "step": step,
            "top5": top5_data,
            "native_token_id": int(snap.native_token_id) if snap.native_token_id else None,
        })
        # Feed the native token to continue
        session.append(snap.native_token_id)
    return results

print("=== FP16 ===")
fp16_results = run_dtype("float16")
print(json.dumps(fp16_results, indent=2))

# Free GPU memory
import gc
gc.collect()
torch.cuda.empty_cache()

print("\n=== BF16 ===")
bf16_results = run_dtype("bfloat16")
print(json.dumps(bf16_results, indent=2))

# Compare
print("\n=== COMPARISON ===")
for step in range(min(len(fp16_results), len(bf16_results))):
    fp16_top5 = fp16_results[step]["top5"]
    bf16_top5 = bf16_results[step]["top5"]
    
    fp16_tokens = {t["token_id"]: t for t in fp16_top5}
    bf16_tokens = {t["token_id"]: t for t in bf16_top5}
    
    common = set(fp16_tokens.keys()) & set(bf16_tokens.keys())
    print(f"\nStep {step}:")
    print(f"  FP16 native: {fp16_results[step]['native_token_id']}")
    print(f"  BF16 native: {bf16_results[step]['native_token_id']}")
    print(f"  Common tokens in top-5: {len(common)}")
    
    for tid in sorted(common, key=lambda t: fp16_tokens[t]["rank"]):
        fp16_bin = fp16_tokens[tid]["logit_bin"]
        bf16_bin = bf16_tokens[tid]["logit_bin"]
        delta = (bf16_bin - fp16_bin) if (fp16_bin is not None and bf16_bin is not None) else None
        print(f"    Token {tid}: FP16 bin={fp16_bin}, BF16 bin={bf16_bin}, delta={delta}, "
              f"FP16 prob={fp16_tokens[tid]['probability']:.6f}, "
              f"BF16 prob={bf16_tokens[tid]['probability']:.6f}")
