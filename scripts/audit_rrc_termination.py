"""Compare paper and verified RRC termination on deterministic mock distributions."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from sparsamp_semantic.providers.mock import MockProvider  # noqa: E402
from sparsamp_semantic.rrc import RrcConfig, RotationRangeCodec  # noqa: E402


KEY = b"0123456789abcdef0123456789abcdef"


def _bits(seed: int, bit_length: int) -> str:
    output = bytearray()
    counter = 0
    while len(output) * 8 < bit_length:
        output.extend(hashlib.sha256(f"{seed}:{counter}".encode()).digest())
        counter += 1
    return "".join(f"{value:08b}" for value in output)[:bit_length]


def _evaluate(bit_length: int, samples: int) -> dict[str, object]:
    exact = {"paper": 0, "verified": 0}
    token_counts: dict[str, list[int]] = {"paper": [], "verified": []}
    for seed in range(samples):
        bits = _bits(seed, bit_length)
        prompt = f"rrc-audit-{seed}"
        for mode in ("paper", "verified"):
            codec = RotationRangeCodec(
                RrcConfig(
                    message_bits=bit_length,
                    max_tokens=max(256, bit_length * 4),
                    guard_digits=80,
                    min_precision=16,
                    termination_mode=mode,
                )
            )
            encoded = codec.encode(MockProvider().start(prompt), bits, KEY)
            decoded = codec.decode(MockProvider().start(prompt), encoded.token_ids, KEY)
            exact[mode] += decoded.bits == bits
            token_counts[mode].append(len(encoded.token_ids))
    overhead = [
        verified - paper
        for paper, verified in zip(token_counts["paper"], token_counts["verified"], strict=True)
    ]
    return {
        "bit_length": bit_length,
        "samples": samples,
        "paper_exact": exact["paper"],
        "verified_exact": exact["verified"],
        "paper_mean_tokens": statistics.mean(token_counts["paper"]),
        "verified_mean_tokens": statistics.mean(token_counts["verified"]),
        "mean_extra_tokens": statistics.mean(overhead),
        "max_extra_tokens": max(overhead),
        "fraction_with_extra_tokens": sum(value > 0 for value in overhead) / samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bit-lengths", default="16,32,64,128,256")
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    if args.samples < 1:
        raise ValueError("samples must be positive")
    bit_lengths = [int(value) for value in args.bit_lengths.split(",")]
    if any(value < 1 for value in bit_lengths):
        raise ValueError("bit lengths must be positive")
    result = {
        "provider": "MockProvider(0.4,0.3,0.2,0.1)",
        "samples_per_bit_length": args.samples,
        "results": [_evaluate(bit_length, args.samples) for bit_length in bit_lengths],
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
