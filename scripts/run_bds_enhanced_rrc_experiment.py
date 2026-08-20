"""BDS-Enhanced RRC cross-precision experiment.

This script compares standard RRC against BDS-enhanced RRC on a real
language model (Qwen2.5-1.5B-Instruct or GPT-2) across different
numerical precisions (FP32, FP16, BF16).

Usage:
    python scripts/run_bds_enhanced_rrc_experiment.py \
        --model models/qwen2.5-1.5b-instruct \
        --device cuda \
        --dtype float16 \
        --output outputs/bds_rrc_experiment.json

The experiment measures:
1. Round-trip correctness (encode-decode match)
2. BDS robustness analysis (vulnerable steps per trajectory)
3. Comparison with standard RRC
4. Cross-precision replay (encode in FP32, decode in FP16)
"""

from __future__ import annotations

import argparse
import json
import hashlib
import os
import sys
from pathlib import Path
from typing import Any

# Ensure the src directory is on the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sparsamp_semantic.bds_enhanced_rrc import (
    BdsRrcConfig,
    BdsEnhancedRotationRangeCodec,
    _compute_bds_envelope,
    verify_bds_robustness,
)
from sparsamp_semantic.rrc import RrcConfig, RotationRangeCodec
from sparsamp_semantic.providers.huggingface import HuggingFaceConfig, HuggingFaceProvider
from sparsamp_semantic.providers.mock import MockProvider


def load_key() -> bytes:
    """Load the secret key from the environment or generate a deterministic one."""
    key_hex = os.environ.get("SPARSAMP_SECRET_KEY", "")
    if key_hex:
        return bytes.fromhex(key_hex)
    # Deterministic fallback key for reproducibility
    return hashlib.sha256(b"bds-rrc-experiment-default-key").digest()


def run_single_trial(
    provider: HuggingFaceProvider,
    prompt: str,
    payload_bits: int,
    key: bytes,
    config: dict[str, Any],
    use_bds: bool = True,
) -> dict[str, Any]:
    """Run a single encode-decode trial with the given configuration."""
    if use_bds:
        codec_config = BdsRrcConfig(
            message_bits=payload_bits,
            max_tokens=config.get("max_tokens", 2048),
            bin_shift_radius=config.get("bin_shift_radius", 1),
            envelope_top_k=config.get("envelope_top_k", 3),
            logit_quantum=config.get("logit_quantum", 0.5),
            contract_temperature=config.get("contract_temperature", 1.0),
            contract_mass_bits=config.get("contract_mass_bits", 16),
            termination_mode=config.get("termination_mode", "verified"),
            vulnerable_step_policy=config.get("vulnerable_step_policy", "full"),
        )
        codec = BdsEnhancedRotationRangeCodec(codec_config)
    else:
        rrc_config = RrcConfig(
            message_bits=payload_bits,
            max_tokens=config.get("max_tokens", 2048),
            termination_mode=config.get("termination_mode", "verified"),
        )
        codec = RotationRangeCodec(rrc_config)

    # Generate random payload bits
    payload = "".join(
        "1" if (hashlib.sha256(key + i.to_bytes(4, "big")).digest()[0] & 1) else "0"
        for i in range(payload_bits)
    )

    result: dict[str, Any] = {
        "prompt": prompt,
        "payload_bits": payload_bits,
        "config": config,
        "use_bds": use_bds,
    }

    # Encode
    session = provider.start(prompt)
    try:
        encoded = codec.encode(session, payload, key)
        result["encode_success"] = True
        result["token_count"] = len(encoded.token_ids)
        result["encoded_bits"] = encoded.embedded_bits
        result["elapsed_seconds"] = encoded.elapsed_seconds
        result["bits_per_token"] = encoded.bits_per_token
        result["text"] = encoded.text

        # BDS-specific metadata
        if hasattr(encoded, "_bds_enabled") and encoded._bds_enabled:
            vulnerable = encoded._bds_vulnerable_steps
            result["vulnerable_steps"] = len(vulnerable)
            result["vulnerable_step_indices"] = list(vulnerable)
            result["vulnerable_ratio"] = len(vulnerable) / len(encoded.records) if encoded.records else 0.0
        else:
            result["vulnerable_steps"] = 0
            result["vulnerable_ratio"] = 0.0

        # Decode (same precision)
        decode_session = provider.start(prompt)
        cert = encoded._bds_certificate if hasattr(encoded, '_bds_certificate') else ()
        decoded = codec.decode(decode_session, encoded.token_ids, key, certificate=cert)
        result["decode_success"] = decoded.bits == payload
        result["decoded_bits"] = decoded.bits
        result["decoded_consumed_tokens"] = decoded.consumed_tokens

    except Exception as e:
        result["encode_success"] = False
        result["error"] = str(e)
        result["token_count"] = 0

    return result


def run_cross_precision_trial(
    provider_encode: HuggingFaceProvider,
    provider_decode: HuggingFaceProvider,
    prompt: str,
    payload_bits: int,
    key: bytes,
    config: dict[str, Any],
    encode_precision: str = "float16",
    decode_precision: str = "bfloat16",
) -> dict[str, Any]:
    """Encode in one precision, decode in another.

    The primary experiment is FP16 → BF16 (both 16-bit, the original setting).
    Also supports FP32 → FP16 for broader comparison.
    """
    codec_config = BdsRrcConfig(
        message_bits=payload_bits,
        max_tokens=config.get("max_tokens", 2048),
        bin_shift_radius=config.get("bin_shift_radius", 1),
        envelope_top_k=config.get("envelope_top_k", 3),
        logit_quantum=config.get("logit_quantum", 0.5),
        contract_temperature=config.get("contract_temperature", 1.0),
        contract_mass_bits=config.get("contract_mass_bits", 16),
        termination_mode=config.get("termination_mode", "verified"),
        vulnerable_step_policy=config.get("vulnerable_step_policy", "full"),
    )
    codec = BdsEnhancedRotationRangeCodec(codec_config)

    payload = "".join(
        "1" if (hashlib.sha256(key + i.to_bytes(4, "big")).digest()[0] & 1) else "0"
        for i in range(payload_bits)
    )

    result: dict[str, Any] = {
        "prompt": prompt,
        "payload_bits": payload_bits,
        "cross_precision": True,
        "encode_precision": encode_precision,
        "decode_precision": decode_precision,
    }

    # Encode in encode_precision
    session_encode = provider_encode.start(prompt)
    try:
        encoded = codec.encode(session_encode, payload, key)
        result["encode_success"] = True
        result["token_count"] = len(encoded.token_ids)
        result["text"] = encoded.text

        if hasattr(encoded, "_bds_enabled") and encoded._bds_enabled:
            vulnerable = encoded._bds_vulnerable_steps
            result["encode_vulnerable_steps"] = len(vulnerable)
            result["encode_vulnerable_ratio"] = len(vulnerable) / len(encoded.records) if encoded.records else 0.0
            if hasattr(encoded, "_bds_guard_steps"):
                result["encode_guard_steps"] = len(encoded._bds_guard_steps)

        # Decode in decode_precision
        decode_session = provider_decode.start(prompt)
        cert = encoded._bds_certificate if hasattr(encoded, '_bds_certificate') else ()
        decoded = codec.decode(decode_session, encoded.token_ids, key, certificate=cert)
        result["cross_decode_success"] = decoded.bits == payload
        result["cross_decoded_bits"] = decoded.bits
        result["decode_consumed_tokens"] = decoded.consumed_tokens

    except Exception as e:
        result["encode_success"] = False
        result["error"] = str(e)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="BDS-Enhanced RRC Experiment")
    parser.add_argument("--model", type=Path, required=True, help="Path to the model directory")
    parser.add_argument("--device", type=str, default="cuda", help="Torch device (cuda or cpu)")
    parser.add_argument("--dtype", type=str, default="float16", help="Model dtype")
    parser.add_argument("--output", type=Path, default=Path("outputs/bds_rrc_experiment.json"))
    parser.add_argument("--payload-bits", type=int, default=32, help="Payload size in bits")
    parser.add_argument("--max-tokens", type=int, default=512, help="Maximum tokens per trial")
    parser.add_argument("--prompts", type=str, nargs="*", default=[
        "请用自然、清晰的中文解释为什么可复现实验很重要。",
        "Write a short story about a robot learning to paint.",
        "描述一下人工智能对未来教育的影响。",
    ])
    parser.add_argument("--cross-precision", action="store_true", help="Run cross-precision trials")
    parser.add_argument("--mock", action="store_true", help="Use MockProvider instead of real model")
    args = parser.parse_args()

    key = load_key()
    config = {
        "max_tokens": args.max_tokens,
        "bin_shift_radius": 1,
        "envelope_top_k": 3,
        "logit_quantum": 0.5,
        "contract_temperature": 1.0,
        "contract_mass_bits": 16,
        "termination_mode": "verified",
        "vulnerable_step_policy": "full",
    }

    results: list[dict[str, Any]] = []

    if args.mock:
        # Use MockProvider for testing
        print("Using MockProvider (no real model)")
        provider = MockProvider()
        for prompt in args.prompts:
            print(f"  Prompt: {prompt[:60]}...")
            result = run_single_trial(provider, prompt, args.payload_bits, key, config, use_bds=True)
            results.append(result)
            print(f"    Tokens: {result.get('token_count', 'N/A')}, "
                  f"Success: {result.get('decode_success', False)}, "
                  f"Vulnerable: {result.get('vulnerable_ratio', 0.0):.2%}")
    else:
        # Use real HuggingFace model
        provider_config = HuggingFaceConfig(
            model_name=str(args.model),
            device=args.device,
            dtype=args.dtype,
            logit_quantum=0.5,
            top_p=1.0, top_k=50,
            temperature=1.0,
            precision_context="portable",
        )
        print(f"Loading model from {args.model}...")
        provider = HuggingFaceProvider(provider_config)

        for prompt in args.prompts:
            print(f"  Prompt: {prompt[:60]}...")
            # Standard RRC
            result_std = run_single_trial(provider, prompt, args.payload_bits, key, config, use_bds=False)
            result_std["trial_type"] = "standard_rrc"
            results.append(result_std)

            # BDS-RRC
            result_bds = run_single_trial(provider, prompt, args.payload_bits, key, config, use_bds=True)
            result_bds["trial_type"] = "bds_rrc"
            results.append(result_bds)

            print(f"    Standard RRC: {result_std.get('token_count', 'N/A')} tokens, "
                  f"Success: {result_std.get('decode_success', False)}")
            print(f"    BDS-RRC: {result_bds.get('token_count', 'N/A')} tokens, "
                  f"Success: {result_bds.get('decode_success', False)}, "
                  f"Vulnerable: {result_bds.get('vulnerable_ratio', 0.0):.2%}")

        # Cross-precision trials
        if args.cross_precision:
            # Primary experiment: FP16 → BF16 (both 16-bit, the original setting)
            print("\nCross-precision: FP16 → BF16 (primary):")
            provider_bf16 = HuggingFaceProvider(
                HuggingFaceConfig(
                    model_name=str(args.model),
                    device=args.device,
                    dtype="bfloat16",
                    logit_quantum=0.5,
                    top_p=1.0, top_k=50,
                    temperature=1.0,
            precision_context="portable",
                )
            )
            provider_fp16 = provider  # reuse the FP16 provider

            for prompt in args.prompts:
                result = run_cross_precision_trial(
                    provider_fp16, provider_bf16, prompt,
                    args.payload_bits, key, config,
                    encode_precision="float16", decode_precision="bfloat16",
                )
                result["trial_type"] = "cross_precision_fp16_bf16"
                results.append(result)
                print(f"    {prompt[:60]}...")
                print(f"      Cross decode: {result.get('cross_decode_success', False)}, "
                      f"FP16 vulnerable: {result.get('encode_vulnerable_ratio', 0.0):.2%}")

            # Secondary: FP32 → FP16 (broader comparison)
            print("\nCross-precision: FP32 → FP16 (secondary):")
            provider_fp32 = HuggingFaceProvider(
                HuggingFaceConfig(
                    model_name=str(args.model),
                    device=args.device,
                    dtype="float32",
                    logit_quantum=0.5,
                    top_p=1.0, top_k=50,
                    temperature=1.0,
            precision_context="portable",
                )
            )
            for prompt in args.prompts:
                result = run_cross_precision_trial(
                    provider_fp32, provider_fp16, prompt,
                    args.payload_bits, key, config,
                    encode_precision="float32", decode_precision="float16",
                )
                result["trial_type"] = "cross_precision_fp32_fp16"
                results.append(result)
                print(f"    {prompt[:60]}...")
                print(f"      Cross decode: {result.get('cross_decode_success', False)}, "
                      f"FP32 vulnerable: {result.get('encode_vulnerable_ratio', 0.0):.2%}")

    # Save results
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({
            "schema": "bds-rrc-experiment-v1",
            "model": str(args.model) if not args.mock else "mock",
            "payload_bits": args.payload_bits,
            "config": config,
            "key_sha256": hashlib.sha256(key).hexdigest(),
            "results": results,
        }, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
