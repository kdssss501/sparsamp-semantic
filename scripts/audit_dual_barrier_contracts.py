"""R055 resumable FP16/BF16 contract-transition trace on saved R044 paths."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.audit_replay_certificate import (  # noqa: E402
    archive_existing,
    config_signature,
    result_signature as replay_result_signature,
    write_report,
)
from sparsamp_semantic.conformal_replay import contract_boundary_margin  # noqa: E402
from sparsamp_semantic.contract_transition import (  # noqa: E402
    classify_contract_transition,
    rank_cutoff_gap,
)
from sparsamp_semantic.providers.huggingface import (  # noqa: E402
    HuggingFaceConfig,
    HuggingFaceProvider,
)
from sparsamp_semantic.replay_certificate import (  # noqa: E402
    ReplayContractConfig,
    contract_decision,
    decision_context,
)
from sparsamp_semantic.replay_package import canonical_signature  # noqa: E402
from sparsamp_semantic.types import DistributionSnapshot  # noqa: E402


SCHEMA = "sparsamp-r055-dual-barrier-trace-v1"
SOURCE_SCHEMA = "sparsamp-r041-replay-certificate-v1"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_source(path: Path) -> dict[str, Any]:
    source = json.loads(path.read_text(encoding="utf-8"))
    if source.get("schema") != SOURCE_SCHEMA or source.get("phase") != "completed":
        raise ValueError("source must be a completed R041-family replay report")
    config = source.get("experiment_config")
    if not isinstance(config, dict) or source.get("experiment_signature") != config_signature(config):
        raise ValueError("source experiment signature is invalid")
    rows = source.get("rows")
    if not isinstance(rows, list) or source.get("result_signature") != replay_result_signature(rows):
        raise ValueError("source result signature is invalid")
    return source


def trial_key(row: dict[str, Any]) -> tuple[int, int]:
    return int(row["prompt_index"]), int(row["seed"])


def select_source_rows(
    source: dict[str, Any], *, prompt_indices: Iterable[int], seeds: Iterable[int]
) -> list[dict[str, Any]]:
    prompts = tuple(sorted(set(int(value) for value in prompt_indices)))
    selected_seeds = tuple(sorted(set(int(value) for value in seeds)))
    if not prompts or not selected_seeds or any(value < 0 for value in (*prompts, *selected_seeds)):
        raise ValueError("prompt indices and seeds must be non-empty and non-negative")
    expected = {(prompt, seed) for prompt in prompts for seed in selected_seeds}
    rows = [
        row
        for row in source["rows"]
        if str(row["policy"]) == "seeded" and trial_key(row) in expected
    ]
    keys = [trial_key(row) for row in rows]
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError("source does not contain the exact requested trial matrix")
    return sorted(rows, key=trial_key)


def replay_config(source: dict[str, Any], seed: int) -> ReplayContractConfig:
    config = source["experiment_config"]
    return ReplayContractConfig(
        contract_top_k=int(config["contract_top_k"]),
        logit_quantum=float(config["logit_quantum"]),
        mass_bits=int(config["mass_bits"]),
        temperature=float(config["temperature"]),
        public_seed=int(seed),
    )


def provider_config(source: dict[str, Any], dtype: str) -> HuggingFaceConfig:
    config = source["experiment_config"]
    return HuggingFaceConfig(
        model_name=str(config["model"]),
        device=str(config["device"]),
        dtype=dtype,
        top_p=1.0,
        top_k=int(config["envelope_top_k"]),
        logit_quantum=float(config["logit_quantum"]),
        temperature=float(config["temperature"]),
        precision_context="portable",
        allow_eos=False,
        adaptive_temperature=False,
        system_prompt=str(config["system_prompt"]),
    )


def snapshot_record(
    snapshot: DistributionSnapshot,
    *,
    step: int,
    context: bytes,
    config: ReplayContractConfig,
) -> dict[str, Any]:
    ranked = sorted(snapshot.candidates, key=lambda candidate: int(candidate.rank))
    bins_raw = snapshot.metadata.get("quantized_logit_bins")
    if not isinstance(bins_raw, dict):
        raise ValueError("snapshot does not expose quantized logit bins")
    bins = {int(token_id): int(value) for token_id, value in bins_raw.items()}
    envelope_ids = [int(candidate.token_id) for candidate in ranked]
    envelope_bins = [bins[token_id] for token_id in envelope_ids]
    decision = contract_decision(snapshot, step, context, config, policy="seeded")
    return {
        "step": step,
        "envelope_token_ids": envelope_ids,
        "envelope_logit_bins": envelope_bins,
        "rank2_rank3_gap_bins": rank_cutoff_gap(envelope_bins, cutoff=2),
        "contract_token_ids": list(decision.token_ids),
        "contract_counts": list(decision.counts),
        "decision_token_id": int(decision.token_id),
        "source_mass": float(snapshot.source_mass),
        "base_entropy_bits": float(snapshot.metadata["base_entropy_bits"]),
        "max_logit_quantization_error": float(
            snapshot.metadata["max_logit_quantization_error"]
        ),
    }


def trace_saved_path(
    provider: HuggingFaceProvider,
    source: dict[str, Any],
    row: dict[str, Any],
) -> dict[str, Any]:
    prompt = str(row["prompt"])
    tokens = [int(value) for value in row["reference_token_ids"]]
    config = replay_config(source, int(row["seed"]))
    context = decision_context(str(source["experiment_config"]["model"]), prompt, config)
    session = provider.start(prompt)
    steps: list[dict[str, Any]] = []
    rejection_step: int | None = None
    for step, reference_token in enumerate(tokens):
        snapshot = session.next_distribution()
        record = snapshot_record(snapshot, step=step, context=context, config=config)
        envelope = set(int(value) for value in record["envelope_token_ids"])
        record["reference_token_rank"] = next(
            (
                rank
                for rank, token_id in enumerate(record["envelope_token_ids"])
                if int(token_id) == reference_token
            ),
            None,
        )
        steps.append(record)
        if reference_token not in envelope:
            rejection_step = step
            break
        session.append(reference_token)
    return {
        "trace_completed": rejection_step is None and len(steps) == len(tokens),
        "token_count": len(tokens),
        "traced_steps": len(steps),
        "reference_rejection_step": rejection_step,
        "steps": steps,
    }


def reference_trace_matches_source(
    source_row: dict[str, Any], reference_trace: dict[str, Any]
) -> bool:
    """Require exact regeneration of every saved reference contract and choice."""

    if not bool(reference_trace["trace_completed"]):
        return False
    steps = reference_trace["steps"]
    saved_contracts = source_row["reference_contracts"]
    saved_tokens = [int(value) for value in source_row["reference_token_ids"]]
    if len(steps) != len(saved_contracts) or len(steps) != len(saved_tokens):
        return False
    return all(
        [int(value) for value in step["contract_token_ids"]]
        == [int(value) for value in saved["token_ids"]]
        and [int(value) for value in step["contract_counts"]]
        == [int(value) for value in saved["counts"]]
        and int(step["decision_token_id"]) == token
        for step, saved, token in zip(steps, saved_contracts, saved_tokens, strict=True)
    )


def _maximum_common_bin_shift(reference: dict[str, Any], target: dict[str, Any]) -> int:
    reference_bins = dict(
        zip(reference["envelope_token_ids"], reference["envelope_logit_bins"], strict=True)
    )
    target_bins = dict(
        zip(target["envelope_token_ids"], target["envelope_logit_bins"], strict=True)
    )
    common = set(reference_bins) & set(target_bins)
    return max((abs(int(reference_bins[token]) - int(target_bins[token])) for token in common), default=0)


def compare_traces(
    source: dict[str, Any],
    source_row: dict[str, Any],
    reference_trace: dict[str, Any],
    target_trace: dict[str, Any],
) -> dict[str, Any]:
    reference_steps = reference_trace["steps"]
    target_steps = target_trace["steps"]
    common_steps = min(len(reference_steps), len(target_steps))
    config = replay_config(source, int(source_row["seed"]))
    context = decision_context(
        str(source["experiment_config"]["model"]), str(source_row["prompt"]), config
    )
    saved_contracts = source_row["reference_contracts"]
    saved_tokens = [int(value) for value in source_row["reference_token_ids"]]
    saved_corrections = {int(item["step"]) for item in source_row["corrections"]}
    steps: list[dict[str, Any]] = []
    regenerated_reference_exact = True
    target_corrections: set[int] = set()
    for step in range(common_steps):
        reference = reference_steps[step]
        target = target_steps[step]
        saved = saved_contracts[step]
        reference_contract_exact = (
            [int(value) for value in reference["contract_token_ids"]]
            == [int(value) for value in saved["token_ids"]]
            and [int(value) for value in reference["contract_counts"]]
            == [int(value) for value in saved["counts"]]
            and int(reference["decision_token_id"]) == saved_tokens[step]
        )
        regenerated_reference_exact &= reference_contract_exact
        transition = classify_contract_transition(
            reference_token_ids=reference["contract_token_ids"],
            reference_counts=reference["contract_counts"],
            reference_choice=int(reference["decision_token_id"]),
            target_token_ids=target["contract_token_ids"],
            target_counts=target["contract_counts"],
            target_choice=int(target["decision_token_id"]),
        )
        decision_flip = int(target["decision_token_id"]) != saved_tokens[step]
        if decision_flip:
            target_corrections.add(step)
        margin = contract_boundary_margin(
            saved["counts"], step=step, context=context, public_seed=config.public_seed
        )
        steps.append(
            {
                "step": step,
                "reference_contract_exact": reference_contract_exact,
                "support_exact": transition.support_exact,
                "counts_exact": transition.counts_exact,
                "decision_flip": decision_flip,
                "cause": transition.cause,
                "support_overlap": transition.support_overlap,
                "same_support_count_tv": (
                    float(transition.count_total_variation)
                    if transition.count_total_variation is not None
                    else None
                ),
                "reference_rank2_rank3_gap_bins": int(
                    reference["rank2_rank3_gap_bins"]
                ),
                "reference_boundary_slack": margin.minimum_slack,
                "common_envelope_max_bin_shift": _maximum_common_bin_shift(
                    reference, target
                ),
            }
        )
    source_correction_match = target_corrections == saved_corrections
    trace_complete = (
        bool(reference_trace["trace_completed"])
        and bool(target_trace["trace_completed"])
        and common_steps == len(saved_tokens)
    )
    causes = [str(item["cause"]) for item in steps if bool(item["decision_flip"])]
    return {
        "trace_complete": trace_complete,
        "regenerated_reference_exact": regenerated_reference_exact,
        "source_correction_match": source_correction_match,
        "source_correction_steps": sorted(saved_corrections),
        "target_correction_steps": sorted(target_corrections),
        "valid": trace_complete and regenerated_reference_exact and source_correction_match,
        "steps": steps,
        "decision_flips": len(causes),
        "support_flips": causes.count("support_flip"),
        "mass_flips": causes.count("mass_flip"),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    comparisons = [row["comparison"] for row in rows if "comparison" in row]
    steps = [step for item in comparisons for step in item["steps"]]
    flips = [step for step in steps if bool(step["decision_flip"])]
    same_support_tvs = [
        float(step["same_support_count_tv"])
        for step in steps
        if step["same_support_count_tv"] is not None
    ]
    return {
        "trials": len(rows),
        "compared_trials": len(comparisons),
        "valid_trials": sum(bool(item["valid"]) for item in comparisons),
        "reference_exact_trials": sum(
            bool(item["regenerated_reference_exact"]) for item in comparisons
        ),
        "source_correction_match_trials": sum(
            bool(item["source_correction_match"]) for item in comparisons
        ),
        "compared_steps": len(steps),
        "decision_flips": len(flips),
        "support_flips": sum(step["cause"] == "support_flip" for step in flips),
        "mass_flips": sum(step["cause"] == "mass_flip" for step in flips),
        "support_change_steps": sum(not bool(step["support_exact"]) for step in steps),
        "same_support_count_change_steps": sum(
            bool(step["support_exact"]) and not bool(step["counts_exact"])
            for step in steps
        ),
        "mean_same_support_count_tv": mean(same_support_tvs) if same_support_tvs else None,
        "max_same_support_count_tv": max(same_support_tvs, default=None),
    }


def experiment_config(
    source_path: Path,
    source: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    run_label: str,
) -> dict[str, Any]:
    config = source["experiment_config"]
    return {
        "schema": SCHEMA,
        "run_label": run_label,
        "source_path": str(source_path),
        "source_sha256": file_sha256(source_path),
        "source_result_signature": source["result_signature"],
        "model": config["model"],
        "device": config["device"],
        "reference_dtype": config["reference_dtype"],
        "target_dtype": config["replay_dtype"],
        "envelope_top_k": config["envelope_top_k"],
        "contract_top_k": config["contract_top_k"],
        "logit_quantum": config["logit_quantum"],
        "mass_bits": config["mass_bits"],
        "temperature": config["temperature"],
        "trial_keys": [list(trial_key(row)) for row in rows],
    }


def initial_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "prompt_index": int(row["prompt_index"]),
            "seed": int(row["seed"]),
            "prompt": str(row["prompt"]),
            "token_count": int(row["token_count"]),
        }
        for row in rows
    ]


def build_report(config: dict[str, Any], rows: list[dict[str, Any]], phase: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "run_label": config["run_label"],
        "phase": phase,
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "experiment_config": config,
        "experiment_signature": config_signature(config),
        "progress": {
            "reference_trials": sum("reference_trace" in row for row in rows),
            "target_trials": sum("target_trace" in row for row in rows),
            "compared_trials": sum("comparison" in row for row in rows),
            "expected_trials": len(rows),
        },
        "summary": summarize(rows),
        "result_signature": canonical_signature({"rows": rows}),
        "rows": rows,
    }


def load_checkpoint(path: Path, expected_config: dict[str, Any]) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("experiment_config") != expected_config:
        raise ValueError("checkpoint experiment configuration mismatch")
    if report.get("experiment_signature") != config_signature(expected_config):
        raise ValueError("checkpoint experiment signature is invalid")
    rows = report.get("rows")
    if not isinstance(rows, list):
        raise ValueError("checkpoint rows are invalid")
    keys = [trial_key(row) for row in rows]
    expected = {tuple(value) for value in expected_config["trial_keys"]}
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError("checkpoint trial matrix is invalid")
    return rows


def release_cuda() -> None:
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


def run_phase(
    *,
    phase_name: str,
    dtype: str,
    source: dict[str, Any],
    source_rows: dict[tuple[int, int], dict[str, Any]],
    rows: list[dict[str, Any]],
    config: dict[str, Any],
    output: Path,
) -> None:
    trace_key = f"{phase_name}_trace"
    pending = [row for row in rows if trace_key not in row]
    if not pending:
        return
    provider = HuggingFaceProvider(provider_config(source, dtype))
    for row in pending:
        source_row = source_rows[trial_key(row)]
        row[trace_key] = trace_saved_path(provider, source, source_row)
        if phase_name == "reference":
            row["reference_regenerated_exact"] = reference_trace_matches_source(
                source_row, row[trace_key]
            )
        elif "reference_trace" in row:
            row["comparison"] = compare_traces(
                source, source_row, row["reference_trace"], row[trace_key]
            )
        write_report(output, build_report(config, rows, f"partial_{phase_name}"))
    del provider
    release_cuda()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("outputs/R044_qwen_replay_scale.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/R055_qwen_dual_barrier_trace.json"))
    parser.add_argument("--run-label", default="R055")
    parser.add_argument("--prompt-indices", nargs="+", type=int, default=list(range(20)))
    parser.add_argument("--seeds", nargs="+", type=int, default=[0])
    parser.add_argument("--phase", choices=("both", "reference", "target"), default="both")
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()

    source = load_source(args.source)
    selected = select_source_rows(
        source, prompt_indices=args.prompt_indices, seeds=args.seeds
    )
    config = experiment_config(args.source, source, selected, run_label=args.run_label)
    if args.fresh:
        archive_existing(args.output)
    rows = [] if args.fresh else load_checkpoint(args.output, config)
    if not rows:
        rows = initial_rows(selected)
        write_report(args.output, build_report(config, rows, "initialized"))
    source_rows = {trial_key(row): row for row in selected}

    if args.phase in {"both", "reference"}:
        run_phase(
            phase_name="reference",
            dtype=str(config["reference_dtype"]),
            source=source,
            source_rows=source_rows,
            rows=rows,
            config=config,
            output=args.output,
        )
        invalid_reference = [
            trial_key(row) for row in rows if not bool(row.get("reference_regenerated_exact"))
        ]
        if invalid_reference:
            raise RuntimeError(
                f"reference regeneration gate failed for {invalid_reference}; target phase stopped"
            )
    if args.phase in {"both", "target"}:
        if any("reference_trace" not in row for row in rows):
            raise ValueError("target phase requires completed reference traces")
        run_phase(
            phase_name="target",
            dtype=str(config["target_dtype"]),
            source=source,
            source_rows=source_rows,
            rows=rows,
            config=config,
            output=args.output,
        )

    complete = all("comparison" in row for row in rows)
    report = build_report(config, rows, "completed" if complete else f"partial_{args.phase}")
    write_report(args.output, report)
    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
