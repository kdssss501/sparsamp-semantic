"""Audit the distribution-free integer-apportionment term in replay artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from sparsamp_semantic.probability_contract import (  # noqa: E402
    support_preserving_tv_upper_bound,
)
from sparsamp_semantic.replay_package import file_sha256, write_atomic_json  # noqa: E402


def _mass_bits(counts: list[int]) -> int:
    total_mass = sum(counts)
    if total_mass < 1 or total_mass & (total_mass - 1):
        raise ValueError("contract counts must sum to a positive power of two")
    return total_mass.bit_length() - 1


def analyze(report: dict[str, Any]) -> dict[str, Any]:
    rows = report.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("replay report must contain rows")

    contracts: list[dict[str, Any]] = []
    for row in rows:
        row_contracts = row.get("reference_contracts")
        if not isinstance(row_contracts, list) or not row_contracts:
            raise ValueError("each replay row must contain reference_contracts")
        for contract in row_contracts:
            counts = [int(value) for value in contract["counts"]]
            if not counts or any(value <= 0 for value in counts):
                raise ValueError("support-preserving counts must be positive")
            bits = _mass_bits(counts)
            bound = support_preserving_tv_upper_bound(len(counts), mass_bits=bits)
            contracts.append(
                {
                    "candidate_count": len(counts),
                    "mass_bits": bits,
                    "tv_upper_bound": float(bound),
                    "tv_upper_bound_fraction": f"{bound.numerator}/{bound.denominator}",
                    "quantization_tv": float(contract["quantization_tv"]),
                    "truncation_reverse_kl_nats": float(
                        contract["contract_truncation_kl_nats"]
                    ),
                }
            )

    candidate_counts = sorted({item["candidate_count"] for item in contracts})
    mass_bits = sorted({item["mass_bits"] for item in contracts})
    bounds = [item["tv_upper_bound"] for item in contracts]
    quantization_tv = [item["quantization_tv"] for item in contracts]
    truncation = [item["truncation_reverse_kl_nats"] for item in contracts]
    return {
        "schema": "integer-apportionment-audit-v1",
        "trials": len(rows),
        "contracts": len(contracts),
        "candidate_counts": candidate_counts,
        "mass_bits": mass_bits,
        "apportionment": {
            "max_tv_upper_bound": max(bounds),
            "mean_tv_upper_bound": mean(bounds),
            "bound_type": "strict distribution-free upper bound for base support-preserving largest-remainder allocation",
            "uniform_kl_bound": None,
            "kl_note": "No finite distribution-free KL bound exists without a lower bound on target probabilities.",
        },
        "context": {
            "mean_full_logit_quantization_tv": mean(quantization_tv),
            "max_full_logit_quantization_tv": max(quantization_tv),
            "mean_truncation_reverse_kl_nats": mean(truncation),
        },
    }


def markdown_report(result: dict[str, Any], source: Path) -> str:
    apportionment = result["apportionment"]
    context = result["context"]
    return "\n".join(
        [
            "# R050 Integer Apportionment Audit",
            "",
            "## Material Passport",
            "",
            "- Origin: Stage 4 response to methodology/domain review",
            "- Verification status: ANALYZED",
            f"- Source: `{source}`",
            f"- Source SHA-256: `{file_sha256(source)}`",
            "",
            "## Result",
            "",
            f"- Trials: {result['trials']}",
            f"- Token-level contracts: {result['contracts']}",
            f"- Candidate counts: {result['candidate_counts']}",
            f"- Integer mass bits: {result['mass_bits']}",
            f"- Maximum apportionment TV upper bound: {apportionment['max_tv_upper_bound']:.10f}",
            f"- Mean recorded full-logit quantization TV: {context['mean_full_logit_quantization_tv']:.10f}",
            f"- Mean recorded support-truncation reverse KL: {context['mean_truncation_reverse_kl_nats']:.10f} nats/token",
            "",
            "## Interpretation",
            "",
            "For k positive candidates and integer mass M, the base allocator reserves one count per candidate and applies largest remainder to M-k counts. Each positive coordinate error is strictly below 2/M, and at most k-1 coordinates can have positive error because coordinate errors sum to zero. Therefore TV is strictly below 2(k-1)/M.",
            "",
            "This bound isolates the integer-apportionment component without pretending that KL components with different directions are additive. A finite distribution-free KL bound is impossible unless every pre-apportionment target probability has a public positive lower bound. The bound applies to both reference and target allocations with the same k and M; it does not measure support truncation or full-logit quantization.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    result = analyze(report)
    result["source"] = {"path": str(args.input), "sha256": file_sha256(args.input)}
    write_atomic_json(args.output, result)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown_report(result, args.input), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
