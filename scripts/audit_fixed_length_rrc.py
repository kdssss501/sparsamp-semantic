"""Audit fixed-length Verified-RRC reliability and rate on deterministic mock distributions."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from statistics import mean

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from sparsamp_semantic.fixed_length_rrc import (  # noqa: E402
    FixedLengthDecodeError,
    FixedLengthRotationRangeCodec,
    FixedLengthRrcConfig,
)
from sparsamp_semantic.providers.mock import MockProvider  # noqa: E402


KEY = b"fixed-length-rrc-audit-key-v1"
WRONG_KEY = b"fixed-length-rrc-wrong-key!"


def _bits(bit_length: int, seed: int) -> str:
    output = ""
    counter = 0
    while len(output) < bit_length:
        digest = hashlib.sha256(f"{bit_length}:{seed}:{counter}".encode()).digest()
        output += "".join(f"{byte:08b}" for byte in digest)
        counter += 1
    return output[:bit_length]


def _public_budget(payload_bits: int, tag_bits: int, rate_floor: float, slack: int) -> int:
    return math.ceil((payload_bits + tag_bits) / rate_floor) + slack


def audit(
    *,
    samples: int,
    seed_start: int,
    payload_lengths: tuple[int, ...],
    tag_bits: int,
    rate_floor: float,
    slack: int,
) -> dict[str, object]:
    provider = MockProvider()
    rows: list[dict[str, object]] = []
    for payload_bits in payload_lengths:
        total_tokens = _public_budget(payload_bits, tag_bits, rate_floor, slack)
        codec = FixedLengthRotationRangeCodec(
            FixedLengthRrcConfig(
                payload_bits=payload_bits,
                total_tokens=total_tokens,
                tag_bits=tag_bits,
                guard_digits=80,
                failure_mode="cover",
            )
        )
        successes = 0
        exact = 0
        wrong_key_accepts = 0
        prefix_lengths: list[int] = []
        for seed in range(seed_start, seed_start + samples):
            prompt = f"fixed-length-audit-{payload_bits}-{seed}"
            payload = _bits(payload_bits, seed)
            encoded = codec.encode(provider.start(prompt), payload, KEY)
            if not encoded.payload_embedded:
                continue
            successes += 1
            prefix_lengths.append(encoded.embedded_token_count)
            decoded = codec.decode(provider.start(prompt), encoded.token_ids, KEY)
            exact += int(decoded.bits == payload)
            try:
                codec.decode(provider.start(prompt), encoded.token_ids, WRONG_KEY)
            except FixedLengthDecodeError:
                pass
            else:
                wrong_key_accepts += 1

        rows.append(
            {
                "payload_bits": payload_bits,
                "tag_bits": tag_bits,
                "frame_bits": payload_bits + tag_bits,
                "public_total_tokens": total_tokens,
                "samples": samples,
                "successful_embeddings": successes,
                "fallbacks": samples - successes,
                "exact_decodes": exact,
                "wrong_key_accepts": wrong_key_accepts,
                "mean_private_prefix_tokens": mean(prefix_lengths) if prefix_lengths else None,
                "min_private_prefix_tokens": min(prefix_lengths) if prefix_lengths else None,
                "max_private_prefix_tokens": max(prefix_lengths) if prefix_lengths else None,
                "mean_padding_tokens": (
                    total_tokens - mean(prefix_lengths) if prefix_lengths else None
                ),
                "net_bits_per_public_token": payload_bits / total_tokens,
                "framed_bits_per_public_token": (payload_bits + tag_bits) / total_tokens,
                "authentication_overhead_fraction": tag_bits / (payload_bits + tag_bits),
            }
        )
    return {
        "provider": "MockProvider(0.4,0.3,0.2,0.1)",
        "tag_bits": tag_bits,
        "seed_start": seed_start,
        "rate_floor_for_budget": rate_floor,
        "slack_tokens": slack,
        "results": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--payload-bits", type=int, nargs="+", default=[16, 32, 64, 128])
    parser.add_argument("--tag-bits", type=int, default=64)
    parser.add_argument("--rate-floor", type=float, default=1.25)
    parser.add_argument("--slack", type=int, default=8)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    if args.samples < 1:
        raise ValueError("samples must be positive")
    if args.rate_floor <= 0:
        raise ValueError("rate-floor must be positive")
    result = audit(
        samples=args.samples,
        seed_start=args.seed_start,
        payload_lengths=tuple(args.payload_bits),
        tag_bits=args.tag_bits,
        rate_floor=args.rate_floor,
        slack=args.slack,
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
