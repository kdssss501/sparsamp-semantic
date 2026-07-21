"""Compare replay records under one referenced-package boundary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.analyze_replay_cost import full_trace_bytes, row_manifest  # noqa: E402
from sparsamp_semantic.certificate_format import (  # noqa: E402
    encode_manifest,
    encode_referenced_package_header,
    encode_trial_record,
    encode_uvarint,
)
from sparsamp_semantic.replay_package import (  # noqa: E402
    file_sha256,
    validate_reference_bundle,
    write_atomic_json,
)


BLOCK_MAGIC = b"SPRB\x01"


def block_repair_payload(row: dict[str, Any], block_size: int) -> bytes:
    """Store complete reference blocks containing at least one correction."""

    if block_size < 1:
        raise ValueError("block_size must be positive")
    token_ids = [int(value) for value in row["reference_token_ids"]]
    dirty_blocks = sorted(
        {int(item["step"]) // block_size for item in row["corrections"]}
    )
    output = bytearray(BLOCK_MAGIC)
    output.extend(encode_uvarint(len(token_ids)))
    output.extend(encode_uvarint(block_size))
    output.extend(encode_uvarint(len(dirty_blocks)))
    for block_index in dirty_blocks:
        start = block_index * block_size
        block = token_ids[start : start + block_size]
        if not block:
            raise ValueError("correction step lies outside the reference trace")
        output.extend(encode_uvarint(block_index))
        output.extend(encode_uvarint(len(block)))
        for token_id in block:
            output.extend(encode_uvarint(token_id))
    return bytes(output)


def _record(row: dict[str, Any], payload: bytes) -> bytes:
    return encode_trial_record(
        prompt_index=int(row["prompt_index"]),
        seed=int(row["seed"]),
        policy=str(row["policy"]),
        token_count=int(row["token_count"]),
        reference_token_sha256=str(row["reference_token_sha256"]),
        payload=payload,
    )


def analyze(
    bundle: dict[str, Any],
    target: dict[str, Any],
    *,
    block_sizes: tuple[int, ...] = (4, 8, 16, 32),
) -> dict[str, Any]:
    validate_reference_bundle(bundle)
    if target.get("phase") != "completed":
        raise ValueError("target replay report must be completed")
    if target["experiment_config"]["bundle_signature"] != bundle["bundle_signature"]:
        raise ValueError("target report does not belong to the reference bundle")
    rows = target.get("rows")
    if not isinstance(rows, list) or len(rows) != len(bundle["rows"]):
        raise ValueError("target report trial count does not match the bundle")
    if len(set(block_sizes)) != len(block_sizes) or any(value < 1 for value in block_sizes):
        raise ValueError("block sizes must be unique positive integers")

    header = encode_referenced_package_header(
        bundle_signature=bundle["bundle_signature"],
        model_signature=bundle["model_fingerprint"]["signature"],
        environment_signature=target["environment"]["signature"],
    )
    token_count = sum(int(row["token_count"]) for row in rows)
    full_trace_payloads = [full_trace_bytes(row["reference_token_ids"]) for row in rows]
    full_trace_records = [
        _record(row, payload)
        for row, payload in zip(rows, full_trace_payloads, strict=True)
    ]
    full_trace_package = len(header) + sum(map(len, full_trace_records))

    def summarize(
        name: str,
        payloads: list[bytes],
        *,
        exact_successes: int,
        target_passes_per_trial: int,
        target_specific: bool,
    ) -> dict[str, Any]:
        package_bytes = len(header) + sum(
            len(_record(row, payload))
            for row, payload in zip(rows, payloads, strict=True)
        )
        return {
            "name": name,
            "exact_successes": exact_successes,
            "trials": len(rows),
            "payload_bytes": sum(map(len, payloads)),
            "referenced_package_bytes": package_bytes,
            "ratio_to_referenced_full_trace": package_bytes / full_trace_package,
            "bits_per_token": 8 * package_bytes / token_count,
            "target_model_passes_per_trial": target_passes_per_trial,
            "target_specific": target_specific,
        }

    baselines = [
        summarize(
            "seed_only",
            [b"" for _ in rows],
            exact_successes=sum(bool(row["uncorrected_exact"]) for row in rows),
            target_passes_per_trial=1,
            target_specific=False,
        ),
        summarize(
            "sparse_precision_replay_certificate",
            [encode_manifest(row_manifest(row)) for row in rows],
            exact_successes=sum(bool(row["corrected_exact"]) for row in rows),
            target_passes_per_trial=2,
            target_specific=True,
        ),
        summarize(
            "full_token_trace",
            full_trace_payloads,
            exact_successes=len(rows),
            target_passes_per_trial=0,
            target_specific=False,
        ),
    ]
    for block_size in block_sizes:
        baselines.append(
            summarize(
                f"block_repair_{block_size}",
                [block_repair_payload(row, block_size) for row in rows],
                exact_successes=sum(bool(row["corrected_exact"]) for row in rows),
                target_passes_per_trial=2,
                target_specific=True,
            )
        )

    return {
        "schema": "precision-replay-baseline-analysis-v1",
        "trials": len(rows),
        "tokens": token_count,
        "referenced_header_bytes": len(header),
        "baselines": baselines,
        "missing_baselines": [
            {
                "name": "native_softmax_target_conditioned_delta",
                "reason": "Requires a new GPU run that samples the unquantized native distribution on each frozen reference prefix; current artifacts do not store those choices.",
            }
        ],
        "interpretation": {
            "common_boundary": "All byte results use the same referenced header and per-trial identity record.",
            "block_repair": "A block baseline stores every reference token in each fixed block containing at least one SPRC correction; it is exact under the same target-conditioned assumptions but coarser than token-level repair.",
            "compute": "Pass counts are logical target-model passes; block repair may skip generation inside stored blocks but that optimization is not timed here.",
        },
    }


def markdown_report(result: dict[str, Any], bundle: Path, target: Path) -> str:
    lines = [
        "# R051 Matched Replay Baselines",
        "",
        "## Material Passport",
        "",
        "- Origin: Stage 4 response to EIC/domain review",
        "- Verification status: ANALYZED",
        f"- Reference bundle: `{bundle}`",
        f"- Reference SHA-256: `{file_sha256(bundle)}`",
        f"- Target report: `{target}`",
        f"- Target SHA-256: `{file_sha256(target)}`",
        "",
        "## Results",
        "",
        "| Method | Exact | Referenced bytes | Full-trace ratio | Bits/token | Target passes | Target-specific |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for item in result["baselines"]:
        lines.append(
            f"| {item['name']} | {item['exact_successes']}/{item['trials']} | "
            f"{item['referenced_package_bytes']:,} | "
            f"{100 * item['ratio_to_referenced_full_trace']:.2f}% | "
            f"{item['bits_per_token']:.3f} | "
            f"{item['target_model_passes_per_trial']} | "
            f"{'yes' if item['target_specific'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Missing Baseline",
            "",
            f"- `{result['missing_baselines'][0]['name']}`: {result['missing_baselines'][0]['reason']}",
            "",
            "## Interpretation",
            "",
            f"- {result['interpretation']['common_boundary']}",
            f"- {result['interpretation']['block_repair']}",
            f"- {result['interpretation']['compute']}",
            "- Seed-only is the zero-payload stochastic replay control and is not exact for most trials.",
            "- Full trace is target-independent and exact, but it bypasses model replay; its zero-pass property must be considered alongside byte cost.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--block-sizes", type=int, nargs="+", default=[4, 8, 16, 32])
    args = parser.parse_args()

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    target = json.loads(args.target.read_text(encoding="utf-8"))
    result = analyze(bundle, target, block_sizes=tuple(args.block_sizes))
    result["source"] = {
        "bundle": {"path": str(args.bundle), "sha256": file_sha256(args.bundle)},
        "target": {"path": str(args.target), "sha256": file_sha256(args.target)},
    }
    write_atomic_json(args.output, result)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown_report(result, args.bundle, args.target), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
