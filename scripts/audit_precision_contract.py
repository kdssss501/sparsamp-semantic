"""Compare Decimal and integer probability contracts across model precision modes."""

from __future__ import annotations

import argparse
import gc
import json
import platform
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from math import log, log2
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from sparsamp_semantic.probability_contract import (  # noqa: E402
    SupportStrategy,
    allocate_integer_mass,
    decimal_quantized_probabilities,
    support_feasible_mass_bits,
)
from sparsamp_semantic.providers.huggingface import (  # noqa: E402
    HuggingFaceConfig,
    HuggingFaceProvider,
)


def _snapshot_data(snapshot: Any) -> dict[str, Any]:
    bins_by_token = snapshot.metadata.get("quantized_logit_bins")
    counts_by_token = snapshot.metadata.get("bin_mass_counts")
    probabilities = [float(item.probability) for item in snapshot.candidates]
    return {
        "token_ids": [int(item.token_id) for item in snapshot.candidates],
        "probabilities": probabilities,
        "entropy_bits": -sum(
            probability * log2(probability)
            for probability in probabilities
            if probability > 0
        ),
        "logit_bins": (
            [int(bins_by_token[int(item.token_id)]) for item in snapshot.candidates]
            if bins_by_token is not None
            else None
        ),
        "bin_mass_counts": (
            [int(counts_by_token[int(item.token_id)]) for item in snapshot.candidates]
            if counts_by_token is not None
            else None
        ),
        "source_mass": float(snapshot.source_mass),
        "candidate_count": len(snapshot.candidates),
        "logit_quantization_kl_nats": float(
            snapshot.metadata.get("logit_quantization_kl_nats", 0.0)
        ),
        "logit_quantization_total_variation": float(
            snapshot.metadata.get("logit_quantization_total_variation", 0.0)
        ),
        "max_logit_quantization_error": float(
            snapshot.metadata.get("max_logit_quantization_error", 0.0)
        ),
        "bin_mass_kl_nats": float(snapshot.metadata.get("bin_mass_kl_nats", 0.0)),
        "bin_mass_total_variation": float(
            snapshot.metadata.get("bin_mass_total_variation", 0.0)
        ),
    }


def _top_probability_token_id(snapshot: Any) -> int:
    """Select the probability-rank leader independently of public interval order."""

    return int(min(snapshot.candidates, key=lambda item: item.rank).token_id)


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
        token_id = _top_probability_token_id(snapshot)
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
    snapshot: dict[str, Any],
    *,
    mass_bits: int | None,
    preserve_support: bool,
    support_strategy: SupportStrategy = "base",
) -> tuple[tuple[int, Any], ...]:
    probabilities = snapshot["probabilities"]
    if mass_bits is None:
        values = decimal_quantized_probabilities(probabilities, "1e-15")
    else:
        values = allocate_integer_mass(
            probabilities,
            mass_bits=mass_bits,
            preserve_support=preserve_support,
            support_strategy=support_strategy,
        ).counts
    return tuple(zip(snapshot["token_ids"], values, strict=True))


def _quantization_metrics(
    probabilities: list[float], counts: tuple[int, ...]
) -> dict[str, float]:
    total_probability = sum(probabilities)
    total_mass = sum(counts)
    target = [value / total_probability for value in probabilities]
    implemented = [value / total_mass for value in counts]
    return {
        "forward_kl_nats": sum(
            expected * log(expected / observed)
            for expected, observed in zip(target, implemented, strict=True)
            if expected > 0
        ),
        "total_variation": 0.5
        * sum(
            abs(expected - observed)
            for expected, observed in zip(target, implemented, strict=True)
        ),
    }


def max_internal_cdf_delta(
    reference_token_ids: list[int],
    reference_probabilities: list[float],
    replay_token_ids: list[int],
    replay_probabilities: list[float],
) -> float | None:
    """Return the largest aligned internal CDF drift, or None on support mismatch."""

    if reference_token_ids != replay_token_ids:
        return None
    reference_cdf = 0.0
    replay_cdf = 0.0
    maximum = 0.0
    for reference_probability, replay_probability in zip(
        reference_probabilities[:-1], replay_probabilities[:-1], strict=True
    ):
        reference_cdf += reference_probability
        replay_cdf += replay_probability
        maximum = max(maximum, abs(reference_cdf - replay_cdf))
    return maximum


def interval_lattice_feasible(max_cdf_delta: float | None, block_size: int) -> bool:
    """Check the necessary initial-lattice condition for a guarded sparse block."""

    if block_size < 1:
        raise ValueError("block_size must be positive")
    return max_cdf_delta is not None and max_cdf_delta < 2 ** (-(block_size + 1))


def _adaptive_contract(
    snapshot: dict[str, Any],
    *,
    headroom_bits: int,
    support_strategy: SupportStrategy,
) -> dict[str, Any]:
    candidate_count = int(snapshot.get("candidate_count", len(snapshot["token_ids"])))
    mass_bits = support_feasible_mass_bits(candidate_count, headroom_bits)
    allocation = allocate_integer_mass(
        snapshot["probabilities"],
        mass_bits=mass_bits,
        preserve_support=True,
        support_strategy=support_strategy,
    )
    return {
        "sequence": tuple(zip(snapshot["token_ids"], allocation.counts, strict=True)),
        "mass_bits": mass_bits,
        **_quantization_metrics(snapshot["probabilities"], allocation.counts),
    }


def compare_snapshots(
    reference: dict[str, Any],
    replay: dict[str, Any],
    *,
    mass_bits: tuple[int, ...],
    preserve_support: bool,
    support_headroom_bits: tuple[int, ...] = (),
    support_strategies: tuple[SupportStrategy, ...] = ("base", "waterfill"),
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
    reference_bins = (
        dict(zip(reference["token_ids"], reference["logit_bins"], strict=True))
        if reference.get("logit_bins") is not None
        else None
    )
    replay_bins = (
        dict(zip(replay["token_ids"], replay["logit_bins"], strict=True))
        if replay.get("logit_bins") is not None
        else None
    )
    common_bin_matches = (
        [reference_bins[token_id] == replay_bins[token_id] for token_id in intersection]
        if reference_bins is not None and replay_bins is not None
        else []
    )
    cdf_delta = max_internal_cdf_delta(
        reference["token_ids"],
        reference["probabilities"],
        replay["token_ids"],
        replay["probabilities"],
    )
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
    adaptive_contracts: dict[str, Any] = {}
    for strategy in support_strategies:
        for headroom in support_headroom_bits:
            reference_contract = _adaptive_contract(
                reference,
                headroom_bits=headroom,
                support_strategy=strategy,
            )
            replay_contract = _adaptive_contract(
                replay,
                headroom_bits=headroom,
                support_strategy=strategy,
            )
            adaptive_contracts[f"{strategy}_headroom_{headroom}"] = {
                "exact": (
                    reference_contract["mass_bits"] == replay_contract["mass_bits"]
                    and reference_contract["sequence"] == replay_contract["sequence"]
                ),
                "reference": {
                    name: value
                    for name, value in reference_contract.items()
                    if name != "sequence"
                },
                "replay": {
                    name: value
                    for name, value in replay_contract.items()
                    if name != "sequence"
                },
            }
    return {
        "candidate_order_equal": reference["token_ids"] == replay["token_ids"],
        "candidate_jaccard": len(intersection) / len(union) if union else 1.0,
        "reference_candidate_count": int(
            reference.get("candidate_count", len(reference["token_ids"]))
        ),
        "replay_candidate_count": int(
            replay.get("candidate_count", len(replay["token_ids"]))
        ),
        "max_common_probability_delta": max(common_deltas, default=0.0),
        "source_mass_delta": abs(reference["source_mass"] - replay["source_mass"]),
        "max_internal_cdf_delta": cdf_delta,
        "quantized_bin_sequence_equal": (
            reference["token_ids"] == replay["token_ids"]
            and reference.get("logit_bins") == replay.get("logit_bins")
            if reference_bins is not None and replay_bins is not None
            else None
        ),
        "bin_mass_count_sequence_equal": (
            reference["token_ids"] == replay["token_ids"]
            and reference.get("bin_mass_counts") == replay.get("bin_mass_counts")
            if reference.get("bin_mass_counts") is not None
            and replay.get("bin_mass_counts") is not None
            else None
        ),
        "common_quantized_bin_agreement": (
            sum(common_bin_matches) / len(common_bin_matches)
            if common_bin_matches
            else None
        ),
        "reference_logit_quantization_kl_nats": float(
            reference.get("logit_quantization_kl_nats", 0.0)
        ),
        "reference_logit_quantization_total_variation": float(
            reference.get("logit_quantization_total_variation", 0.0)
        ),
        "reference_max_logit_quantization_error": float(
            reference.get("max_logit_quantization_error", 0.0)
        ),
        "reference_bin_mass_kl_nats": float(reference.get("bin_mass_kl_nats", 0.0)),
        "reference_bin_mass_total_variation": float(
            reference.get("bin_mass_total_variation", 0.0)
        ),
        "contracts_exact": contracts,
        "adaptive_contracts": adaptive_contracts,
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
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--logit-quantum", type=float)
    parser.add_argument("--bin-mass-bits", type=int)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument(
        "--candidate-order", choices=("probability", "token_id"), default="probability"
    )
    parser.add_argument("--mass-bits", type=int, nargs="+", default=[16, 20, 24, 28, 32])
    parser.add_argument("--support-headroom-bits", type=int, nargs="+", default=[])
    parser.add_argument("--guard-block-sizes", type=int, nargs="+", default=[])
    parser.add_argument(
        "--support-strategies",
        choices=("base", "waterfill"),
        nargs="+",
        default=["base", "waterfill"],
    )
    parser.add_argument("--allow-support-loss", action="store_true")
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/R022_gpt2_precision_contract.json")
    )
    args = parser.parse_args()
    if args.tokens < 1:
        raise ValueError("tokens must be positive")
    if any(value < 0 for value in args.support_headroom_bits):
        raise ValueError("support headroom bits must be non-negative")
    if any(value < 1 for value in args.guard_block_sizes):
        raise ValueError("guard block sizes must be positive")
    if args.allow_support_loss and args.support_headroom_bits:
        raise ValueError("support-adaptive contracts require support preservation")

    common = {
        "model_name": args.model,
        "top_p": args.top_p,
        "top_k": args.top_k,
        "logit_quantum": args.logit_quantum,
        "bin_mass_bits": args.bin_mass_bits,
        "temperature": args.temperature,
        "candidate_order": args.candidate_order,
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
            support_headroom_bits=tuple(args.support_headroom_bits),
            support_strategies=tuple(args.support_strategies),
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
    adaptive_names = [
        f"{strategy}_headroom_{headroom}"
        for strategy in args.support_strategies
        for headroom in args.support_headroom_bits
    ]
    adaptive_summary = {}
    for name in adaptive_names:
        values = [item["adaptive_contracts"][name] for item in comparisons]
        references = [value["reference"] for value in values]
        adaptive_summary[name] = {
            "exact_steps": sum(value["exact"] for value in values),
            "same_support_exact_steps": sum(
                value["exact"] and item["candidate_jaccard"] == 1.0
                for value, item in zip(values, comparisons, strict=True)
            ),
            "compared_steps": len(values),
            "reference_mass_bits_mean": (
                sum(value["mass_bits"] for value in references) / len(references)
                if references
                else 0.0
            ),
            "reference_mass_bits_min": min(
                (value["mass_bits"] for value in references), default=None
            ),
            "reference_mass_bits_max": max(
                (value["mass_bits"] for value in references), default=None
            ),
            "reference_forward_kl_nats_mean": (
                sum(value["forward_kl_nats"] for value in references) / len(references)
                if references
                else 0.0
            ),
            "reference_forward_kl_nats_max": max(
                (value["forward_kl_nats"] for value in references), default=0.0
            ),
            "reference_total_variation_mean": (
                sum(value["total_variation"] for value in references) / len(references)
                if references
                else 0.0
            ),
            "reference_total_variation_max": max(
                (value["total_variation"] for value in references), default=0.0
            ),
        }
    structural_summary = {
        "candidate_order_equal_steps": sum(item["candidate_order_equal"] for item in comparisons),
        "candidate_set_equal_steps": sum(item["candidate_jaccard"] == 1.0 for item in comparisons),
        "mean_candidate_jaccard": (
            sum(item["candidate_jaccard"] for item in comparisons) / len(comparisons)
            if comparisons
            else 0.0
        ),
        "reference_candidate_count_mean": (
            sum(item["reference_candidate_count"] for item in comparisons) / len(comparisons)
            if comparisons
            else 0.0
        ),
        "reference_candidate_count_min": min(
            (item["reference_candidate_count"] for item in comparisons), default=None
        ),
        "reference_candidate_count_max": max(
            (item["reference_candidate_count"] for item in comparisons), default=None
        ),
        "reference_entropy_bits_mean": (
            sum(float(snapshot["entropy_bits"]) for snapshot in reference)
            / len(reference)
            if reference
            else 0.0
        ),
        "reference_entropy_bits_min": min(
            (float(snapshot["entropy_bits"]) for snapshot in reference), default=None
        ),
        "reference_entropy_bits_max": max(
            (float(snapshot["entropy_bits"]) for snapshot in reference), default=None
        ),
        "reference_source_mass_mean": (
            sum(float(snapshot["source_mass"]) for snapshot in reference) / len(reference)
            if reference
            else 0.0
        ),
        "reference_source_mass_min": min(
            (float(snapshot["source_mass"]) for snapshot in reference), default=None
        ),
        "quantized_bin_sequence_equal_steps": sum(
            item["quantized_bin_sequence_equal"] is True for item in comparisons
        ),
        "bin_mass_count_sequence_equal_steps": sum(
            item["bin_mass_count_sequence_equal"] is True for item in comparisons
        ),
        "mean_common_quantized_bin_agreement": (
            sum(
                item["common_quantized_bin_agreement"]
                for item in comparisons
                if item["common_quantized_bin_agreement"] is not None
            )
            / sum(
                item["common_quantized_bin_agreement"] is not None
                for item in comparisons
            )
            if any(
                item["common_quantized_bin_agreement"] is not None
                for item in comparisons
            )
            else None
        ),
        "reference_logit_quantization_kl_nats_mean": (
            sum(item["reference_logit_quantization_kl_nats"] for item in comparisons)
            / len(comparisons)
            if comparisons
            else 0.0
        ),
        "reference_logit_quantization_total_variation_mean": (
            sum(
                item["reference_logit_quantization_total_variation"]
                for item in comparisons
            )
            / len(comparisons)
            if comparisons
            else 0.0
        ),
        "reference_max_logit_quantization_error_max": max(
            (item["reference_max_logit_quantization_error"] for item in comparisons),
            default=0.0,
        ),
        "reference_bin_mass_kl_nats_mean": (
            sum(item["reference_bin_mass_kl_nats"] for item in comparisons)
            / len(comparisons)
            if comparisons
            else 0.0
        ),
        "reference_bin_mass_total_variation_mean": (
            sum(item["reference_bin_mass_total_variation"] for item in comparisons)
            / len(comparisons)
            if comparisons
            else 0.0
        ),
        "max_internal_cdf_delta_max": max(
            (
                item["max_internal_cdf_delta"]
                for item in comparisons
                if item["max_internal_cdf_delta"] is not None
            ),
            default=None,
        ),
    }
    guard_feasibility = {
        str(block_size): {
            "feasible_steps": sum(
                interval_lattice_feasible(item["max_internal_cdf_delta"], block_size)
                for item in comparisons
            ),
            "compared_steps": len(comparisons),
            "initial_cdf_error_threshold": 2 ** (-(block_size + 1)),
        }
        for block_size in args.guard_block_sizes
    }
    payload = {
        "schema": "sparsamp-precision-contract-audit-v6",
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
        "adaptive_summary": adaptive_summary,
        "structural_summary": structural_summary,
        "guard_feasibility": guard_feasibility,
        "steps": comparisons,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
