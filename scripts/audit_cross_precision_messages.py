"""Audit complete SparSamp payload recovery across local model precision modes."""

from __future__ import annotations

import argparse
import gc
import hashlib
import hmac
import json
import os
import platform
import secrets
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from sparsamp_semantic.core import (  # noqa: E402
    CodecConfig,
    IncompleteEncodeError,
    SparSampCodec,
)
from sparsamp_semantic.providers.huggingface import (  # noqa: E402
    HuggingFaceConfig,
    HuggingFaceProvider,
)


DEFAULT_PROMPTS = (
    "Explain why reproducible AI experiments matter.",
    "Describe two practices that improve secure software updates.",
    "Explain one benefit and one risk of language models in education.",
)


def _payload_bits(key: bytes, seed: int, bit_length: int) -> str:
    output = bytearray()
    counter = 0
    label = f"R025\0payload\0{seed}".encode()
    while len(output) * 8 < bit_length:
        output.extend(
            hmac.new(key, label + counter.to_bytes(4, "big"), hashlib.sha256).digest()
        )
        counter += 1
    return "".join(f"{value:08b}" for value in output)[:bit_length]


def load_experiment_key(key_file: Path) -> tuple[bytes, str]:
    """Load an environment key or create a persistent ignored experiment key."""

    environment_value = os.environ.get("SPARSAMP_SECRET_KEY", "")
    if len(environment_value.encode()) >= 16:
        return environment_value.encode(), "environment"
    if key_file.is_file():
        key = bytes.fromhex(key_file.read_text(encoding="ascii").strip())
        if len(key) < 16:
            raise RuntimeError("experiment key file must contain at least 16 bytes")
        return key, "key_file"
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key = secrets.token_bytes(32)
    key_file.write_text(key.hex(), encoding="ascii")
    return key, "generated_key_file"


def _variants(block_size: int, max_tokens: int) -> dict[str, CodecConfig]:
    common = {
        "block_size": block_size,
        "max_tokens": max_tokens,
        "preserve_probability_support": True,
    }
    return {
        "decimal_1e-15": CodecConfig(probability_quantum="1e-15", **common),
        "fixed_integer_16": CodecConfig(
            probability_quantum=None,
            probability_mass_bits=16,
            probability_support_strategy="base",
            **common,
        ),
        "waterfill_headroom_3": CodecConfig(
            probability_quantum=None,
            probability_mass_headroom_bits=3,
            probability_support_strategy="waterfill",
            **common,
        ),
        "waterfill_headroom_4": CodecConfig(
            probability_quantum=None,
            probability_mass_headroom_bits=4,
            probability_support_strategy="waterfill",
            **common,
        ),
    }


def bit_error_count(expected: str, recovered: str) -> int:
    """Count mismatches and missing payload bits; ignore surplus decoded padding."""

    observed = recovered[: len(expected)]
    comparable = expected[: len(observed)]
    mismatches = sum(
        expected_bit != observed_bit
        for expected_bit, observed_bit in zip(comparable, observed, strict=True)
    )
    return mismatches + len(expected) - len(observed)


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    variants = sorted({str(row["variant"]) for row in rows})
    for variant in variants:
        selected = [row for row in rows if row["variant"] == variant]
        encoded = [row for row in selected if row["encode_success"]]
        total_bits = sum(int(row["payload_bit_length"]) for row in selected)
        summary[variant] = {
            "trials": len(selected),
            "encode_successes": sum(bool(row["encode_success"]) for row in selected),
            "same_precision_successes": sum(
                bool(row.get("same_precision_success")) for row in selected
            ),
            "cross_precision_successes": sum(
                bool(row.get("cross_precision_success")) for row in selected
            ),
            "cross_precision_message_success_rate": (
                sum(bool(row.get("cross_precision_success")) for row in selected)
                / len(selected)
                if selected
                else 0.0
            ),
            "aggregate_ber": (
                sum(int(row.get("bit_errors", row["payload_bit_length"])) for row in selected)
                / total_bits
                if total_bits
                else 0.0
            ),
            "decode_error_count": sum(bool(row.get("decode_error")) for row in selected),
            "mean_token_count": (
                mean(int(row["token_count"]) for row in encoded) if encoded else 0.0
            ),
            "mean_bits_per_token": (
                mean(float(row["bits_per_token"]) for row in encoded) if encoded else 0.0
            ),
            "mean_forward_kl_nats": (
                mean(float(row["forward_quantization_kl_nats"]) for row in encoded)
                if encoded
                else 0.0
            ),
            "mean_quantization_tv_step_sum": (
                mean(float(row["quantization_tv_step_sum"]) for row in encoded)
                if encoded
                else 0.0
            ),
        }
    return summary


def _release_cuda() -> None:
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


def _decode_bits(
    codec: SparSampCodec,
    provider: HuggingFaceProvider,
    prompt: str,
    token_ids: tuple[int, ...],
    key: bytes,
) -> str:
    return codec.decode(provider.start(prompt), token_ids, key).bits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="models/gpt2")
    parser.add_argument("--prompt", action="append", dest="prompts")
    parser.add_argument("--payload-seeds", type=int, nargs="+", default=[0, 1])
    parser.add_argument("--payload-bits", type=int, default=16)
    parser.add_argument("--block-size", type=int, default=8)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--reference-dtype", default="float32")
    parser.add_argument("--replay-dtype", default="float16")
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/R025_gpt2_message_audit.json")
    )
    parser.add_argument(
        "--key-file", type=Path, default=Path("outputs/R025_experiment.key")
    )
    args = parser.parse_args()
    if args.payload_bits < 1:
        raise ValueError("payload bits must be positive")
    if args.block_size < 1:
        raise ValueError("block size must be positive")
    if args.max_tokens < 1:
        raise ValueError("max tokens must be positive")

    key, key_source = load_experiment_key(args.key_file)
    prompts = tuple(args.prompts or DEFAULT_PROMPTS)
    variants = _variants(args.block_size, args.max_tokens)
    common_model = {
        "model_name": args.model,
        "top_p": args.top_p,
        "temperature": args.temperature,
        "candidate_order": "token_id",
        "precision_context": "portable",
        "device": args.device,
        "allow_eos": False,
        "adaptive_temperature": False,
    }
    reference_config = HuggingFaceConfig(dtype=args.reference_dtype, **common_model)
    replay_config = HuggingFaceConfig(dtype=args.replay_dtype, **common_model)
    reference_provider = HuggingFaceProvider(reference_config)
    rows: list[dict[str, Any]] = []

    for prompt_index, prompt in enumerate(prompts):
        for payload_seed in args.payload_seeds:
            payload = _payload_bits(key, payload_seed, args.payload_bits)
            for variant, codec_config in variants.items():
                codec = SparSampCodec(codec_config)
                row: dict[str, Any] = {
                    "prompt_index": prompt_index,
                    "prompt": prompt,
                    "payload_seed": payload_seed,
                    "payload_bit_length": len(payload),
                    "payload_sha256": hashlib.sha256(payload.encode()).hexdigest(),
                    "variant": variant,
                    "codec": asdict(codec_config),
                    "encode_success": False,
                    "same_precision_success": False,
                    "cross_precision_success": False,
                    "bit_errors": len(payload),
                }
                try:
                    encoded = codec.encode(reference_provider.start(prompt), payload, key)
                except IncompleteEncodeError as error:
                    row["encode_error"] = {
                        "type": type(error).__name__,
                        "message": str(error),
                        "completed_bits": error.completed_bits,
                        "token_count": len(error.token_ids),
                    }
                    rows.append(row)
                    continue
                row.update(
                    {
                        "encode_success": True,
                        "token_ids": [int(value) for value in encoded.token_ids],
                        "cover_text": encoded.text,
                        "token_count": len(encoded.token_ids),
                        "bits_per_token": encoded.bits_per_token,
                        "forward_quantization_kl_nats": (
                            encoded.forward_quantization_kl_nats
                        ),
                        "quantization_tv_step_sum": encoded.quantization_tv_step_sum,
                        "effective_mass_bits": [
                            record.effective_probability_mass_bits
                            for record in encoded.records
                            if record.effective_probability_mass_bits is not None
                        ],
                    }
                )
                try:
                    same_bits = _decode_bits(
                        codec,
                        reference_provider,
                        prompt,
                        encoded.token_ids,
                        key,
                    )
                    row["same_precision_success"] = same_bits[: len(payload)] == payload
                except Exception as error:  # noqa: BLE001 - experiment records exact failure
                    row["same_precision_error"] = {
                        "type": type(error).__name__,
                        "message": str(error),
                    }
                rows.append(row)

    del reference_provider
    _release_cuda()
    replay_provider = HuggingFaceProvider(replay_config)
    for row in rows:
        if not row["encode_success"]:
            continue
        codec = SparSampCodec(CodecConfig(**row["codec"]))
        payload = _payload_bits(key, int(row["payload_seed"]), int(row["payload_bit_length"]))
        try:
            recovered = _decode_bits(
                codec,
                replay_provider,
                str(row["prompt"]),
                tuple(int(value) for value in row["token_ids"]),
                key,
            )
            errors = bit_error_count(payload, recovered)
            row["recovered_bit_length"] = len(recovered)
            row["bit_errors"] = errors
            row["cross_precision_success"] = errors == 0
        except Exception as error:  # noqa: BLE001 - experiment records exact failure
            row["decode_error"] = {
                "type": type(error).__name__,
                "message": str(error),
            }

    del replay_provider
    _release_cuda()
    payload = {
        "schema": "sparsamp-cross-precision-message-audit-v1",
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "reference": asdict(reference_config),
        "replay": asdict(replay_config),
        "key_fingerprint": hashlib.sha256(key).hexdigest()[:12],
        "key_source": key_source,
        "prompt_count": len(prompts),
        "payload_seeds": args.payload_seeds,
        "payload_bits": args.payload_bits,
        "summary": summarize_rows(rows),
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
