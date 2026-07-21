"""Compare R052 unquantized deltas with the matched SPRC target report."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.analyze_replay_ablations import percentile  # noqa: E402
from sparsamp_semantic.replay_package import file_sha256, write_atomic_json  # noqa: E402


def key(row: dict[str, Any]) -> tuple[int, int, str]:
    return int(row["prompt_index"]), int(row["seed"]), str(row["policy"])


def paired_interval(
    differences: dict[int, float], *, repetitions: int, seed: int
) -> tuple[float, float]:
    prompt_ids = sorted(differences)
    if len(prompt_ids) < 2 or repetitions < 1:
        raise ValueError("paired bootstrap requires at least two prompts")
    generator = random.Random(seed)
    estimates = [
        mean(differences[generator.choice(prompt_ids)] for _ in prompt_ids)
        for _ in range(repetitions)
    ]
    return percentile(estimates, 0.025), percentile(estimates, 0.975)


def analyze(
    sprc: dict[str, Any],
    unquantized: dict[str, Any],
    *,
    repetitions: int = 10_000,
    seed: int = 20260721,
) -> dict[str, Any]:
    if sprc.get("phase") != "completed" or unquantized.get("phase") != "completed":
        raise ValueError("both source reports must be completed")
    sprc_rows = {key(row): row for row in sprc["rows"]}
    unquantized_rows = {key(row): row for row in unquantized["rows"]}
    if sprc_rows.keys() != unquantized_rows.keys() or len(sprc_rows) < 2:
        raise ValueError("source reports must contain the same unique trials")
    for trial in sprc_rows:
        if (
            sprc_rows[trial]["reference_token_sha256"]
            != unquantized_rows[trial]["reference_token_sha256"]
        ):
            raise ValueError("reference token identity mismatch")

    sprc_mean = mean(float(row["correction_rate"]) for row in sprc_rows.values())
    variants: dict[str, Any] = {}
    for variant, summary in unquantized["summary"].items():
        differences = {
            trial[0]: (
                float(unquantized_rows[trial]["variants"][variant]["correction_rate"])
                - float(sprc_rows[trial]["correction_rate"])
            )
            for trial in sprc_rows
        }
        low, high = paired_interval(
            differences, repetitions=repetitions, seed=seed + int(variant.split("_")[1])
        )
        variants[variant] = {
            "trials": int(summary["trials"]),
            "tokens": int(summary["tokens"]),
            "exact_recovery": int(summary["exact_recovery"]),
            "mean_correction_rate": float(summary["mean_correction_rate"]),
            "sprc_mean_correction_rate": sprc_mean,
            "correction_rate_delta_vs_sprc": mean(differences.values()),
            "paired_prompt_ci95": [low, high],
            "referenced_package_bytes": int(summary["referenced_package_bytes"]),
            "package_byte_delta_vs_sprc": int(summary["referenced_package_bytes"])
            - 1148,
            "bits_per_token": float(summary["bits_per_token"]),
            "support_shortfall_steps": int(summary["support_shortfall_steps"]),
            "reference_outside_support_steps": int(
                summary["reference_outside_support_steps"]
            ),
            "minimum_available_support": int(summary["minimum_available_support"]),
        }

    return {
        "schema": "unquantized-target-delta-analysis-v1",
        "bootstrap_repetitions": repetitions,
        "bootstrap_seed": seed,
        "matched_trials": len(sprc_rows),
        "matched_reference_tokens": sum(
            int(row["token_count"]) for row in sprc_rows.values()
        ),
        "sprc": {
            "mean_correction_rate": sprc_mean,
            "referenced_package_bytes": 1148,
            "bits_per_token": 6.1226666666666665,
        },
        "variants": variants,
    }


def markdown_report(
    result: dict[str, Any], sprc_path: Path, unquantized_path: Path
) -> str:
    lines = [
        "# R052 Unquantized Delta Analysis",
        "",
        "## Material Passport",
        "",
        "- Origin: Stage 4 direct mechanism baseline",
        "- Verification status: ANALYZED",
        f"- SPRC target report: {sprc_path}",
        f"- SPRC SHA-256: {file_sha256(sprc_path)}",
        f"- Unquantized report: {unquantized_path}",
        f"- Unquantized SHA-256: {file_sha256(unquantized_path)}",
        f"- Paired prompt bootstrap: {result['bootstrap_repetitions']:,} resamples",
        f"- Bootstrap seed: {result['bootstrap_seed']}",
        "",
        "## Results",
        "",
        "| Method | Exact | Mean correction rate | Delta vs SPRC [95% CI] | Referenced bytes | Bits/token | Support shortfall |",
        "|---|---:|---:|---:|---:|---:|---:|",
        (
            f"| SPRC | 20/20 | {100 * result['sprc']['mean_correction_rate']:.3f}% | "
            f"reference | {result['sprc']['referenced_package_bytes']:,} | "
            f"{result['sprc']['bits_per_token']:.3f} | 0 |"
        ),
    ]
    for name, item in result["variants"].items():
        ci = item["paired_prompt_ci95"]
        lines.append(
            f"| {name.replace('_', '-')} | {item['exact_recovery']}/{item['trials']} | "
            f"{100 * item['mean_correction_rate']:.3f}% | "
            f"{100 * item['correction_rate_delta_vs_sprc']:+.3f} pp "
            f"[{100 * ci[0]:+.3f}, {100 * ci[1]:+.3f}] | "
            f"{item['referenced_package_bytes']:,} | {item['bits_per_token']:.3f} | "
            f"{item['support_shortfall_steps']} |"
        )
    top2 = result["variants"]["top_2"]
    top16 = result["variants"]["top_16"]
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- Removing logit-bin and integer-mass contracts while retaining top-2 increased mean correction rate by {100 * top2['correction_rate_delta_vs_sprc']:.3f} percentage points; its paired interval is [{100 * top2['paired_prompt_ci95'][0]:+.3f}, {100 * top2['paired_prompt_ci95'][1]:+.3f}].",
            f"- The unquantized top-2 package was {top2['package_byte_delta_vs_sprc']:+d} bytes relative to SPRC under the same referenced boundary.",
            f"- Expanding to a positive-support top-16 cap increased correction density to {100 * top16['mean_correction_rate']:.3f}% and produced {top16['support_shortfall_steps']} finite-precision support-shortfall step.",
            "- Exact recovery remains a manifest integrity property for every method and is not used to claim statistical superiority.",
            "- This is one BF16 target stack and one public seed per prompt; the interval describes the frozen prompt set.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sprc", type=Path, required=True)
    parser.add_argument("--unquantized", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--bootstrap-repetitions", type=int, default=10_000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260721)
    args = parser.parse_args()

    sprc = json.loads(args.sprc.read_text(encoding="utf-8"))
    unquantized = json.loads(args.unquantized.read_text(encoding="utf-8"))
    result = analyze(
        sprc,
        unquantized,
        repetitions=args.bootstrap_repetitions,
        seed=args.bootstrap_seed,
    )
    result["source"] = {
        "sprc": {"path": str(args.sprc), "sha256": file_sha256(args.sprc)},
        "unquantized": {
            "path": str(args.unquantized),
            "sha256": file_sha256(args.unquantized),
        },
    }
    write_atomic_json(args.output, result)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(
        markdown_report(result, args.sprc, args.unquantized), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
