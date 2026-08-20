
"""Verify that top-K token bins are stable across FP16/BF16."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import torch, gc
from sparsamp_semantic.providers.huggingface import HuggingFaceConfig, HuggingFaceProvider

MODEL = "models/qwen2.5-1.5b-instruct"
PROMPTS = [
    "hello world",
    "Explain quantum computing in simple terms.",
    "Write a short story about a robot.",
    "Describe the future of education.",
]

def check_stability(prompt, K=3, steps=15):
    config_fp16 = HuggingFaceConfig(
        model_name=MODEL, device="cuda", dtype="float16",
        logit_quantum=0.5, top_p=0.95, temperature=1.0,
    )
    config_bf16 = HuggingFaceConfig(
        model_name=MODEL, device="cuda", dtype="bfloat16",
        logit_quantum=0.5, top_p=0.95, temperature=1.0,
    )
    
    provider_fp16 = HuggingFaceProvider(config_fp16)
    session_fp16 = provider_fp16.start(prompt)
    
    provider_bf16 = HuggingFaceProvider(config_bf16)
    session_bf16 = provider_bf16.start(prompt)
    
    mismatches = 0
    total_steps = 0
    
    for step in range(steps):
        snap_fp16 = session_fp16.next_distribution()
        snap_bf16 = session_bf16.next_distribution()
        
        fp16_bins = snap_fp16.metadata.get("quantized_logit_bins", {})
        bf16_bins = snap_bf16.metadata.get("quantized_logit_bins", {})
        
        fp16_topk = sorted(snap_fp16.candidates, key=lambda c: int(c.rank))[:K]
        bf16_topk = sorted(snap_bf16.candidates, key=lambda c: int(c.rank))[:K]
        
        fp16_topk_ids = {int(c.token_id) for c in fp16_topk}
        bf16_topk_ids = {int(c.token_id) for c in bf16_topk}
        
        if fp16_topk_ids != bf16_topk_ids:
            print(f"Step {step}: Top-K token sets differ!")
            print(f"  FP16: {fp16_topk_ids}")
            print(f"  BF16: {bf16_topk_ids}")
            mismatches += 1
        
        for tid in fp16_topk_ids & bf16_topk_ids:
            fp16_bin = fp16_bins.get(tid)
            bf16_bin = bf16_bins.get(tid)
            if fp16_bin != bf16_bin:
                print(f"Step {step}: Token {tid} bin differs: FP16={fp16_bin}, BF16={bf16_bin}")
                mismatches += 1
        
        total_steps += 1
        
        native = snap_fp16.native_token_id
        if native is None:
            native = snap_fp16.candidates[0].token_id
        session_fp16.append(native)
        session_bf16.append(native)
    
    del provider_fp16, provider_bf16
    gc.collect()
    torch.cuda.empty_cache()
    
    return mismatches, total_steps

for K in [2, 3, 4, 5]:
    print(f"
=== Testing K={K} ===")
    total_mismatches = 0
    total_steps = 0
    for prompt in PROMPTS:
        print(f"  Prompt: {prompt[:50]}...")
        m, s = check_stability(prompt, K=K, steps=15)
        total_mismatches += m
        total_steps += s
        if m > 0:
            print(f"    Mismatches: {m}/{s}")
    print(f"  Total: {total_mismatches}/{total_steps} mismatches")
