"""R036-D3 oracle coverage audit for bounded cross-precision contract lists."""

from __future__ import annotations

import argparse
import gc
import json
import math
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.audit_bin_mass_failure_modes import file_sha256, load_source_report  # noqa: E402
from scripts.audit_byte_sliced_messages import (  # noqa: E402
    archive_existing_report,
    config_signature,
    trial_key,
    write_report,
)
from sparsamp_semantic.probability_contract import allocate_logit_bin_mass  # noqa: E402
from sparsamp_semantic.providers.base import ProviderSession  # noqa: E402
from sparsamp_semantic.providers.huggingface import (  # noqa: E402
    HuggingFaceConfig,
    HuggingFaceProvider,
)
from sparsamp_semantic.types import DistributionSnapshot  # noqa: E402

SCHEMA = "sparsamp-r036d3-contract-list-oracle-v1"


def config_name(top_k: int, radius: int) -> str:
    return f"K={top_k},r={radius}"


def beam_upper_bound(top_k: int, radius: int) -> int:
    return math.comb(top_k, 2) * (2 * radius + 1) ** 2


def _ranked(snapshot: DistributionSnapshot) -> list[Any]:
    return sorted(snapshot.candidates, key=lambda candidate: int(candidate.rank))


def _bins(snapshot: DistributionSnapshot) -> dict[int, int]:
    values = snapshot.metadata.get("quantized_logit_bins")
    if not isinstance(values, dict):
        raise ValueError("snapshot does not expose quantized_logit_bins")
    return {int(token_id): int(value) for token_id, value in values.items()}


def trace_oracle(
    reference: ProviderSession,
    replay: ProviderSession,
    token_ids: list[int],
    top_ks: list[int],
    radii: list[int],
    quantum: float,
    temperature: float,
    mass_bits: int,
) -> dict[str, Any]:
    max_k = max(top_ks)
    covered = {config_name(k, r): True for k in top_ks for r in radii}
    steps: list[dict[str, Any]] = []
    appended = 0
    max_min_k = 2
    max_radius = 0
    for step, observed in enumerate(token_ids):
        ref_snapshot = reference.next_distribution()
        replay_snapshot = replay.next_distribution()
        ref_ranked = _ranked(ref_snapshot)
        replay_ranked = _ranked(replay_snapshot)
        if len(ref_ranked) < 2 or len(replay_ranked) < max_k:
            raise ValueError("provider returned fewer candidates than requested")
        ref_bins = _bins(ref_snapshot)
        replay_bins = _bins(replay_snapshot)
        ref_support_ranked = [int(candidate.token_id) for candidate in ref_ranked[:2]]
        ref_support = sorted(ref_support_ranked)
        replay_ranks = {
            int(candidate.token_id): rank + 1 for rank, candidate in enumerate(replay_ranked)
        }
        support_ranks = [replay_ranks.get(token_id) for token_id in ref_support]
        min_k = max(support_ranks) if all(rank is not None for rank in support_ranks) else None
        radius = (
            max(abs(ref_bins[token_id] - replay_bins[token_id]) for token_id in ref_support)
            if min_k is not None
            else None
        )
        if min_k is not None:
            max_min_k = max(max_min_k, int(min_k))
        if radius is not None:
            max_radius = max(max_radius, int(radius))
        for k in top_ks:
            for r in radii:
                covered[config_name(k, r)] &= (
                    min_k is not None and int(min_k) <= k and radius is not None and radius <= r
                )
        allocation = allocate_logit_bin_mass(
            ref_support,
            [ref_bins[token_id] for token_id in ref_support],
            quantum=quantum,
            temperature=temperature,
            mass_bits=mass_bits,
        )
        observed_rank = replay_ranks.get(observed)
        steps.append(
            {
                "step": step,
                "reference_support": ref_support,
                "reference_bins": [ref_bins[token_id] for token_id in ref_support],
                "reference_counts": list(allocation.counts),
                "replay_support_ranks": support_ranks,
                "minimum_top_k": min_k,
                "minimum_bin_radius": radius,
                "observed_replay_rank": observed_rank,
            }
        )
        if observed_rank is None:
            break
        reference.append(observed)
        replay.append(observed)
        appended += 1
    full_trace = appended == len(token_ids)
    if not full_trace:
        covered = {name: False for name in covered}
    return {
        "token_count": len(token_ids),
        "appended_tokens": appended,
        "full_trace": full_trace,
        "trajectory_minimum_top_k": max_min_k if full_trace else None,
        "trajectory_minimum_bin_radius": max_radius if full_trace else None,
        "covered_configs": [name for name, value in covered.items() if value],
        "coverage": covered,
        "steps": steps,
    }


def summarize(
    rows: list[dict[str, Any]], top_ks: list[int], radii: list[int]
) -> dict[str, Any]:
    variants: dict[str, Any] = {}
    eligible: list[tuple[int, int, int, str]] = []
    for variant in sorted({str(row["variant"]) for row in rows}):
        selected = [row for row in rows if row["variant"] == variant]
        grid: dict[str, Any] = {}
        for k in top_ks:
            for radius in radii:
                name = config_name(k, radius)
                successes = sum(bool(row.get("oracle_trace", {}).get("coverage", {}).get(name)) for row in selected)
                grid[name] = {
                    "covered_trials": successes,
                    "trials": len(selected),
                    "beam_upper_bound": beam_upper_bound(k, radius),
                    "oracle_go": len(selected) == 6 and successes >= 5,
                }
                if grid[name]["oracle_go"]:
                    eligible.append((beam_upper_bound(k, radius), k, radius, variant))
        variants[variant] = {
            "trials": len(selected),
            "full_top_k_trace_trials": sum(bool(row.get("oracle_trace", {}).get("full_trace")) for row in selected),
            "grid": grid,
        }
    eligible.sort()
    return {
        "variants": variants,
        "overall_oracle_go": bool(eligible),
        "selected": (
            {"variant": eligible[0][3], "top_k": eligible[0][1], "bin_radius": eligible[0][2], "beam_upper_bound": eligible[0][0]}
            if eligible
            else None
        ),
    }


def experiment_config(args: Any, source: dict[str, Any]) -> dict[str, Any]:
    source_config = source["experiment_config"]
    return {
        "schema": SCHEMA,
        "run_label": args.run_label,
        "source_path": str(args.input),
        "source_sha256": file_sha256(args.input),
        "source_experiment_signature": source["experiment_signature"],
        "model": source_config["model"],
        "reference_dtype": source_config["reference_dtype"],
        "replay_dtype": source_config["replay_dtype"],
        "top_ks": args.top_k,
        "bin_radii": args.bin_radius,
        "logit_quantum": source_config["logit_quantum"],
        "temperature": source_config["temperature"],
        "bin_mass_bits": source_config["bin_mass_bits"],
        "trial_keys": source_config["trial_keys"],
    }


def build_report(args: Any, source: dict[str, Any], rows: list[dict[str, Any]], phase: str) -> dict[str, Any]:
    config = experiment_config(args, source)
    return {
        "schema": SCHEMA,
        "run_label": args.run_label,
        "phase": phase,
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "experiment_config": config,
        "experiment_signature": config_signature(config),
        "progress": {"completed_trials": len(rows), "expected_trials": len(source["rows"])},
        "summary": summarize(rows, args.top_k, args.bin_radius),
        "rows": rows,
    }


def load_rows(path: Path, expected: dict[str, Any]) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("experiment_config") != expected or report.get("experiment_signature") != config_signature(expected):
        raise ValueError("checkpoint configuration/signature mismatch; use another output or --fresh")
    rows = report.get("rows")
    if not isinstance(rows, list):
        raise ValueError("checkpoint rows must be a list")
    keys = [trial_key(row) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("checkpoint contains duplicate trials")
    return rows


def provider_config(source: dict[str, Any], dtype: str, top_k: int) -> HuggingFaceConfig:
    return HuggingFaceConfig(
        model_name=source["model"], device=source["device"], dtype=dtype,
        top_p=1.0, top_k=top_k, logit_quantum=source["logit_quantum"],
        bin_mass_bits=source["bin_mass_bits"], temperature=source["temperature"],
        candidate_order="token_id", precision_context="portable", allow_eos=False,
        adaptive_temperature=False,
    )


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
    parser.add_argument("--input", type=Path, default=Path("outputs/R036_gpt2_bin_mass_raw_bytes.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/R036D3_contract_list_oracle.json"))
    parser.add_argument("--run-label", default="R036-D3")
    parser.add_argument("--top-k", type=int, nargs="+", default=[2, 4, 8, 16])
    parser.add_argument("--bin-radius", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()
    if sorted(set(args.top_k)) != args.top_k or min(args.top_k) < 2:
        raise ValueError("top-k values must be unique, sorted, and >=2")
    if sorted(set(args.bin_radius)) != args.bin_radius or min(args.bin_radius) < 0:
        raise ValueError("bin-radius values must be unique, sorted, and non-negative")
    source = load_source_report(args.input)
    config = experiment_config(args, source)
    rows = [] if args.fresh else load_rows(args.output, config)
    if args.fresh:
        archive_existing_report(args.output)
    if args.fresh or not args.output.exists():
        write_report(args.output, build_report(args, source, rows, "initialized"))
    done = {trial_key(row) for row in rows}
    pending = [row for row in source["rows"] if trial_key(row) not in done]
    if pending:
        base = source["experiment_config"]
        max_k = max(args.top_k)
        ref_provider = HuggingFaceProvider(provider_config(base, base["reference_dtype"], max_k))
        replay_provider = HuggingFaceProvider(provider_config(base, base["replay_dtype"], max_k))
        for source_row in pending:
            row = {key: source_row[key] for key in ("prompt_index", "payload_seed", "window_tokens", "parity_bytes", "variant")}
            try:
                row["oracle_trace"] = trace_oracle(
                    ref_provider.start(str(source_row["prompt"])),
                    replay_provider.start(str(source_row["prompt"])),
                    [int(token) for token in source_row["token_ids"]],
                    args.top_k, args.bin_radius, float(base["logit_quantum"]),
                    float(base["temperature"]), int(base["bin_mass_bits"]),
                )
            except Exception as error:  # noqa: BLE001
                row["oracle_error"] = {"type": type(error).__name__, "message": str(error)}
            rows.append(row)
            write_report(args.output, build_report(args, source, rows, "partial"))
        del ref_provider, replay_provider
        release_cuda()
    report = build_report(args, source, rows, "completed")
    write_report(args.output, report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
