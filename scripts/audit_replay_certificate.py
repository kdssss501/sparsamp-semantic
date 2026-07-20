"""R041 cross-precision reproducible-generation certificate benchmark."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import platform
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from math import log
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from sparsamp_semantic.providers.huggingface import (  # noqa: E402
    HuggingFaceConfig,
    HuggingFaceProvider,
)
from sparsamp_semantic.replay_certificate import (  # noqa: E402
    ReplayContractConfig,
    build_manifest,
    contract_decision,
    decision_context,
    manifest_payload_sizes,
)

SCHEMA = "sparsamp-r041-replay-certificate-v1"
DEFAULT_PROMPTS = (
    "Explain why reproducible AI experiments matter.",
    "Describe two practices that improve reliable software releases.",
    "Explain one benefit and one limitation of language models in education.",
)
DEFAULT_SYSTEM_PROMPT = (
    "You are a clear and accurate assistant. Answer the user's question directly, "
    "use complete sentences, and avoid unnecessary repetition."
)


def config_signature(config: dict[str, Any]) -> str:
    payload = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True), encoding="utf-8"
    )
    temporary.replace(path)


def archive_existing(path: Path) -> None:
    if not path.exists():
        return
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path.replace(path.with_name(f"{path.stem}.{stamp}.bak{path.suffix}"))


def release_cuda() -> None:
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


def trial_key(row: dict[str, Any]) -> tuple[int, int, str]:
    return int(row["prompt_index"]), int(row["seed"]), str(row["policy"])


def common_prefix_length(left: list[int], right: list[int]) -> int:
    count = 0
    for left_token, right_token in zip(left, right, strict=False):
        if left_token != right_token:
            break
        count += 1
    return count


def summarize(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for policy in sorted({str(row["policy"]) for row in rows}):
        selected = [row for row in rows if row["policy"] == policy]
        completed = [row for row in selected if bool(row.get("replay_completed"))]
        result[policy] = {
            "trials": len(selected),
            "replay_completed": len(completed),
            "corrected_exact_successes": sum(
                bool(row.get("corrected_exact")) for row in selected
            ),
            "uncorrected_exact_successes": sum(
                bool(row.get("uncorrected_exact")) for row in selected
            ),
            "mean_correction_rate": (
                mean(float(row["correction_rate"]) for row in completed) if completed else None
            ),
            "max_correction_rate": (
                max(float(row["correction_rate"]) for row in completed) if completed else None
            ),
            "reference_token_envelope_coverage": (
                sum(int(row["reference_tokens_in_envelope"]) for row in completed)
                / sum(int(row["token_count"]) for row in completed)
                if completed
                else None
            ),
            "mean_sparse_to_full_payload_ratio": (
                mean(float(row["sparse_to_full_payload_ratio"]) for row in completed)
                if completed
                else None
            ),
            "mean_uncorrected_prefix_tokens": (
                mean(int(row["uncorrected_common_prefix_tokens"]) for row in completed)
                if completed
                else None
            ),
            "mean_shared_contract_exact_rate": (
                mean(float(row["shared_contract_exact_rate"]) for row in completed)
                if completed
                else None
            ),
            "mean_contract_source_mass": (
                mean(float(row["mean_contract_source_mass"]) for row in completed)
                if completed and all("mean_contract_source_mass" in row for row in completed)
                else None
            ),
            "mean_contract_truncation_kl_nats": (
                mean(
                    float(row["mean_contract_truncation_kl_nats"])
                    for row in completed
                )
                if completed
                and all("mean_contract_truncation_kl_nats" in row for row in completed)
                else None
            ),
        }
    return result


def result_signature(rows: list[dict[str, Any]]) -> str:
    deterministic = []
    for row in sorted(rows, key=trial_key):
        deterministic.append(
            {
                "trial_key": list(trial_key(row)),
                "reference_token_sha256": row.get("reference_token_sha256"),
                "corrections": row.get("corrections"),
                "corrected_exact": row.get("corrected_exact"),
                "uncorrected_exact": row.get("uncorrected_exact"),
                "uncorrected_common_prefix_tokens": row.get(
                    "uncorrected_common_prefix_tokens"
                ),
                "uncorrected_positional_agreement": row.get(
                    "uncorrected_positional_agreement"
                ),
                "reference_tokens_in_envelope": row.get(
                    "reference_tokens_in_envelope"
                ),
                "shared_contract_exact_steps": row.get("shared_contract_exact_steps"),
                "sparse_payload_bytes": row.get("sparse_payload_bytes"),
                "full_trace_payload_bytes": row.get("full_trace_payload_bytes"),
            }
        )
    payload = json.dumps(
        deterministic, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def experiment_config(args: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "run_label": args.run_label,
        "model": args.model,
        "device": args.device,
        "reference_dtype": args.reference_dtype,
        "replay_dtype": args.replay_dtype,
        "tokens": args.tokens,
        "seeds": args.seeds,
        "policies": args.policies,
        "envelope_top_k": args.envelope_top_k,
        "contract_top_k": args.contract_top_k,
        "logit_quantum": args.logit_quantum,
        "mass_bits": args.mass_bits,
        "temperature": args.temperature,
        "vocabulary_size": args.vocabulary_size,
        "system_prompt": args.system_prompt,
        "prompts": list(DEFAULT_PROMPTS),
    }


def build_report(args: Any, rows: list[dict[str, Any]], phase: str) -> dict[str, Any]:
    config = experiment_config(args)
    expected = len(DEFAULT_PROMPTS) * len(args.seeds) * len(args.policies)
    return {
        "schema": SCHEMA,
        "run_label": args.run_label,
        "phase": phase,
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "experiment_config": config,
        "experiment_signature": config_signature(config),
        "progress": {"completed_trials": len(rows), "expected_trials": expected},
        "result_signature": result_signature(rows),
        "summary": summarize(rows),
        "rows": rows,
    }


def load_rows(path: Path, expected_config: dict[str, Any]) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("experiment_config") != expected_config:
        raise ValueError("checkpoint configuration mismatch")
    rows = report.get("rows")
    if not isinstance(rows, list) or len({trial_key(row) for row in rows}) != len(rows):
        raise ValueError("checkpoint rows are invalid or duplicated")
    return rows


def provider_config(args: Any, dtype: str) -> HuggingFaceConfig:
    return HuggingFaceConfig(
        model_name=args.model,
        device=args.device,
        dtype=dtype,
        top_p=1.0,
        top_k=args.envelope_top_k,
        logit_quantum=args.logit_quantum,
        candidate_order="token_id",
        temperature=args.temperature,
        precision_context="portable",
        allow_eos=False,
        adaptive_temperature=False,
        system_prompt=args.system_prompt,
    )


def replay_config(args: Any, seed: int) -> ReplayContractConfig:
    return ReplayContractConfig(
        contract_top_k=args.contract_top_k,
        logit_quantum=args.logit_quantum,
        mass_bits=args.mass_bits,
        temperature=args.temperature,
        public_seed=seed,
    )


def generate_reference(
    provider: HuggingFaceProvider,
    args: Any,
    prompt: str,
    seed: int,
    policy: str,
) -> dict[str, Any]:
    session = provider.start(prompt)
    contract_config = replay_config(args, seed)
    context = decision_context(args.model, prompt, contract_config)
    token_ids: list[int] = []
    contracts: list[dict[str, Any]] = []
    started = perf_counter()
    for step in range(args.tokens):
        snapshot = session.next_distribution()
        decision = contract_decision(snapshot, step, context, contract_config, policy=policy)
        contract_candidates = sorted(
            snapshot.candidates, key=lambda candidate: int(candidate.rank)
        )[: args.contract_top_k]
        contract_source_mass = snapshot.source_mass * sum(
            candidate.probability for candidate in contract_candidates
        )
        token_ids.append(decision.token_id)
        contracts.append(
            {
                "token_ids": list(decision.token_ids),
                "counts": list(decision.counts),
                "source_mass": snapshot.source_mass,
                "contract_source_mass": contract_source_mass,
                "contract_truncation_kl_nats": -log(contract_source_mass),
                "quantization_kl_nats": snapshot.metadata.get(
                    "logit_quantization_kl_nats"
                ),
                "quantization_tv": snapshot.metadata.get(
                    "logit_quantization_total_variation"
                ),
                "latency_ms": snapshot.latency_ms,
            }
        )
        session.append(decision.token_id)
    return {
        "reference_completed": True,
        "token_count": len(token_ids),
        "reference_token_ids": token_ids,
        "reference_token_sha256": hashlib.sha256(
            b"".join(token.to_bytes(4, "big") for token in token_ids)
        ).hexdigest(),
        "reference_text": session.render(),
        "reference_contracts": contracts,
        "reference_seconds": perf_counter() - started,
        "mean_reference_source_mass": mean(item["source_mass"] for item in contracts),
        "mean_contract_source_mass": mean(
            item["contract_source_mass"] for item in contracts
        ),
        "mean_contract_truncation_kl_nats": mean(
            item["contract_truncation_kl_nats"] for item in contracts
        ),
        "mean_reference_quantization_kl_nats": mean(
            float(item["quantization_kl_nats"]) for item in contracts
        ),
        "mean_reference_quantization_tv": mean(
            float(item["quantization_tv"]) for item in contracts
        ),
    }


def run_replay(
    provider: HuggingFaceProvider,
    args: Any,
    row: dict[str, Any],
) -> None:
    prompt = str(row["prompt"])
    reference = [int(token) for token in row["reference_token_ids"]]
    contract_config = replay_config(args, int(row["seed"]))
    context = decision_context(args.model, prompt, contract_config)

    shared = provider.start(prompt)
    local_shared_choices: list[int] = []
    contract_exact = 0
    reference_in_envelope = 0
    reference_ranks: list[int] = []
    started = perf_counter()
    for step, reference_token in enumerate(reference):
        snapshot = shared.next_distribution()
        decision = contract_decision(
            snapshot, step, context, contract_config, policy=str(row["policy"])
        )
        local_shared_choices.append(decision.token_id)
        expected_contract = row["reference_contracts"][step]
        if (
            list(decision.token_ids) == expected_contract["token_ids"]
            and list(decision.counts) == expected_contract["counts"]
        ):
            contract_exact += 1
        ranked = {int(candidate.token_id): int(candidate.rank) for candidate in snapshot.candidates}
        if reference_token not in ranked:
            row["replay_error"] = f"reference token absent from top-{args.envelope_top_k}"
            row["replay_completed"] = False
            row["reference_tokens_in_envelope"] = reference_in_envelope
            row["replay_seconds"] = perf_counter() - started
            return
        reference_in_envelope += 1
        reference_ranks.append(ranked[reference_token])
        shared.append(reference_token)

    manifest = build_manifest(tuple(reference), tuple(local_shared_choices))
    corrected = provider.start(prompt)
    corrected_tokens: list[int] = []
    for step in range(args.tokens):
        snapshot = corrected.next_distribution()
        decision = contract_decision(
            snapshot, step, context, contract_config, policy=str(row["policy"])
        )
        token_id = manifest.apply(step, decision.token_id)
        corrected.append(token_id)
        corrected_tokens.append(token_id)

    uncorrected = provider.start(prompt)
    uncorrected_tokens: list[int] = []
    for step in range(args.tokens):
        snapshot = uncorrected.next_distribution()
        decision = contract_decision(
            snapshot, step, context, contract_config, policy=str(row["policy"])
        )
        uncorrected.append(decision.token_id)
        uncorrected_tokens.append(decision.token_id)

    sparse_bytes, full_bytes = manifest_payload_sizes(
        manifest, vocabulary_size=args.vocabulary_size
    )
    row.update(
        {
            "replay_completed": True,
            "corrections": [asdict(item) for item in manifest.corrections],
            "correction_count": len(manifest.corrections),
            "correction_rate": len(manifest.corrections) / args.tokens,
            "corrected_exact": corrected_tokens == reference,
            "corrected_text": corrected.render(),
            "uncorrected_exact": uncorrected_tokens == reference,
            "uncorrected_common_prefix_tokens": common_prefix_length(
                reference, uncorrected_tokens
            ),
            "uncorrected_positional_agreement": sum(
                left == right for left, right in zip(reference, uncorrected_tokens, strict=True)
            )
            / args.tokens,
            "uncorrected_text": uncorrected.render(),
            "reference_tokens_in_envelope": reference_in_envelope,
            "mean_reference_rank_in_replay": mean(reference_ranks),
            "shared_contract_exact_steps": contract_exact,
            "shared_contract_exact_rate": contract_exact / args.tokens,
            "sparse_payload_bytes": sparse_bytes,
            "full_trace_payload_bytes": full_bytes,
            "sparse_to_full_payload_ratio": sparse_bytes / full_bytes,
            "replay_seconds": perf_counter() - started,
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="models/gpt2")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--reference-dtype", default="float32")
    parser.add_argument("--replay-dtype", default="float16")
    parser.add_argument("--tokens", type=int, default=64)
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1])
    parser.add_argument("--policies", nargs="+", default=["seeded", "greedy"])
    parser.add_argument("--envelope-top-k", type=int, default=16)
    parser.add_argument("--contract-top-k", type=int, default=2)
    parser.add_argument("--logit-quantum", type=float, default=0.5)
    parser.add_argument("--mass-bits", type=int, default=16)
    parser.add_argument("--temperature", type=float, default=1.2)
    parser.add_argument("--vocabulary-size", type=int, default=50257)
    parser.add_argument("--system-prompt", default=DEFAULT_SYSTEM_PROMPT)
    parser.add_argument("--run-label", default="R041")
    parser.add_argument("--output", type=Path, default=Path("outputs/R041_gpt2_replay_certificate.json"))
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()
    if args.tokens < 1 or len(args.seeds) != len(set(args.seeds)):
        raise ValueError("tokens must be positive and seeds unique")
    if set(args.policies) - {"seeded", "greedy"}:
        raise ValueError("policies must be seeded or greedy")
    if len(args.policies) != len(set(args.policies)):
        raise ValueError("policies must be unique")

    config = experiment_config(args)
    rows = [] if args.fresh else load_rows(args.output, config)
    if args.fresh:
        archive_existing(args.output)
    if args.fresh or not args.output.exists():
        write_report(args.output, build_report(args, rows, "initialized"))
    by_key = {trial_key(row): row for row in rows}

    pending_reference = [
        (prompt_index, prompt, seed, policy)
        for prompt_index, prompt in enumerate(DEFAULT_PROMPTS)
        for seed in args.seeds
        for policy in args.policies
        if not bool(by_key.get((prompt_index, seed, policy), {}).get("reference_completed"))
    ]
    if pending_reference:
        provider = HuggingFaceProvider(provider_config(args, args.reference_dtype))
        for prompt_index, prompt, seed, policy in pending_reference:
            key = (prompt_index, seed, policy)
            row = by_key.get(
                key,
                {"prompt_index": prompt_index, "prompt": prompt, "seed": seed, "policy": policy},
            )
            try:
                row.update(generate_reference(provider, args, prompt, seed, policy))
            except Exception as error:  # noqa: BLE001
                row["reference_error"] = f"{type(error).__name__}: {error}"
            if key not in by_key:
                rows.append(row)
                by_key[key] = row
            write_report(args.output, build_report(args, rows, "reference_partial"))
        del provider
        release_cuda()

    pending_replay = [
        row
        for row in rows
        if bool(row.get("reference_completed")) and not bool(row.get("replay_completed"))
    ]
    if pending_replay:
        provider = HuggingFaceProvider(provider_config(args, args.replay_dtype))
        for row in pending_replay:
            try:
                run_replay(provider, args, row)
            except Exception as error:  # noqa: BLE001
                row["replay_error"] = f"{type(error).__name__}: {error}"
                row["replay_completed"] = False
            write_report(args.output, build_report(args, rows, "replay_partial"))
        del provider
        release_cuda()

    phase = "completed" if all(bool(row.get("replay_completed")) for row in rows) else "partial"
    report = build_report(args, rows, phase)
    write_report(args.output, report)
    print(json.dumps({"phase": phase, "summary": report["summary"]}, indent=2))
    return 0 if phase == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
