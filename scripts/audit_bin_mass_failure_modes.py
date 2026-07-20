"""R036-D1 diagnose fixed-window convergence and cross-precision contract failure."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import platform
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, median
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from scripts.audit_byte_sliced_messages import (  # noqa: E402
    KEY,
    archive_existing_report,
    config_signature,
    trial_key,
    write_report,
)
from sparsamp_semantic.byte_sliced import ByteSlicedCodec, ByteSlicedConfig  # noqa: E402
from sparsamp_semantic.providers.base import ProviderSession  # noqa: E402
from sparsamp_semantic.providers.huggingface import (  # noqa: E402
    HuggingFaceConfig,
    HuggingFaceProvider,
)
from sparsamp_semantic.types import DistributionSnapshot  # noqa: E402


SCHEMA = "sparsamp-r036d1-bin-mass-failure-diagnostic-v1"
SOURCE_SCHEMA = "sparsamp-r036-bin-mass-raw-byte-pilot-v1"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_source_report(path: Path) -> dict[str, Any]:
    """Load a completed, internally signed R036 report."""

    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("schema") != SOURCE_SCHEMA:
        raise ValueError("source report has an unsupported schema")
    if report.get("phase") != "completed":
        raise ValueError("source report must be completed")
    config = report.get("experiment_config")
    if not isinstance(config, dict):
        raise ValueError("source report is missing experiment_config")
    if report.get("experiment_signature") != config_signature(config):
        raise ValueError("source report experiment_signature is invalid")
    rows = report.get("rows")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("source report rows must be a list of objects")
    keys = [trial_key(row) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("source report contains duplicate trial identities")
    expected = {tuple(int(value) for value in key) for key in config["trial_keys"]}
    if set(keys) != expected:
        raise ValueError("source report does not contain the configured trial matrix")
    return report


def _integer_counts(snapshot: DistributionSnapshot) -> dict[int, int]:
    counts = snapshot.metadata.get("bin_mass_counts")
    if not isinstance(counts, dict):
        raise ValueError("snapshot does not expose bin_mass_counts")
    result = {int(token_id): int(count) for token_id, count in counts.items()}
    support = {int(candidate.token_id) for candidate in snapshot.candidates}
    if set(result) != support:
        raise ValueError("bin_mass_counts do not match candidate support")
    return result


def trace_contract(
    reference_session: ProviderSession,
    replay_session: ProviderSession,
    token_ids: list[int] | tuple[int, ...],
) -> dict[str, Any]:
    """Trace the shared support/count contract until the observed prefix is rejected."""

    first_support_divergence: int | None = None
    first_count_divergence: int | None = None
    first_reference_rejection: int | None = None
    first_replay_rejection: int | None = None
    appended_tokens = 0
    events: list[dict[str, Any]] = []
    max_count_tv = 0.0

    for step, observed in enumerate(token_ids):
        reference = reference_session.next_distribution()
        replay = replay_session.next_distribution()
        reference_support = tuple(int(candidate.token_id) for candidate in reference.candidates)
        replay_support = tuple(int(candidate.token_id) for candidate in replay.candidates)
        reference_counts = _integer_counts(reference)
        replay_counts = _integer_counts(replay)
        support_exact = reference_support == replay_support
        counts_exact = reference_counts == replay_counts
        if not support_exact and first_support_divergence is None:
            first_support_divergence = step
        if not counts_exact and first_count_divergence is None:
            first_count_divergence = step

        union = set(reference_counts) | set(replay_counts)
        count_l1 = sum(
            abs(reference_counts.get(token_id, 0) - replay_counts.get(token_id, 0))
            for token_id in union
        )
        total_mass = max(sum(reference_counts.values()), sum(replay_counts.values()))
        count_tv = count_l1 / (2 * total_mass) if total_mass else 0.0
        max_count_tv = max(max_count_tv, count_tv)
        observed_in_reference = observed in reference_counts
        observed_in_replay = observed in replay_counts
        if not observed_in_reference and first_reference_rejection is None:
            first_reference_rejection = step
        if not observed_in_replay and first_replay_rejection is None:
            first_replay_rejection = step
        if not support_exact or not counts_exact or not observed_in_reference or not observed_in_replay:
            events.append(
                {
                    "step": step,
                    "observed_token_id": observed,
                    "reference_support": list(reference_support),
                    "replay_support": list(replay_support),
                    "support_exact": support_exact,
                    "counts_exact": counts_exact,
                    "count_l1_units": count_l1,
                    "count_total_variation": count_tv,
                    "observed_in_reference": observed_in_reference,
                    "observed_in_replay": observed_in_replay,
                    "source_mass_absolute_difference": abs(
                        float(reference.source_mass) - float(replay.source_mass)
                    ),
                }
            )
        if not observed_in_reference or not observed_in_replay:
            break
        reference_session.append(observed)
        replay_session.append(observed)
        appended_tokens += 1

    full_trace = appended_tokens == len(token_ids)
    return {
        "token_count": len(token_ids),
        "appended_tokens": appended_tokens,
        "trace_fraction": appended_tokens / len(token_ids) if token_ids else 1.0,
        "first_support_divergence_step": first_support_divergence,
        "first_count_divergence_step": first_count_divergence,
        "first_reference_rejection_step": first_reference_rejection,
        "first_replay_rejection_step": first_replay_rejection,
        "full_trace": full_trace,
        "full_support_agreement": full_trace and first_support_divergence is None,
        "full_count_agreement": full_trace and first_count_divergence is None,
        "max_count_total_variation": max_count_tv,
        "events": events,
    }


def _payload_matches(payload: bytes | None, expected_sha256: str) -> bool:
    return payload is not None and hashlib.sha256(payload).hexdigest() == expected_sha256


def _record_dicts(records: tuple[Any, ...]) -> list[dict[str, Any]]:
    return [asdict(record) for record in records]


def _singleton_cdf(records: list[dict[str, Any]], window_tokens: int) -> list[float]:
    if not records:
        return [0.0] * window_tokens
    return [
        sum(
            bool(record["completed"])
            and record.get("singleton_step") is not None
            and int(record["singleton_step"]) <= step
            for record in records
        )
        / len(records)
        for step in range(window_tokens)
    ]


def summarize(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for variant in sorted({str(row["variant"]) for row in rows}):
        selected = [row for row in rows if row["variant"] == variant]
        same_records = [
            record for row in selected for record in row.get("same_precision_records", [])
        ]
        singleton_tokens = [
            int(record["singleton_step"]) + 1
            for record in same_records
            if bool(record.get("completed")) and record.get("singleton_step") is not None
        ]
        support_divergences = [
            int(row["contract_trace"]["first_support_divergence_step"])
            for row in selected
            if row.get("contract_trace", {}).get("first_support_divergence_step") is not None
        ]
        count_divergences = [
            int(row["contract_trace"]["first_count_divergence_step"])
            for row in selected
            if row.get("contract_trace", {}).get("first_count_divergence_step") is not None
        ]
        full_count_rows = [
            row
            for row in selected
            if bool(row.get("contract_trace", {}).get("full_count_agreement"))
        ]
        window_tokens = int(selected[0]["window_tokens"]) if selected else 0
        result[variant] = {
            "trials": len(selected),
            "same_precision_successes": sum(
                bool(row.get("same_precision_success")) for row in selected
            ),
            "cross_precision_successes": sum(
                bool(row.get("cross_precision_success")) for row in selected
            ),
            "source_same_outcome_matches": sum(
                bool(row.get("source_same_outcome_match")) for row in selected
            ),
            "source_cross_outcome_matches": sum(
                bool(row.get("source_cross_outcome_match")) for row in selected
            ),
            "symbols": len(same_records),
            "same_precision_completed_symbols": sum(
                bool(record.get("completed")) for record in same_records
            ),
            "same_precision_symbol_completion_rate": (
                sum(bool(record.get("completed")) for record in same_records) / len(same_records)
                if same_records
                else 0.0
            ),
            "mean_singleton_tokens_when_completed": (
                mean(singleton_tokens) if singleton_tokens else None
            ),
            "singleton_completion_cdf": _singleton_cdf(same_records, window_tokens),
            "full_support_agreement_trials": sum(
                bool(row.get("contract_trace", {}).get("full_support_agreement"))
                for row in selected
            ),
            "full_count_agreement_trials": len(full_count_rows),
            "replay_observed_rejection_trials": sum(
                row.get("contract_trace", {}).get("first_replay_rejection_step") is not None
                for row in selected
            ),
            "median_first_support_divergence_step": (
                median(support_divergences) if support_divergences else None
            ),
            "median_first_count_divergence_step": (
                median(count_divergences) if count_divergences else None
            ),
            "mean_trace_fraction": mean(
                float(row.get("contract_trace", {}).get("trace_fraction", 0.0))
                for row in selected
            )
            if selected
            else 0.0,
            "cross_successes_conditioned_on_full_count_agreement": sum(
                bool(row.get("cross_precision_success")) for row in full_count_rows
            ),
            "full_count_agreement_conditioning_trials": len(full_count_rows),
        }
    return result


def diagnostic_config(
    args: Any, source_path: Path, source_report: dict[str, Any]
) -> dict[str, Any]:
    source_config = source_report["experiment_config"]
    return {
        "schema": SCHEMA,
        "run_label": str(args.run_label),
        "source_path": str(source_path),
        "source_sha256": file_sha256(source_path),
        "source_experiment_signature": source_report["experiment_signature"],
        "model": source_config["model"],
        "device": source_config["device"],
        "reference_dtype": source_config["reference_dtype"],
        "replay_dtype": source_config["replay_dtype"],
        "top_p": source_config["top_p"],
        "top_k": source_config["top_k"],
        "logit_quantum": source_config["logit_quantum"],
        "bin_mass_bits": source_config["bin_mass_bits"],
        "temperature": source_config["temperature"],
        "trial_keys": source_config["trial_keys"],
    }


def diagnostic_trial_key(row: dict[str, Any]) -> tuple[int, int, int, int]:
    return trial_key(row)


def build_report(
    args: Any,
    source_path: Path,
    source_report: dict[str, Any],
    rows: list[dict[str, Any]],
    phase: str,
) -> dict[str, Any]:
    config = diagnostic_config(args, source_path, source_report)
    return {
        "schema": SCHEMA,
        "run_label": args.run_label,
        "phase": phase,
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "experiment_config": config,
        "experiment_signature": config_signature(config),
        "progress": {
            "completed_trials": len(rows),
            "expected_trials": len(source_report["rows"]),
        },
        "summary": summarize(rows),
        "rows": rows,
    }


def load_checkpoint_rows(path: Path, expected_config: dict[str, Any]) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("experiment_config") != expected_config:
        raise ValueError(
            "checkpoint experiment_config does not match this command; "
            "use another output path or pass --fresh"
        )
    if report.get("experiment_signature") != config_signature(expected_config):
        raise ValueError("checkpoint experiment_signature is invalid")
    rows = report.get("rows")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("checkpoint rows must be a list of objects")
    keys = [diagnostic_trial_key(row) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("checkpoint contains duplicate trial identities")
    expected = {tuple(int(value) for value in key) for key in expected_config["trial_keys"]}
    if not set(keys) <= expected:
        raise ValueError("checkpoint contains a trial outside the source matrix")
    return rows


def _provider_config(source_config: dict[str, Any], dtype: str) -> HuggingFaceConfig:
    return HuggingFaceConfig(
        model_name=source_config["model"],
        top_p=float(source_config["top_p"]),
        top_k=source_config["top_k"],
        logit_quantum=source_config["logit_quantum"],
        bin_mass_bits=source_config["bin_mass_bits"],
        candidate_order=source_config["candidate_order"],
        temperature=float(source_config["temperature"]),
        precision_context=source_config["precision_context"],
        device=source_config["device"],
        dtype=dtype,
        allow_eos=bool(source_config["allow_eos"]),
        adaptive_temperature=bool(source_config["adaptive_temperature"]),
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
    parser.add_argument(
        "--input", type=Path, default=Path("outputs/R036_gpt2_bin_mass_raw_bytes.json")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/R036D1_gpt2_failure_modes.json")
    )
    parser.add_argument("--run-label", default="R036-D1")
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="archive an existing diagnostic and initialize from zero trials",
    )
    args = parser.parse_args()

    source_report = load_source_report(args.input)
    config = diagnostic_config(args, args.input, source_report)
    rows = [] if args.fresh else load_checkpoint_rows(args.output, config)
    if args.fresh:
        archive_existing_report(args.output)
    if args.fresh or not args.output.exists():
        write_report(
            args.output,
            build_report(args, args.input, source_report, rows, "initialized"),
        )

    completed = {diagnostic_trial_key(row) for row in rows}
    pending = [row for row in source_report["rows"] if trial_key(row) not in completed]
    if pending:
        source_config = source_report["experiment_config"]
        reference_provider = HuggingFaceProvider(
            _provider_config(source_config, source_config["reference_dtype"])
        )
        replay_provider = HuggingFaceProvider(
            _provider_config(source_config, source_config["replay_dtype"])
        )
        for source_row in pending:
            row: dict[str, Any] = {
                "prompt_index": int(source_row["prompt_index"]),
                "payload_seed": int(source_row["payload_seed"]),
                "window_tokens": int(source_row["window_tokens"]),
                "parity_bytes": int(source_row["parity_bytes"]),
                "variant": str(source_row["variant"]),
                "source_same_precision_success": bool(source_row["same_precision_success"]),
                "source_cross_precision_success": bool(source_row["cross_precision_success"]),
            }
            try:
                prompt = str(source_row["prompt"])
                token_ids = [int(token_id) for token_id in source_row["token_ids"]]
                row["contract_trace"] = trace_contract(
                    reference_provider.start(prompt),
                    replay_provider.start(prompt),
                    token_ids,
                )
                codec = ByteSlicedCodec(ByteSlicedConfig(**source_row["codec"]))
                same = codec.decode(reference_provider.start(prompt), token_ids, KEY)
                cross = codec.decode(replay_provider.start(prompt), token_ids, KEY)
                expected_sha256 = str(source_row["payload_sha256"])
                row["same_precision_success"] = _payload_matches(
                    same.payload_bytes, expected_sha256
                )
                row["cross_precision_success"] = _payload_matches(
                    cross.payload_bytes, expected_sha256
                )
                row["same_precision_error"] = same.error
                row["cross_precision_error"] = cross.error
                row["same_precision_records"] = _record_dicts(same.records)
                row["cross_precision_records"] = _record_dicts(cross.records)
                row["source_same_outcome_match"] = (
                    row["same_precision_success"] == row["source_same_precision_success"]
                )
                row["source_cross_outcome_match"] = (
                    row["cross_precision_success"] == row["source_cross_precision_success"]
                )
            except Exception as error:  # noqa: BLE001 - retain exact diagnostic failure
                row["diagnostic_error"] = {
                    "type": type(error).__name__,
                    "message": str(error),
                }
            rows.append(row)
            write_report(
                args.output,
                build_report(args, args.input, source_report, rows, "partial"),
            )
        del reference_provider
        del replay_provider
        release_cuda()

    report = build_report(args, args.input, source_report, rows, "completed")
    write_report(args.output, report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
