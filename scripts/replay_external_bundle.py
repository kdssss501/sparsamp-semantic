"""Replay a portable reference bundle in a target numerical environment."""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.audit_replay_certificate import (  # noqa: E402
    provider_config,
    release_cuda,
    result_signature,
    run_replay,
    summarize,
    trial_key,
)
from sparsamp_semantic.providers.huggingface import HuggingFaceProvider  # noqa: E402
from sparsamp_semantic.replay_package import (  # noqa: E402
    canonical_signature,
    model_fingerprint,
    runtime_fingerprint,
    validate_reference_bundle,
    write_atomic_json,
)


def target_config(bundle: dict, args: argparse.Namespace, model: dict) -> dict:
    return {
        "schema": "external-precision-replay-target-v1",
        "bundle_signature": bundle["bundle_signature"],
        "logical_model": bundle["experiment_config"]["model"],
        "local_model": str(args.model),
        "target_dtype": args.target_dtype or bundle["experiment_config"]["replay_dtype"],
        "device": args.device,
        "model_fingerprint": model,
    }


def build_report(
    bundle: dict, config: dict, rows: list[dict], environment: dict, phase: str
) -> dict:
    return {
        "schema": "external-precision-replay-target-v1",
        "phase": phase,
        "experiment_config": config,
        "experiment_signature": canonical_signature(config),
        "environment": environment,
        "progress": {"completed_trials": len(rows), "expected_trials": len(bundle["rows"])},
        "result_signature": result_signature(rows),
        "summary": summarize(rows),
        "rows": rows,
    }


def load_checkpoint(path: Path, config: dict) -> list[dict]:
    if not path.exists():
        return []
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("experiment_config") != config:
        raise ValueError("target checkpoint configuration mismatch")
    rows = report.get("rows")
    if not isinstance(rows, list) or len({trial_key(row) for row in rows}) != len(rows):
        raise ValueError("target checkpoint rows are invalid")
    return rows


def namespace_from_bundle(bundle: dict, *, model_name: str, device: str) -> SimpleNamespace:
    config = dict(bundle["experiment_config"])
    config.update({"model": model_name, "device": device})
    return SimpleNamespace(**config)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--target-dtype", default=None)
    parser.add_argument("--metadata-only-weights", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    validate_reference_bundle(bundle)
    local_model = model_fingerprint(args.model, hash_weights=not args.metadata_only_weights)
    if local_model["signature"] != bundle["model_fingerprint"]["signature"]:
        raise ValueError("local model fingerprint does not match the reference bundle")
    environment = runtime_fingerprint()
    config = target_config(bundle, args, local_model)
    if args.fresh and args.output.exists():
        args.output.replace(args.output.with_suffix(args.output.suffix + ".bak"))
    rows = [] if args.fresh else load_checkpoint(args.output, config)
    by_key = {trial_key(row): row for row in rows}

    provider_args = namespace_from_bundle(bundle, model_name=str(args.model), device=args.device)
    target_dtype = config["target_dtype"]
    provider = HuggingFaceProvider(provider_config(provider_args, target_dtype))
    run_args = namespace_from_bundle(
        bundle, model_name=bundle["experiment_config"]["model"], device=args.device
    )
    for reference in bundle["rows"]:
        key = trial_key(reference)
        if bool(by_key.get(key, {}).get("replay_completed")):
            continue
        row = deepcopy(reference)
        try:
            run_replay(provider, run_args, row)
        except Exception as error:  # noqa: BLE001
            row["replay_error"] = f"{type(error).__name__}: {error}"
            row["replay_completed"] = False
        if key in by_key:
            rows[rows.index(by_key[key])] = row
        else:
            rows.append(row)
        by_key[key] = row
        write_atomic_json(
            args.output, build_report(bundle, config, rows, environment, "replay_partial")
        )
    del provider
    release_cuda()

    completed = len(rows) == len(bundle["rows"]) and all(
        bool(row.get("replay_completed")) and bool(row.get("corrected_exact")) for row in rows
    )
    report = build_report(bundle, config, rows, environment, "completed" if completed else "partial")
    write_atomic_json(args.output, report)
    print(json.dumps({"phase": report["phase"], "summary": report["summary"]}, indent=2))
    return 0 if completed else 1


if __name__ == "__main__":
    raise SystemExit(main())
