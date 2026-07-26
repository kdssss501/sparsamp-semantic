"""Analyze the preregistered R053 q/T/B sensitivity checkpoints."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.analyze_replay_ablations import (  # noqa: E402
    compare_variants,
    deterministic_signature,
    load_complete_rows,
    summarize_variant,
)
from scripts.analyze_replay_cost import row_manifest  # noqa: E402
from sparsamp_semantic.certificate_format import (  # noqa: E402
    encode_manifest,
    encode_trial_record,
)


REFERENCED_HEADER_BYTES = 101


def referenced_package_bytes(rows: list[dict[str, Any]]) -> int:
    """Return compact manifest bytes under the frozen referenced boundary."""

    total = REFERENCED_HEADER_BYTES
    for row in rows:
        total += len(
            encode_trial_record(
                prompt_index=int(row["prompt_index"]),
                seed=int(row["seed"]),
                policy=str(row["policy"]),
                token_count=int(row["token_count"]),
                reference_token_sha256=str(row["reference_token_sha256"]),
                payload=encode_manifest(row_manifest(row)),
            )
        )
    return total


def parse_variant(value: str) -> tuple[str, Path]:
    name, separator, path = value.partition("=")
    if not separator or not name or not path:
        raise argparse.ArgumentTypeError("variant must use NAME=PATH")
    return name, Path(path)


def analyze(
    baseline_path: Path,
    variants: dict[str, Path],
    *,
    selected_seed: int = 0,
    bootstrap: int = 10_000,
    bootstrap_seed: int = 20260723,
) -> dict[str, Any]:
    if not variants:
        raise ValueError("at least one sensitivity variant is required")
    loaded_baseline = load_complete_rows(baseline_path, selected_seed)
    loaded_variants = {
        name: load_complete_rows(path, selected_seed) for name, path in variants.items()
    }
    all_loaded = {"baseline": loaded_baseline, **loaded_variants}
    summaries: dict[str, Any] = {}
    for index, (name, (report, rows)) in enumerate(all_loaded.items()):
        summary = summarize_variant(
            report, rows, bootstrap, bootstrap_seed + index * 100
        )
        summary["parameters"] = {
            key: report["experiment_config"][key]
            for key in ("contract_top_k", "logit_quantum", "mass_bits", "temperature")
        }
        summary["referenced_package_bytes"] = referenced_package_bytes(rows)
        summary["referenced_bits_per_token"] = (
            8 * summary["referenced_package_bytes"] / summary["tokens"]
        )
        summaries[name] = summary

    comparisons: dict[str, Any] = {}
    baseline_rows = loaded_baseline[1]
    for index, (name, (_, rows)) in enumerate(loaded_variants.items()):
        comparison = compare_variants(
            baseline_rows, rows, bootstrap, bootstrap_seed + 1000 + index * 100
        )
        comparison["referenced_package_byte_delta"] = (
            summaries[name]["referenced_package_bytes"]
            - summaries["baseline"]["referenced_package_bytes"]
        )
        comparisons[f"{name}_minus_baseline"] = comparison

    sources = {
        "baseline": baseline_path,
        **variants,
    }
    result = {
        "schema": "r053-qtb-sensitivity-analysis-v1",
        "selected_seed": selected_seed,
        "bootstrap_repetitions": bootstrap,
        "bootstrap_seed": bootstrap_seed,
        "referenced_header_bytes": REFERENCED_HEADER_BYTES,
        "sources": {
            name: {
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for name, path in sources.items()
        },
        "variants": summaries,
        "comparisons": comparisons,
    }
    result["analysis_signature"] = deterministic_signature(result)
    return result


def markdown_report(result: dict[str, Any]) -> str:
    lines = [
        "# R053 Bounded q/T/B Sensitivity",
        "",
        "## Material Passport",
        "",
        "- Verification status: ANALYZED",
        f"- Selected public seed: {result['selected_seed']}",
        f"- Prompt bootstrap: {result['bootstrap_repetitions']:,} resamples",
        f"- Analysis signature: `{result['analysis_signature']}`",
        "",
        "## Results",
        "",
        "| Variant | q | T | B | Exact | Correction rate | Delta vs baseline (95% CI) | Source mass | Referenced bytes |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    baseline = result["variants"]["baseline"]
    for name, value in result["variants"].items():
        parameters = value["parameters"]
        rate = value["metrics"]["correction_rate"]["value"]
        if name == "baseline":
            delta_text = "reference"
        else:
            delta = result["comparisons"][f"{name}_minus_baseline"]["deltas"][
                "correction_rate"
            ]
            low, high = delta["paired_cluster_ci95"]
            delta_text = (
                f"{delta['candidate_minus_baseline']:+.4f} "
                f"[{low:+.4f}, {high:+.4f}]"
            )
        lines.append(
            f"| {name} | {parameters['logit_quantum']} | "
            f"{parameters['temperature']} | {parameters['mass_bits']} | "
            f"{value['corrected_exact']}/{value['trials']} | {rate:.4f} | "
            f"{delta_text} | "
            f"{value['metrics']['contract_source_mass']['value']:.4f} | "
            f"{value['referenced_package_bytes']:,} |"
        )

    best_name, best = min(
        result["variants"].items(),
        key=lambda item: item[1]["metrics"]["correction_rate"]["value"],
    )
    best_delta = (
        None
        if best_name == "baseline"
        else result["comparisons"][f"{best_name}_minus_baseline"]["deltas"][
            "correction_rate"
        ]
    )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- All {sum(v['trials'] for v in result['variants'].values())} analyzed trials passed the corrected-exact integrity gate.",
            f"- The lowest observed correction density was `{best_name}` at {best['metrics']['correction_rate']['value']:.4%}.",
        ]
    )
    if best_delta is not None:
        low, high = best_delta["paired_cluster_ci95"]
        lines.append(
            f"- Its paired change from baseline was {best_delta['candidate_minus_baseline']:+.4%} "
            f"(prompt-bootstrap 95% CI {low:+.4%} to {high:+.4%})."
        )
    lines.extend(
        [
            f"- Baseline referenced size was {baseline['referenced_package_bytes']:,} bytes; byte differences include changed trajectory lengths and manifests.",
            "- This bounded one-seed OFAT study identifies local sensitivity, not a global optimum.",
            "",
            "## Interpretation Boundary",
            "",
            "Parameter changes participate in reference sampling, so comparisons are paired by prompt and public seed rather than by identical token trajectory. Exact recovery remains a protocol gate. Correction density, retained mass and package bytes are empirical outcomes for one model and GPU stack.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--variant", action="append", type=parse_variant, required=True)
    parser.add_argument("--selected-seed", type=int, default=0)
    parser.add_argument("--bootstrap", type=int, default=10_000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260723)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()
    variants = dict(args.variant)
    if len(variants) != len(args.variant):
        raise ValueError("variant names must be unique")
    result = analyze(
        args.baseline,
        variants,
        selected_seed=args.selected_seed,
        bootstrap=args.bootstrap,
        bootstrap_seed=args.bootstrap_seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")
    args.markdown.write_text(markdown_report(result), encoding="utf-8")
    print(json.dumps(result["variants"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
