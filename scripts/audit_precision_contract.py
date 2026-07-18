"""Compare Decimal and integer probability contracts across model precision modes."""

from __future__ import annotations

import argparse
import gc
import json
import platform
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from sparsamp_semantic.probability_contract import (  # noqa: E402
    allocate_integer_mass,
    decimal_quantized_probabilities,
)
from sparsamp_semantic.providers.huggingface import (  # noqa: E402
    HuggingFaceConfig,
    HuggingFaceProvider,
)


def _snapshot_data(snapshot: Any) -> dict[str, Any]:
    return {
        "token_ids": [int(item.token_id) for item in snapshot.candidates],
        "probabilities": [float(item.probability) for item in snapshot.candidates],
        "source_mass": float(snapshot.source_mass),
    }


def _collect_reference(
    config: HuggingFaceConfig, prompt: str, token_count: int
) -> tuple[list[dict[str, Any]], list[int]]:
    provider = HuggingFaceProvider(config)
    session = provider.start(prompt)
    snapshots: list[dict[str, Any]] = []
    prefix: list[int] = []
    for _ in range(token_count):
        snapshot = session.next_distribution()
        snapshots.append(_snapshot_data(snapshot))
        token_id = int(snapshot.candidates[0].token_id)
        prefix.append(token_id)
        session.append(token_id)
    return snapshots, prefix


def _collect_replay(
    config: HuggingFaceConfig, prompt: str, prefix: list[int]
) -> tuple[list[dict[str, Any]], int | None]:
    provider = HuggingFaceProvider(config)
    session = provider.start(prompt)
    snapshots: list[dict[str, Any]] = []
    first_missing_step: int | None = None
    for step, token_id in enumerate(prefix):
        snapshot = session.next_distribution()
        snapshots.append(_snapshot_data(snapshot))
        candidate_ids = {int(item.token_id) for item in snapshot.candidates}
        if token_id not in candidate_ids:
            first_missing_step = step
            break
        session.append(token_id)
    return snapshots, first_missing_step


def _contract_sequence(
    snapshot: dict[str, Any], *, mass_bits: int | None, preserve_support: bool
) -> tuple[tuple[int, Any], ...]:
    probabilities = snapshot["probabilities"]
    if mass_bits is None:
        values = decimal_quantized_probabilities(probabilities, "1e-15")
    else:
        values = allocate_integer_mass(
            probabilities,
            mass_bits=mass_bits,
            preserve_support=preserve_support,
        ).counts
    return tuple(zip(snapshot["token_ids"], values, strict=True))


def compare_snapshots(
    reference: dict[str, Any],
    replay: dict[str, Any],
    *,
    mass_bits: tuple[int, ...],
    preserve_support: bool,
) -> dict[str, Any]:
    """Compare one shared-prefix next-token distribution under two precisions."""

    reference_ids = set(reference["token_ids"])
    replay_ids = set(replay["token_ids"])
    union = reference_ids | replay_ids
    intersection = reference_ids & replay_ids
    ref_probabilities = dict(zip(reference["token_ids"], reference["probabilities"], strict=True))
    replay_probabilities = dict(zip(replay["token_ids"], replay["probabilities"], strict=True))
    common_deltas = [
        abs(ref_probabilities[token_id] - replay_probabilities[token_id])
        for token_id in intersection
    ]
    contracts = {
        "decimal_1e-15": _contract_sequence(
            reference, mass_bits=None, preserve_support=preserve_support
        )
        == _contract_sequence(replay, mass_bits=None, preserve_support=preserve_support)
    }
    for bits in mass_bits:
        contracts[f"integer_{bits}"] = _contract_sequence(
            reference, mass_bits=bits, preserve_support=preserve_support
        ) == _contract_sequence(replay, mass_bits=bits, preserve_support=preserve_support)
    return {
        "candidate_order_equal": reference["token_ids"] == replay["token_ids"],
        "candidate_jaccard": len(intersection) / len(union) if union else 1.0,
        "max_common_probability_delta": max(common_deltas, default=0.0),
        "source_mass_delta": abs(reference["source_mass"] - replay["source_mass"]),
        "contracts_exact": contracts,
    }


def _release_cuda() -> None:
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
    parser.add_argument("--prompt", default="Explain why reproducible AI experiments matter.")
    parser.add_argument("--tokens", type=int, default=32)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--reference-dtype", default="float32")
    parser.add_argument("--replay-dtype", default="float16")
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--mass-bits", type=int, nargs="+", default=[16, 20, 24, 28, 32])
    parser.add_argument("--allow-support-loss", action="store_true")
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/R022_gpt2_precision_contract.json")
    )
    args = parser.parse_args()
    if args.tokens < 1:
        raise ValueError("tokens must be positive")

    common = {
        "model_name": args.model,
        "top_p": args.top_p,
        "temperature": args.temperature,
        "device": args.device,
        "allow_eos": False,
        "adaptive_temperature": False,
    }
    reference_config = HuggingFaceConfig(dtype=args.reference_dtype, **common)
    replay_config = HuggingFaceConfig(dtype=args.replay_dtype, **common)
    reference, prefix = _collect_reference(reference_config, args.prompt, args.tokens)
    _release_cuda()
    replay, first_missing_step = _collect_replay(replay_config, args.prompt, prefix)
    comparisons = [
        compare_snapshots(
            expected,
            observed,
            mass_bits=tuple(args.mass_bits),
            preserve_support=not args.allow_support_loss,
        )
        for expected, observed in zip(reference, replay, strict=False)
    ]
    contract_names = ["decimal_1e-15", *(f"integer_{bits}" for bits in args.mass_bits)]
    summary = {
        name: {
            "exact_steps": sum(item["contracts_exact"][name] for item in comparisons),
            "compared_steps": len(comparisons),
        }
        for name in contract_names
    }
    payload = {
        "schema": "sparsamp-precision-contract-audit-v1",
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "reference": asdict(reference_config),
        "replay": asdict(replay_config),
        "prompt": args.prompt,
        "requested_tokens": args.tokens,
        "compared_steps": len(comparisons),
        "first_missing_prefix_step": first_missing_step,
        "preserve_support": not args.allow_support_loss,
        "summary": summary,
        "steps": comparisons,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
