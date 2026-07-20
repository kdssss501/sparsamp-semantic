"""R036-D6 retrospective soft RS list-recovery audit over contract candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.audit_bin_mass_failure_modes import file_sha256  # noqa: E402
from scripts.audit_byte_sliced_messages import (  # noqa: E402
    archive_existing_report,
    config_signature,
    write_report,
)
from sparsamp_semantic.list_recovery import (  # noqa: E402
    ListRecoveryConfig,
    candidate_cost_map,
    decode_rs_lists,
    score_codeword,
)

SCHEMA = "sparsamp-r036d6-rs-list-recovery-v1"


def row_key(row: dict[str, Any]) -> tuple[int, int, int]:
    return int(row["prompt_index"]), int(row["payload_seed"]), int(row["cost_threshold"])


def summarize(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for threshold in sorted({int(row["cost_threshold"]) for row in rows}):
        selected = [row for row in rows if int(row["cost_threshold"]) == threshold]
        result[str(threshold)] = {
            "trials": len(selected),
            "unique_successes": sum(bool(row["unique_success"]) for row in selected),
            "expected_in_best_tie": sum(bool(row["expected_in_best_tie"]) for row in selected),
            "mean_best_tie_count": mean(int(row["best_tie_count"]) for row in selected),
            "mean_net_payload_bits_per_token": mean(
                float(row["net_payload_bits_per_token"]) for row in selected
            ),
        }
    return result


def experiment_config(args: Any, source: dict[str, Any], candidates: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "run_label": args.run_label,
        "source_path": str(args.source),
        "source_sha256": file_sha256(args.source),
        "source_signature": source["experiment_signature"],
        "candidate_path": str(args.candidates),
        "candidate_sha256": file_sha256(args.candidates),
        "candidate_signature": candidates["experiment_signature"],
        "variant": args.variant,
        "cost_thresholds": args.cost_thresholds,
        "enumeration_limit": args.enumeration_limit,
    }


def build_report(
    args: Any,
    source: dict[str, Any],
    candidates: dict[str, Any],
    rows: list[dict[str, Any]],
    phase: str,
) -> dict[str, Any]:
    config = experiment_config(args, source, candidates)
    expected = sum(row["variant"] == args.variant for row in candidates["rows"]) * len(
        args.cost_thresholds
    )
    return {
        "schema": SCHEMA,
        "run_label": args.run_label,
        "phase": phase,
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "experiment_config": config,
        "experiment_signature": config_signature(config),
        "progress": {"completed_trials": len(rows), "expected_trials": expected},
        "summary": summarize(rows),
        "rows": rows,
    }


def load_rows(path: Path, expected: dict[str, Any]) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("experiment_config") != expected:
        raise ValueError("checkpoint configuration mismatch")
    rows = report.get("rows")
    if not isinstance(rows, list) or len({row_key(row) for row in rows}) != len(rows):
        raise ValueError("checkpoint rows are invalid or duplicated")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("outputs/R036_gpt2_bin_mass_raw_bytes.json"))
    parser.add_argument(
        "--candidates",
        type=Path,
        default=Path("outputs/R036D5_contract_list_decoder_k4_r1_b4096_q16.json"),
    )
    parser.add_argument("--output", type=Path, default=Path("outputs/R036D6_rs_list_recovery.json"))
    parser.add_argument("--variant", default="window=32,parity=2")
    parser.add_argument("--cost-thresholds", type=int, nargs="+", default=[0, 1, 2, 3])
    parser.add_argument("--enumeration-limit", type=int, default=1 << 16)
    parser.add_argument("--run-label", default="R036-D6")
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()
    if len(args.cost_thresholds) != len(set(args.cost_thresholds)):
        raise ValueError("cost thresholds must be unique")
    source = json.loads(args.source.read_text(encoding="utf-8"))
    candidates = json.loads(args.candidates.read_text(encoding="utf-8"))
    config = experiment_config(args, source, candidates)
    rows = [] if args.fresh else load_rows(args.output, config)
    if args.fresh:
        archive_existing_report(args.output)
    if args.fresh or not args.output.exists():
        write_report(args.output, build_report(args, source, candidates, rows, "initialized"))
    done = {row_key(row) for row in rows}
    source_rows = {
        (int(row["prompt_index"]), int(row["payload_seed"]), str(row["variant"])): row
        for row in source["rows"]
    }
    for candidate_row in candidates["rows"]:
        if candidate_row["variant"] != args.variant:
            continue
        source_row = source_rows[
            (int(candidate_row["prompt_index"]), int(candidate_row["payload_seed"]), args.variant)
        ]
        payload_bytes = int(source_row["payload_bits"]) // 8
        parity_bytes = int(source_row["parity_bytes"])
        expected_codeword = bytes.fromhex(str(source_row["codeword_hex"]))
        windows = [
            (window["candidates"], window["candidate_costs"])
            for window in candidate_row["windows"]
        ]
        cost_maps = [candidate_cost_map(*window) for window in windows]
        for threshold in args.cost_thresholds:
            identity = (
                int(candidate_row["prompt_index"]),
                int(candidate_row["payload_seed"]),
                int(threshold),
            )
            if identity in done:
                continue
            decoder_config = ListRecoveryConfig(
                payload_bytes=payload_bytes,
                parity_bytes=parity_bytes,
                cost_threshold=threshold,
                enumeration_limit=args.enumeration_limit,
            )
            decoded = decode_rs_lists(windows, decoder_config)
            expected_score = score_codeword(expected_codeword, cost_maps, threshold)
            decoded_sha = hashlib.sha256(decoded.payload).hexdigest() if decoded.payload else None
            row = {
                "prompt_index": identity[0],
                "payload_seed": identity[1],
                "variant": args.variant,
                "cost_threshold": threshold,
                "best_score": list(decoded.best_score),
                "runner_up_score": list(decoded.runner_up_score) if decoded.runner_up_score else None,
                "best_tie_count": decoded.best_tie_count,
                "expected_score": list(expected_score),
                "expected_in_best_tie": expected_score == decoded.best_score,
                "unique_success": decoded_sha == source_row["payload_sha256"],
                "enumerated_payloads": decoded.enumerated_payloads,
                "net_payload_bits_per_token": float(source_row["net_payload_bits_per_token"]),
            }
            rows.append(row)
            done.add(identity)
            write_report(args.output, build_report(args, source, candidates, rows, "partial"))
    report = build_report(args, source, candidates, rows, "completed")
    write_report(args.output, report)
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
