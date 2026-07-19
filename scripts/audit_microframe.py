"""Run an R026 fixed-window microframe audit on Mock or a local HF model."""

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

from sparsamp_semantic.microframe import MicroframeCodec, MicroframeConfig  # noqa: E402
from sparsamp_semantic.providers.mock import MockProvider  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("mock", "hf"), default="mock")
    parser.add_argument("--model", default="models/qwen2.5-1.5b-instruct")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--dtype", default="float16")
    parser.add_argument("--replay-dtype")
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--payload-hex", default="4142")
    parser.add_argument("--window-tokens", type=int, default=12)
    parser.add_argument("--symbol-bytes", type=int, default=1)
    parser.add_argument("--auth-tag-bits", type=int, default=8)
    parser.add_argument("--parity-bytes", type=int, default=0)
    parser.add_argument("--prompt", default="Explain why reproducible experiments matter.")
    parser.add_argument("--output", type=Path, default=Path("outputs/R026_microframe_mock.json"))
    args = parser.parse_args()
    payload = bytes.fromhex(args.payload_hex)
    key = b"r026-local-audit-key-0123456789"
    config = MicroframeConfig(
        window_tokens=args.window_tokens,
        symbol_bytes=args.symbol_bytes,
        auth_tag_bits=args.auth_tag_bits,
        parity_bytes=args.parity_bytes,
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
    provider = build_provider(args.dtype)
    codec = MicroframeCodec(config)
    encoded = codec.encode(provider.start(args.prompt), payload, key)
    replay_dtype = args.replay_dtype or args.dtype
    if args.provider == "hf" and replay_dtype != args.dtype:
        del provider
        gc.collect()
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        provider = build_provider(replay_dtype)
    decoded = codec.decode(provider.start(args.prompt), encoded.token_ids, key)
    report = {
        "schema": "sparsamp-r026-microframe-audit-v1",
        "timestamp": datetime.now(UTC).isoformat(),
        "config": asdict(config),
        "provider": args.provider,
        "reference_dtype": args.dtype,
        "replay_dtype": replay_dtype,
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "encoded": {
            "token_count": len(encoded.token_ids),
            "frame_count": encoded.frame_count,
            "bits_per_token": encoded.bits_per_token,
            "codeword_bits_per_token": encoded.codeword_bits_per_token,
            "records": [asdict(record) for record in encoded.records],
        },
        "decoded": {
            "success": decoded.success,
            "payload_matches": decoded.payload_bytes == payload,
            "erasure_count": decoded.erasure_count,
            "error": decoded.error,
            "records": [asdict(record) for record in decoded.records],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["decoded"], ensure_ascii=False, indent=2))
    return 0 if report["decoded"]["payload_matches"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
