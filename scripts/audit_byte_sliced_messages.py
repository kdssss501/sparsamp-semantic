"""R029 message-level pilot for byte-sliced RS variants."""

from __future__ import annotations

import argparse
import gc
import hashlib
import hmac
import json
import platform
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from sparsamp_semantic.byte_sliced import ByteSlicedCodec, ByteSlicedConfig  # noqa: E402
from sparsamp_semantic.providers.huggingface import (  # noqa: E402
    HuggingFaceConfig,
    HuggingFaceProvider,
)


DEFAULT_PROMPTS = (
    "Explain why reproducible AI experiments matter.",
    "Describe two practices that improve secure software updates.",
    "Explain one benefit and one risk of language models in education.",
)
KEY = b"r029-batch-audit-key-0123456789"


def payload_for_seed(seed: int, size: int) -> bytes:
    output = bytearray()
    counter = 0
    label = f"R029\0payload\0{seed}".encode()
    while len(output) < size:
        output.extend(hmac.new(KEY, label + counter.to_bytes(4, "big"), hashlib.sha256).digest())
        counter += 1
    return bytes(output[:size])


def bit_errors(expected: bytes, observed: bytes | None) -> int:
    if observed is None:
        return len(expected) * 8
    return sum((left ^ right).bit_count() for left, right in zip(expected, observed, strict=False)) + max(
        0, len(expected) - len(observed)
    ) * 8


def summarize(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for parity in sorted({int(row["parity_bytes"]) for row in rows}):
        selected = [row for row in rows if int(row["parity_bytes"]) == parity]
        encoded = [row for row in selected if row["encode_success"]]
        total_bits = sum(int(row["payload_bits"]) for row in selected)
        result[str(parity)] = {
            "trials": len(selected),
            "encode_successes": sum(bool(row["encode_success"]) for row in selected),
            "same_precision_successes": sum(bool(row["same_precision_success"]) for row in selected),
            "cross_precision_successes": sum(bool(row["cross_precision_success"]) for row in selected),
            "cross_precision_rate": sum(bool(row["cross_precision_success"]) for row in selected) / len(selected),
            "aggregate_ber": sum(int(row["bit_errors"]) for row in selected) / total_bits if total_bits else 0.0,
            "mean_payload_bits_per_token": mean(
                float(row["payload_bits_per_token"]) for row in encoded
            )
            if encoded
            else 0.0,
            "mean_erasures": mean(int(row["erasure_count"]) for row in selected) if selected else 0.0,
            "mean_raw_symbol_errors": mean(int(row["raw_symbol_errors"]) for row in selected)
            if selected
            else 0.0,
        }
    return result


def release_cuda() -> None:
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="models/gpt2")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--reference-dtype", default="float32")
    parser.add_argument("--replay-dtype", default="float16")
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--logit-quantum", type=float)
    parser.add_argument("--payload-bytes", type=int, default=2)
    parser.add_argument("--payload-seeds", type=int, nargs="+", default=[0, 1])
    parser.add_argument("--parity-bytes", type=int, nargs="+", default=[0, 2, 4])
    parser.add_argument("--window-tokens", type=int, default=8)
    parser.add_argument("--output", type=Path, default=Path("outputs/R029_gpt2_messages.json"))
    args = parser.parse_args()
    if args.payload_bytes < 1:
        raise ValueError("payload-bytes must be positive")

    common = {
        "model_name": args.model,
        "top_p": args.top_p,
        "logit_quantum": args.logit_quantum,
        "candidate_order": "token_id",
        "precision_context": "portable",
        "device": args.device,
        "allow_eos": False,
        "adaptive_temperature": False,
    }
    reference_provider = HuggingFaceProvider(
        HuggingFaceConfig(dtype=args.reference_dtype, **common)
    )
    rows: list[dict[str, Any]] = []
    for prompt_index, prompt in enumerate(DEFAULT_PROMPTS):
        for seed in args.payload_seeds:
            payload = payload_for_seed(seed, args.payload_bytes)
            for parity in args.parity_bytes:
                config = ByteSlicedConfig(window_tokens=args.window_tokens, parity_bytes=parity)
                codec = ByteSlicedCodec(config)
                row: dict[str, Any] = {
                    "prompt_index": prompt_index,
                    "prompt": prompt,
                    "payload_seed": seed,
                    "payload_bits": len(payload) * 8,
                    "payload_sha256": hashlib.sha256(payload).hexdigest(),
                    "parity_bytes": parity,
                    "codec": asdict(config),
                    "encode_success": False,
                    "same_precision_success": False,
                    "cross_precision_success": False,
                    "bit_errors": len(payload) * 8,
                }
                try:
                    encoded = codec.encode(reference_provider.start(prompt), payload, KEY)
                except Exception as error:  # noqa: BLE001 - preserve exact experiment failure
                    row["encode_error"] = {"type": type(error).__name__, "message": str(error)}
                    rows.append(row)
                    continue
                row.update(
                    {
                        "encode_success": True,
                        "token_ids": [int(value) for value in encoded.token_ids],
                        "token_count": len(encoded.token_ids),
                        "payload_bits_per_token": encoded.payload_bits_per_token,
                        "codeword_bits_per_token": encoded.codeword_bits_per_token,
                        "codeword_hex": encoded.codeword_bytes.hex(),
                    }
                )
                try:
                    same = codec.decode(reference_provider.start(prompt), encoded.token_ids, KEY)
                    row["same_precision_success"] = same.payload_bytes == payload
                except Exception as error:  # noqa: BLE001
                    row["same_precision_error"] = {"type": type(error).__name__, "message": str(error)}
                rows.append(row)

    del reference_provider
    release_cuda()
    replay_provider = HuggingFaceProvider(HuggingFaceConfig(dtype=args.replay_dtype, **common))
    for row in rows:
        if not row["encode_success"]:
            continue
        codec = ByteSlicedCodec(ByteSlicedConfig(**row["codec"]))
        payload = payload_for_seed(int(row["payload_seed"]), int(row["payload_bits"]) // 8)
        expected_codeword = bytes.fromhex(str(row["codeword_hex"]))
        try:
            decoded = codec.decode(
                replay_provider.start(str(row["prompt"])),
                tuple(int(value) for value in row["token_ids"]),
                KEY,
            )
            raw_errors = sum(
                record.recovered_symbol is None
                or record.recovered_symbol != expected_codeword[record.window_index]
                for record in decoded.records
            )
            row["cross_precision_success"] = decoded.payload_bytes == payload
            row["bit_errors"] = bit_errors(payload, decoded.payload_bytes)
            row["erasure_count"] = decoded.erasure_count
            row["raw_symbol_errors"] = raw_errors
            row["recovered_payload_hex"] = (
                decoded.payload_bytes.hex() if decoded.payload_bytes is not None else None
            )
            row["decode_error"] = decoded.error
        except Exception as error:  # noqa: BLE001
            row["decode_error"] = f"{type(error).__name__}: {error}"
            row["erasure_count"] = 0
            row["raw_symbol_errors"] = len(expected_codeword)

    del replay_provider
    release_cuda()
    report = {
        "schema": "sparsamp-r029-byte-sliced-message-audit-v1",
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "reference_dtype": args.reference_dtype,
        "replay_dtype": args.replay_dtype,
        "prompt_count": len(DEFAULT_PROMPTS),
        "payload_seeds": args.payload_seeds,
        "summary": summarize(rows),
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
