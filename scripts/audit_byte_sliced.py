"""Run the R029 byte-sliced RS audit on Mock or a local HF model."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from sparsamp_semantic.byte_sliced import ByteSlicedCodec, ByteSlicedConfig  # noqa: E402
from sparsamp_semantic.payload import PayloadCodec, bits_to_bytes, bytes_to_bits  # noqa: E402
from sparsamp_semantic.providers.mock import MockProvider  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("mock", "hf"), default="mock")
    parser.add_argument("--model", default="models/gpt2")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--dtype", default="float16")
    parser.add_argument("--replay-dtype")
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--payload-hex", default="4142")
    parser.add_argument("--message")
    parser.add_argument("--window-tokens", type=int, default=8)
    parser.add_argument("--parity-bytes", type=int, default=2)
    parser.add_argument("--cdf-uncertainty-bound", type=float, default=0.0)
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/R029_byte_sliced_mock.json")
    )
    args = parser.parse_args()
    key = b"r029-local-audit-key-0123456789"
    if args.message is not None:
        payload_bits = PayloadCodec().seal(args.message, key, nonce=bytes(range(12)))
        payload = bits_to_bytes(payload_bits)
    else:
        payload = bytes.fromhex(args.payload_hex)
    config = ByteSlicedConfig(
        window_tokens=args.window_tokens,
        parity_bytes=args.parity_bytes,
        cdf_uncertainty_bound=args.cdf_uncertainty_bound,
    )

    def build_provider(dtype: str):
        if args.provider == "mock":
            return MockProvider()
        from sparsamp_semantic.providers.huggingface import HuggingFaceConfig, HuggingFaceProvider

        return HuggingFaceProvider(
            HuggingFaceConfig(
                model_name=args.model,
                device=args.device,
                dtype=dtype,
                top_p=args.top_p,
                candidate_order="token_id",
                precision_context="portable",
                allow_eos=False,
                adaptive_temperature=False,
            )
        )

    codec = ByteSlicedCodec(config)
    provider = build_provider(args.dtype)
    encoded = codec.encode(provider.start("R029 byte-sliced audit"), payload, key)
    replay_dtype = args.replay_dtype or args.dtype
    if args.provider == "hf" and replay_dtype != args.dtype:
        del provider
        gc.collect()
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        provider = build_provider(replay_dtype)
    decoded = codec.decode(provider.start("R029 byte-sliced audit"), encoded.token_ids, key)
    payload_matches = decoded.payload_bytes == payload
    recovered_message = None
    message_error = None
    if decoded.payload_bytes is not None and args.message is not None:
        try:
            recovered_message = PayloadCodec().open(bytes_to_bits(decoded.payload_bytes), key)
        except Exception as error:  # noqa: BLE001 - record authentication failure
            message_error = f"{type(error).__name__}: {error}"
    report = {
        "schema": "sparsamp-r029-byte-sliced-audit-v1",
        "timestamp": datetime.now(UTC).isoformat(),
        "provider": args.provider,
        "reference_dtype": args.dtype,
        "replay_dtype": replay_dtype,
        "config": asdict(config),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "payload_bytes": len(payload),
        "encoded": {
            "token_count": len(encoded.token_ids),
            "codeword_bytes": len(encoded.codeword_bytes),
            "payload_bits_per_token": encoded.payload_bits_per_token,
            "codeword_bits_per_token": encoded.codeword_bits_per_token,
            "guard_aborted_windows": sum(record.guard_aborted for record in encoded.records),
            "records": [asdict(record) for record in encoded.records],
        },
        "decoded": {
            "success": decoded.success,
            "payload_matches": payload_matches,
            "message_matches": recovered_message == args.message if args.message is not None else None,
            "recovered_message": recovered_message,
            "message_error": message_error,
            "erasure_count": decoded.erasure_count,
            "error": decoded.error,
            "records": [asdict(record) for record in decoded.records],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["decoded"], ensure_ascii=False, indent=2))
    return 0 if payload_matches and (args.message is None or recovered_message == args.message) else 1


if __name__ == "__main__":
    raise SystemExit(main())
