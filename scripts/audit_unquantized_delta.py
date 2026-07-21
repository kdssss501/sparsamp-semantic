"""Build resumable unquantized target-conditioned delta baselines."""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.audit_replay_certificate import release_cuda, trial_key  # noqa: E402
from sparsamp_semantic.certificate_format import (  # noqa: E402
    encode_manifest,
    encode_referenced_package_header,
    encode_trial_record,
)
from sparsamp_semantic.providers.huggingface import (  # noqa: E402
    HuggingFaceConfig,
    HuggingFaceProvider,
)
from sparsamp_semantic.replay_certificate import (  # noqa: E402
    ReplayContractConfig,
    build_manifest,
    decision_context,
    public_replay_fraction,
)
from sparsamp_semantic.replay_package import (  # noqa: E402
    canonical_signature,
    model_fingerprint,
    runtime_fingerprint,
    validate_reference_bundle,
    write_atomic_json,
)
from sparsamp_semantic.types import TokenCandidate  # noqa: E402


SCHEMA = "unquantized-target-delta-v1"


def unquantized_choice(
    candidates: Sequence[TokenCandidate], sample: Fraction, top_k: int
) -> int:
    """Map the shared fraction through an unquantized top-k distribution."""

    if top_k < 1 or not candidates:
        raise ValueError("top-k and candidate support must be positive")
    ranked = sorted(candidates, key=lambda item: int(item.rank))[:top_k]
    ordered = sorted(ranked, key=lambda item: int(item.token_id))
    weights = [Fraction(Decimal(str(item.probability))) for item in ordered]
    total = sum(weights, start=Fraction(0))
    if total <= 0:
        raise ValueError("unquantized candidate distribution has no mass")
    threshold = sample * total
    cumulative = Fraction(0)
    for candidate, weight in zip(ordered, weights, strict=True):
        cumulative += weight
        if threshold < cumulative:
            return int(candidate.token_id)
    return int(ordered[-1].token_id)


def experiment_config(
    bundle: dict[str, Any],
    args: argparse.Namespace,
    model: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "bundle_signature": bundle["bundle_signature"],
        "logical_model": bundle["experiment_config"]["model"],
        "local_model": str(args.model),
        "model_fingerprint": model,
        "device": args.device,
        "target_dtype": args.target_dtype,
        "envelope_top_k": args.envelope_top_k,
        "top_k_values": list(args.top_k_values),
        "temperature": args.temperature,
        "support_policy": "positive-probability-cap-v1",
        "system_prompt": bundle["experiment_config"]["system_prompt"],
    }


def load_rows(path: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("experiment_config") != config:
        raise ValueError("unquantized delta checkpoint configuration mismatch")
    rows = report.get("rows")
    if not isinstance(rows, list) or len({trial_key(row) for row in rows}) != len(rows):
        raise ValueError("unquantized delta checkpoint rows are invalid")
    return rows


def summarize(
    rows: list[dict[str, Any]],
    top_k_values: Sequence[int],
    header_bytes: int,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for top_k in top_k_values:
        key = f"top_{top_k}"
        completed = [row for row in rows if row.get("completed")]
        payload_bytes = sum(
            int(row["variants"][key]["manifest_payload_bytes"]) for row in completed
        )
        record_bytes = sum(
            int(row["variants"][key]["trial_record_bytes"]) for row in completed
        )
        tokens = sum(int(row["token_count"]) for row in completed)
        package_bytes = header_bytes + record_bytes if completed else None
        result[key] = {
            "trials": len(completed),
            "tokens": tokens,
            "exact_recovery": sum(
                bool(row["variants"][key]["corrected_exact"]) for row in completed
            ),
            "mean_correction_rate": (
                mean(
                    float(row["variants"][key]["correction_rate"])
                    for row in completed
                )
                if completed
                else None
            ),
            "manifest_payload_bytes": payload_bytes,
            "referenced_package_bytes": package_bytes,
            "support_shortfall_steps": sum(
                int(row["variants"][key]["support_shortfall_steps"])
                for row in completed
            ),
            "reference_outside_support_steps": sum(
                int(row["variants"][key]["reference_outside_support_steps"])
                for row in completed
            ),
            "minimum_available_support": (
                min(
                    int(row["variants"][key]["minimum_available_support"])
                    for row in completed
                )
                if completed
                else None
            ),
            "bits_per_token": (
                8 * package_bytes / tokens if completed and tokens else None
            ),
        }
    return result


def build_report(
    bundle: dict[str, Any],
    config: dict[str, Any],
    environment: dict[str, Any],
    rows: list[dict[str, Any]],
    header_bytes: int,
) -> dict[str, Any]:
    complete = len(rows) == len(bundle["rows"]) and all(
        row.get("completed") for row in rows
    )
    return {
        "schema": SCHEMA,
        "phase": "completed" if complete else "partial",
        "timestamp": datetime.now(UTC).isoformat(),
        "experiment_config": config,
        "experiment_signature": canonical_signature(config),
        "environment": environment,
        "progress": {
            "completed_trials": len(rows),
            "expected_trials": len(bundle["rows"]),
        },
        "summary": summarize(rows, config["top_k_values"], header_bytes),
        "rows": sorted(rows, key=trial_key),
    }


def run_row(
    provider: HuggingFaceProvider,
    bundle: dict[str, Any],
    reference: dict[str, Any],
    top_k_values: Sequence[int],
    environment_signature: str,
) -> dict[str, Any]:
    row = deepcopy(reference)
    prompt = str(reference["prompt"])
    seed = int(reference["seed"])
    reference_tokens = [int(value) for value in reference["reference_token_ids"]]
    source_config = bundle["experiment_config"]
    replay_config = ReplayContractConfig(
        contract_top_k=int(source_config["contract_top_k"]),
        logit_quantum=float(source_config["logit_quantum"]),
        mass_bits=int(source_config["mass_bits"]),
        temperature=float(source_config["temperature"]),
        public_seed=seed,
    )
    context = decision_context(str(source_config["model"]), prompt, replay_config)
    session = provider.start(prompt)
    local_choices = {top_k: [] for top_k in top_k_values}
    support_shortfalls = {top_k: 0 for top_k in top_k_values}
    minimum_support = {top_k: top_k for top_k in top_k_values}
    reference_outside_support = 0
    started = perf_counter()
    for step, reference_token in enumerate(reference_tokens):
        snapshot = session.next_distribution()
        sample = public_replay_fraction(step, context, seed)
        ranked = {int(item.token_id): int(item.rank) for item in snapshot.candidates}
        reference_outside_support += int(reference_token not in ranked)
        for top_k in top_k_values:
            available = min(top_k, len(snapshot.candidates))
            support_shortfalls[top_k] += int(available < top_k)
            minimum_support[top_k] = min(minimum_support[top_k], available)
            local_choices[top_k].append(
                unquantized_choice(snapshot.candidates, sample, top_k)
            )
        session.append(reference_token)

    variants: dict[str, Any] = {}
    for top_k in top_k_values:
        manifest = build_manifest(
            tuple(reference_tokens), tuple(local_choices[top_k])
        )
        payload = encode_manifest(manifest)
        record = encode_trial_record(
            prompt_index=int(reference["prompt_index"]),
            seed=seed,
            policy=str(reference["policy"]),
            token_count=len(reference_tokens),
            reference_token_sha256=str(reference["reference_token_sha256"]),
            payload=payload,
        )
        corrected = [
            manifest.apply(step, token_id)
            for step, token_id in enumerate(local_choices[top_k])
        ]
        variants[f"top_{top_k}"] = {
            "corrections": [
                {"step": item.step, "token_id": item.token_id}
                for item in manifest.corrections
            ],
            "correction_count": len(manifest.corrections),
            "correction_rate": len(manifest.corrections) / len(reference_tokens),
            "corrected_exact": corrected == reference_tokens,
            "manifest_payload_bytes": len(payload),
            "trial_record_bytes": len(record),
            "support_shortfall_steps": support_shortfalls[top_k],
            "reference_outside_support_steps": reference_outside_support,
            "minimum_available_support": minimum_support[top_k],
        }
    return {
        **row,
        "completed": True,
        "variants": variants,
        "construction_seconds": perf_counter() - started,
        "environment_signature": environment_signature,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--target-dtype", default="bfloat16")
    parser.add_argument("--envelope-top-k", type=int, default=32)
    parser.add_argument("--top-k-values", type=int, nargs="+", default=[2, 16])
    parser.add_argument("--temperature", type=float, default=1.2)
    parser.add_argument("--metadata-only-weights", action="store_true")
    parser.add_argument(
        "--max-new-trials",
        type=int,
        default=None,
        help="execution-only cap for resumable pilots; omitted from experiment signature",
    )
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()
    args.top_k_values = sorted(set(args.top_k_values))
    if not args.top_k_values or args.top_k_values[0] < 1:
        raise ValueError("top-k values must be positive")
    if args.envelope_top_k < max(args.top_k_values):
        raise ValueError("envelope-top-k must cover every requested top-k")
    if args.max_new_trials is not None and args.max_new_trials < 1:
        raise ValueError("max-new-trials must be positive")

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    validate_reference_bundle(bundle)
    local_model = model_fingerprint(
        args.model, hash_weights=not args.metadata_only_weights
    )
    if local_model["signature"] != bundle["model_fingerprint"]["signature"]:
        raise ValueError("local model fingerprint does not match the reference bundle")
    environment = runtime_fingerprint()
    config = experiment_config(bundle, args, local_model)
    if args.fresh and args.output.exists():
        args.output.replace(args.output.with_suffix(args.output.suffix + ".bak"))
    rows = [] if args.fresh else load_rows(args.output, config)
    by_key = {trial_key(row): row for row in rows}
    header = encode_referenced_package_header(
        bundle_signature=bundle["bundle_signature"],
        model_signature=bundle["model_fingerprint"]["signature"],
        environment_signature=environment["signature"],
    )
    write_atomic_json(
        args.output, build_report(bundle, config, environment, rows, len(header))
    )

    provider = HuggingFaceProvider(
        HuggingFaceConfig(
            model_name=str(args.model),
            device=args.device,
            dtype=args.target_dtype,
            top_p=1.0,
            top_k=args.envelope_top_k,
            logit_quantum=None,
            candidate_order="token_id",
            temperature=args.temperature,
            precision_context="portable",
            allow_eos=False,
            adaptive_temperature=False,
            system_prompt=bundle["experiment_config"]["system_prompt"],
            allow_forced_prefix_tokens=True,
        )
    )
    new_trials = 0
    for reference in bundle["rows"]:
        key = trial_key(reference)
        if by_key.get(key, {}).get("completed"):
            continue
        if args.max_new_trials is not None and new_trials >= args.max_new_trials:
            break
        row = run_row(
            provider,
            bundle,
            reference,
            args.top_k_values,
            environment["signature"],
        )
        rows.append(row)
        by_key[key] = row
        new_trials += 1
        write_atomic_json(
            args.output, build_report(bundle, config, environment, rows, len(header))
        )
    del provider
    release_cuda()

    report = build_report(bundle, config, environment, rows, len(header))
    write_atomic_json(args.output, report)
    print(json.dumps({"phase": report["phase"], "summary": report["summary"]}, indent=2))
    return 0 if report["phase"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
