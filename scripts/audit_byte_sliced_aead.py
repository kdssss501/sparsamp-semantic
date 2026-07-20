"""R030 authenticated-message pilot for byte-sliced RS variants.

Each variant is encoded and replayed under one fixed provider configuration,
while the recovered frame must pass ChaCha20-Poly1305 authentication. A
successful raw-byte decode is therefore not counted as a message success when
the AEAD frame is malformed or authenticated with the wrong key.
"""

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
from sparsamp_semantic.payload import PayloadCodec, bits_to_bytes, bytes_to_bits  # noqa: E402
from sparsamp_semantic.providers.huggingface import (  # noqa: E402
    HuggingFaceConfig,
    HuggingFaceProvider,
)


DEFAULT_PROMPTS = (
    "Explain why reproducible AI experiments matter.",
    "Describe two practices that improve secure software updates.",
    "Explain one benefit and one risk of language models in education.",
)
DEFAULT_MESSAGES = ("Trust tests.", "Protect meaning.")
KEY = b"r030-aead-audit-key-0123456789"


def message_frame(message: str, prompt_index: int, message_index: int) -> bytes:
    """Seal one deterministic message with a nonce unique within the pilot."""

    nonce = hmac.new(
        KEY,
        f"R030\\0nonce\\0{prompt_index}\\0{message_index}".encode(),
        hashlib.sha256,
    ).digest()[:12]
    bits = PayloadCodec().seal(message, KEY, nonce=nonce)
    return bits_to_bytes(bits)


def bit_errors(expected: bytes, observed: bytes | None) -> int:
    if observed is None:
        return len(expected) * 8
    return sum(
        (left ^ right).bit_count() for left, right in zip(expected, observed, strict=False)
    ) + max(0, len(expected) - len(observed)) * 8


def raw_symbol_errors(expected_codeword: bytes, records: list[Any]) -> int:
    errors = 0
    for record in records:
        index = int(record.window_index)
        expected = expected_codeword[index] if index < len(expected_codeword) else None
        if record.recovered_symbol is None or expected is None or record.recovered_symbol != expected:
            errors += 1
    return errors + max(0, len(expected_codeword) - len(records))


def authenticated_message(payload: bytes | None, expected_message: str) -> tuple[bool, str | None]:
    if payload is None:
        return False, "missing_payload"
    try:
        recovered = PayloadCodec().open(bytes_to_bits(payload), KEY)
    except Exception as error:  # noqa: BLE001 - preserve authentication failure details
        return False, f"{type(error).__name__}: {error}"
    return recovered == expected_message, None if recovered == expected_message else "message_mismatch"


def variant_name(parity_bytes: int, logit_quantum: float | None) -> str:
    quantum = "none" if logit_quantum is None else f"{logit_quantum:g}"
    return f"parity={parity_bytes},q={quantum}"


def normalized_quantum(value: float | None) -> float | None:
    """Treat CLI zero as the unquantized baseline."""

    return None if value == 0 else value


def summarize(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for variant in sorted({str(row["variant"]) for row in rows}):
        selected = [row for row in rows if row["variant"] == variant]
        encoded = [row for row in selected if row["encode_success"]]
        total_bits = sum(int(row["frame_bits"]) for row in selected)
        result[variant] = {
            "trials": len(selected),
            "encode_successes": sum(bool(row["encode_success"]) for row in selected),
            "same_precision_payload_successes": sum(
                bool(row["same_precision_payload_success"]) for row in selected
            ),
            "same_precision_message_successes": sum(
                bool(row["same_precision_message_success"]) for row in selected
            ),
            "cross_precision_payload_successes": sum(
                bool(row["cross_precision_payload_success"]) for row in selected
            ),
            "cross_precision_message_successes": sum(
                bool(row["cross_precision_message_success"]) for row in selected
            ),
            "cross_precision_message_rate": sum(
                bool(row["cross_precision_message_success"]) for row in selected
            ) / len(selected)
            if selected
            else 0.0,
            "aggregate_frame_ber": sum(int(row["bit_errors"]) for row in selected) / total_bits
            if total_bits
            else 0.0,
            "mean_frame_bytes": mean(int(row["frame_bytes"]) for row in selected) if selected else 0.0,
            "mean_payload_bits_per_token": mean(
                float(row["payload_bits_per_token"]) for row in encoded
            )
            if encoded
            else 0.0,
            "mean_codeword_bits_per_token": mean(
                float(row["codeword_bits_per_token"]) for row in encoded
            )
            if encoded
            else 0.0,
            "mean_erasures": mean(int(row["cross_precision_erasures"]) for row in selected)
            if selected
            else 0.0,
            "mean_raw_symbol_errors": mean(
                int(row["cross_precision_raw_symbol_errors"]) for row in selected
            )
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


def build_report(
    args: Any,
    variants: list[tuple[int, float | None]],
    rows: list[dict[str, Any]],
    phase: str,
) -> dict[str, Any]:
    """Build a complete or checkpoint report without exposing key material."""

    return {
        "schema": f"sparsamp-{args.run_label.lower()}-aead-byte-sliced-pilot-v1",
        "run_label": args.run_label,
        "phase": phase,
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "reference_dtype": args.reference_dtype,
        "replay_dtype": args.replay_dtype,
        "prompt_count": len(DEFAULT_PROMPTS),
        "message_count": len(DEFAULT_MESSAGES),
        "variants": [variant_name(parity, quantum) for parity, quantum in variants],
        "summary": summarize(rows) if phase == "completed" else {},
        "rows": rows,
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    """Atomically persist a report so timeouts retain completed trials."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="models/gpt2")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--reference-dtype", default="float32")
    parser.add_argument("--replay-dtype", default="float16")
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--window-tokens", type=int, default=8)
    parser.add_argument("--parity-bytes", type=int, nargs="+", default=[2])
    parser.add_argument("--logit-quantum", type=float, nargs="+", default=[None])
    parser.add_argument("--run-label", default="R030")
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/R030_gpt2_aead_byte_sliced.json")
    )
    args = parser.parse_args()
    common = {
        "model_name": args.model,
        "top_p": args.top_p,
        "candidate_order": "token_id",
        "precision_context": "portable",
        "device": args.device,
        "allow_eos": False,
        "adaptive_temperature": False,
    }
    rows: list[dict[str, Any]] = []
    quantum_values = [normalized_quantum(value) for value in args.logit_quantum]
    variants = [(parity, quantum) for quantum in quantum_values for parity in args.parity_bytes]
    for quantum in quantum_values:
        reference_provider = HuggingFaceProvider(
            HuggingFaceConfig(dtype=args.reference_dtype, logit_quantum=quantum, **common)
        )
        for prompt_index, prompt in enumerate(DEFAULT_PROMPTS):
            for message_index, message in enumerate(DEFAULT_MESSAGES):
                frame = message_frame(message, prompt_index, message_index)
                for parity in args.parity_bytes:
                    config = ByteSlicedConfig(window_tokens=args.window_tokens, parity_bytes=parity)
                    codec = ByteSlicedCodec(config)
                    row: dict[str, Any] = {
                        "prompt_index": prompt_index,
                        "prompt": prompt,
                        "message_index": message_index,
                        "message": message,
                        "frame_bytes": len(frame),
                        "frame_bits": len(frame) * 8,
                        "frame_sha256": hashlib.sha256(frame).hexdigest(),
                        "parity_bytes": parity,
                        "logit_quantum": quantum,
                        "variant": variant_name(parity, quantum),
                        "codec": asdict(config),
                        "encode_success": False,
                        "same_precision_payload_success": False,
                        "same_precision_message_success": False,
                        "cross_precision_payload_success": False,
                        "cross_precision_message_success": False,
                        "bit_errors": len(frame) * 8,
                        "cross_precision_erasures": 0,
                        "cross_precision_raw_symbol_errors": 0,
                    }
                    try:
                        encoded = codec.encode(reference_provider.start(prompt), frame, KEY)
                    except Exception as error:  # noqa: BLE001 - preserve exact experiment failure
                        row["encode_error"] = {"type": type(error).__name__, "message": str(error)}
                        rows.append(row)
                        write_report(
                            args.output,
                            build_report(args, variants, rows, "reference_partial"),
                        )
                        continue
                    row.update(
                        {
                            "encode_success": True,
                            "token_ids": [int(value) for value in encoded.token_ids],
                            "token_count": len(encoded.token_ids),
                            "payload_bits_per_token": encoded.payload_bits_per_token,
                            "codeword_bits_per_token": encoded.codeword_bits_per_token,
                            "codeword_hex": encoded.codeword_bytes.hex(),
                            "guard_aborted_windows": sum(record.guard_aborted for record in encoded.records),
                        }
                    )
                    try:
                        same = codec.decode(reference_provider.start(prompt), encoded.token_ids, KEY)
                        row["same_precision_payload_success"] = same.payload_bytes == frame
                        same_message_ok, same_message_error = authenticated_message(
                            same.payload_bytes, message
                        )
                        row["same_precision_message_success"] = same_message_ok
                        row["same_precision_message_error"] = same_message_error
                        row["same_precision_decode_error"] = same.error
                    except Exception as error:  # noqa: BLE001
                        row["same_precision_decode_error"] = (
                            f"{type(error).__name__}: {error}"
                        )
                    rows.append(row)
                    write_report(
                        args.output,
                        build_report(args, variants, rows, "reference_partial"),
                    )
        del reference_provider
        release_cuda()

    for quantum in quantum_values:
        replay_provider = HuggingFaceProvider(
            HuggingFaceConfig(dtype=args.replay_dtype, logit_quantum=quantum, **common)
        )
        for row in rows:
            if row["logit_quantum"] != quantum or not row["encode_success"]:
                continue
            codec = ByteSlicedCodec(ByteSlicedConfig(**row["codec"]))
            frame = message_frame(str(row["message"]), int(row["prompt_index"]), int(row["message_index"]))
            expected_codeword = bytes.fromhex(str(row["codeword_hex"]))
            try:
                decoded = codec.decode(
                    replay_provider.start(str(row["prompt"])),
                    tuple(int(value) for value in row["token_ids"]),
                    KEY,
                )
                row["cross_precision_payload_success"] = decoded.payload_bytes == frame
                message_ok, message_error = authenticated_message(
                    decoded.payload_bytes, str(row["message"])
                )
                row["cross_precision_message_success"] = message_ok
                row["cross_precision_message_error"] = message_error
                row["bit_errors"] = bit_errors(frame, decoded.payload_bytes)
                row["cross_precision_erasures"] = decoded.erasure_count
                row["cross_precision_raw_symbol_errors"] = raw_symbol_errors(
                    expected_codeword, list(decoded.records)
                )
                row["recovered_frame_hex"] = (
                    decoded.payload_bytes.hex() if decoded.payload_bytes is not None else None
                )
                row["decode_error"] = decoded.error
            except Exception as error:  # noqa: BLE001
                row["decode_error"] = f"{type(error).__name__}: {error}"
                row["cross_precision_raw_symbol_errors"] = len(expected_codeword)
            write_report(
                args.output,
                build_report(args, variants, rows, "replay_partial"),
            )
        del replay_provider
        release_cuda()
    report = build_report(args, variants, rows, "completed")
    write_report(args.output, report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
