"""Measure complete serialized certificate cost and separated replay throughput."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from sparsamp_semantic.certificate_format import (  # noqa: E402
    canonical_json_bytes,
    encode_manifest,
    encode_referenced_package_header,
    encode_trial_record,
    encode_uvarint,
)
from sparsamp_semantic.replay_certificate import (  # noqa: E402
    ReplayCorrection,
    ReplayManifest,
)
from sparsamp_semantic.replay_package import (  # noqa: E402
    file_sha256,
    validate_reference_bundle,
)


def full_trace_bytes(token_ids: list[int]) -> bytes:
    output = bytearray(b"SPRT\x01")
    output.extend(encode_uvarint(len(token_ids)))
    for token_id in token_ids:
        output.extend(encode_uvarint(int(token_id)))
    return bytes(output)


def trial_header(row: dict[str, Any]) -> bytes:
    value = {
        "prompt_index": int(row["prompt_index"]),
        "seed": int(row["seed"]),
        "policy": str(row["policy"]),
        "token_count": int(row["token_count"]),
        "reference_token_sha256": str(row["reference_token_sha256"]),
    }
    return canonical_json_bytes(value) + b"\n"


def row_manifest(row: dict[str, Any]) -> ReplayManifest:
    corrections = tuple(
        ReplayCorrection(step=int(item["step"]), token_id=int(item["token_id"]))
        for item in row["corrections"]
    )
    return ReplayManifest(token_count=int(row["token_count"]), corrections=corrections)


def analyze(bundle: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    validate_reference_bundle(bundle)
    if target.get("phase") != "completed":
        raise ValueError("target replay report must be completed")
    if target["experiment_config"]["bundle_signature"] != bundle["bundle_signature"]:
        raise ValueError("target report does not belong to the reference bundle")
    rows = target["rows"]
    if len(rows) != len(bundle["rows"]):
        raise ValueError("target report trial count does not match the bundle")
    if not all(bool(row.get("corrected_exact")) for row in rows):
        raise ValueError("cost analysis requires exact corrected replay for every trial")

    shared_header = canonical_json_bytes(
        {
            "schema": "sparse-precision-replay-package-v1",
            "bundle_signature": bundle["bundle_signature"],
            "model_signature": bundle["model_fingerprint"]["signature"],
            "target_environment_signature": target["environment"]["signature"],
            "experiment_config": bundle["experiment_config"],
            "trial_count": len(rows),
        }
    ) + b"\n"
    manifest_payloads = [encode_manifest(row_manifest(row)) for row in rows]
    trace_payloads = [full_trace_bytes(row["reference_token_ids"]) for row in rows]
    trial_headers = [trial_header(row) for row in rows]
    referenced_header = encode_referenced_package_header(
        bundle_signature=bundle["bundle_signature"],
        model_signature=bundle["model_fingerprint"]["signature"],
        environment_signature=target["environment"]["signature"],
    )
    compact_manifest_records = [
        encode_trial_record(
            prompt_index=int(row["prompt_index"]),
            seed=int(row["seed"]),
            policy=str(row["policy"]),
            token_count=int(row["token_count"]),
            reference_token_sha256=str(row["reference_token_sha256"]),
            payload=payload,
        )
        for row, payload in zip(rows, manifest_payloads, strict=True)
    ]
    compact_trace_records = [
        encode_trial_record(
            prompt_index=int(row["prompt_index"]),
            seed=int(row["seed"]),
            policy=str(row["policy"]),
            token_count=int(row["token_count"]),
            reference_token_sha256=str(row["reference_token_sha256"]),
            payload=payload,
        )
        for row, payload in zip(rows, trace_payloads, strict=True)
    ]

    manifest_payload_bytes = sum(map(len, manifest_payloads))
    full_trace_payload_bytes = sum(map(len, trace_payloads))
    identity_header_bytes = sum(map(len, trial_headers))
    shared_header_bytes = len(shared_header)
    certificate_package_bytes = (
        shared_header_bytes + identity_header_bytes + manifest_payload_bytes
    )
    full_trace_package_bytes = shared_header_bytes + identity_header_bytes + full_trace_payload_bytes
    referenced_certificate_bytes = len(referenced_header) + sum(
        map(len, compact_manifest_records)
    )
    referenced_full_trace_bytes = len(referenced_header) + sum(map(len, compact_trace_records))
    token_count = sum(int(row["token_count"]) for row in rows)
    corrections = sum(int(row["correction_count"]) for row in rows)

    required_timing = (
        "manifest_construction_seconds",
        "corrected_replay_seconds",
        "uncorrected_replay_seconds",
    )
    timing_available = all(all(field in row for field in required_timing) for row in rows)
    timing: dict[str, Any] = {"available": timing_available}
    if timing_available:
        timing.update(
            {
                "manifest_construction_seconds": sum(
                    float(row["manifest_construction_seconds"]) for row in rows
                ),
                "corrected_replay_seconds": sum(
                    float(row["corrected_replay_seconds"]) for row in rows
                ),
                "uncorrected_replay_seconds": sum(
                    float(row["uncorrected_replay_seconds"]) for row in rows
                ),
            }
        )
        timing["manifest_tokens_per_second"] = token_count / timing[
            "manifest_construction_seconds"
        ]
        timing["corrected_replay_tokens_per_second"] = token_count / timing[
            "corrected_replay_seconds"
        ]
        timing["uncorrected_replay_tokens_per_second"] = token_count / timing[
            "uncorrected_replay_seconds"
        ]

    return {
        "schema": "precision-replay-cost-analysis-v1",
        "trials": len(rows),
        "tokens": token_count,
        "corrections": corrections,
        "corrected_exact": sum(bool(row["corrected_exact"]) for row in rows),
        "uncorrected_exact": sum(bool(row["uncorrected_exact"]) for row in rows),
        "mean_trial_correction_rate": mean(float(row["correction_rate"]) for row in rows),
        "serialization": {
            "shared_header_bytes": shared_header_bytes,
            "identity_header_bytes": identity_header_bytes,
            "manifest_payload_bytes": manifest_payload_bytes,
            "full_trace_payload_bytes": full_trace_payload_bytes,
            "certificate_package_bytes": certificate_package_bytes,
            "full_trace_package_bytes": full_trace_package_bytes,
            "payload_ratio": manifest_payload_bytes / full_trace_payload_bytes,
            "complete_package_ratio": certificate_package_bytes / full_trace_package_bytes,
            "referenced_header_bytes": len(referenced_header),
            "referenced_certificate_bytes": referenced_certificate_bytes,
            "referenced_full_trace_bytes": referenced_full_trace_bytes,
            "referenced_package_ratio": referenced_certificate_bytes
            / referenced_full_trace_bytes,
            "certificate_bits_per_token": 8 * certificate_package_bytes / token_count,
            "referenced_certificate_bits_per_token": 8
            * referenced_certificate_bytes
            / token_count,
            "mean_certificate_bytes_per_trial": certificate_package_bytes / len(rows),
        },
        "timing": timing,
    }


def markdown_report(result: dict[str, Any], bundle_path: Path, target_path: Path) -> str:
    serial = result["serialization"]
    timing = result["timing"]
    lines = [
        "# R049 Complete Replay Cost Analysis",
        "",
        "## Material Passport",
        "",
        "- Origin Skill: academic-research-suite `experiment-agent`",
        "- Origin Mode: validate",
        "- Verification Status: ANALYZED",
        f"- Reference bundle: `{bundle_path}`",
        f"- Target report: `{target_path}`",
        "",
        "## Results",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Trials | {result['trials']} |",
        f"| Generated tokens | {result['tokens']} |",
        f"| Corrections | {result['corrections']} |",
        f"| Corrected exact | {result['corrected_exact']}/{result['trials']} |",
        f"| Uncorrected exact | {result['uncorrected_exact']}/{result['trials']} |",
        f"| Mean trial correction rate | {result['mean_trial_correction_rate']:.4%} |",
        f"| Binary manifest payload | {serial['manifest_payload_bytes']:,} bytes |",
        f"| Binary full token trace | {serial['full_trace_payload_bytes']:,} bytes |",
        f"| Payload-only ratio | {serial['payload_ratio']:.4%} |",
        f"| Complete certificate package | {serial['certificate_package_bytes']:,} bytes |",
        f"| Complete full-trace package | {serial['full_trace_package_bytes']:,} bytes |",
        f"| Complete-package ratio | {serial['complete_package_ratio']:.4%} |",
        f"| Complete certificate cost | {serial['certificate_bits_per_token']:.3f} bits/token |",
        f"| Referenced compact certificate | {serial['referenced_certificate_bytes']:,} bytes |",
        f"| Referenced compact full trace | {serial['referenced_full_trace_bytes']:,} bytes |",
        f"| Referenced compact ratio | {serial['referenced_package_ratio']:.4%} |",
        f"| Referenced compact cost | {serial['referenced_certificate_bits_per_token']:.3f} bits/token |",
    ]
    if timing["available"]:
        lines.extend(
            [
                f"| Manifest construction throughput | {timing['manifest_tokens_per_second']:.2f} tokens/s |",
                f"| Corrected replay throughput | {timing['corrected_replay_tokens_per_second']:.2f} tokens/s |",
                f"| Uncorrected replay throughput | {timing['uncorrected_replay_tokens_per_second']:.2f} tokens/s |",
            ]
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The payload-only ratio measures the versioned binary manifest against a varint full token trace.",
            "- The complete-package ratio additionally includes one shared contract header and one identity header per trial in both comparators.",
            "- The referenced compact ratio uses fixed SHA-256 identifiers for an externally shared reference bundle, model and target environment; it does not repeat the full JSON contract.",
            "- Certificate construction and corrected replay each require one target-model pass. The uncorrected pass is an evaluation baseline and is not part of operational replay.",
            "- Timing is hardware dependent and is not a cross-environment reproducibility metric.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    target = json.loads(args.target.read_text(encoding="utf-8"))
    result = analyze(bundle, target)
    result["sources"] = {
        "bundle": {"path": str(args.bundle), "sha256": file_sha256(args.bundle)},
        "target": {"path": str(args.target), "sha256": file_sha256(args.target)},
    }
    result["analysis_signature"] = hashlib.sha256(canonical_json_bytes(result)).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")
    args.markdown.write_text(markdown_report(result, args.bundle, args.target), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
