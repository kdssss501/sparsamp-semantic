"""Compare the official SparSamp GPT-2 matrix with published Tables 2-4."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable


PAPER_TABLE2 = {
    2: {"utilization": 0.275, "embedding_speed_bits_s": 214.7, "decoding_speed_bits_s": 203.7},
    4: {"utilization": 0.447, "embedding_speed_bits_s": 358.4, "decoding_speed_bits_s": 339.7},
    8: {"utilization": 0.645, "embedding_speed_bits_s": 504.0, "decoding_speed_bits_s": 477.7},
    16: {"utilization": 0.788, "embedding_speed_bits_s": 640.4, "decoding_speed_bits_s": 606.7},
    32: {"utilization": 0.873, "embedding_speed_bits_s": 705.1, "decoding_speed_bits_s": 667.3},
    64: {"utilization": 0.974, "embedding_speed_bits_s": 755.4, "decoding_speed_bits_s": 715.6},
    128: {"utilization": 0.980, "embedding_speed_bits_s": 731.0, "decoding_speed_bits_s": 699.6},
    256: {"utilization": 0.985, "embedding_speed_bits_s": 656.3, "decoding_speed_bits_s": 629.9},
    512: {"utilization": 0.987, "embedding_speed_bits_s": 709.7, "decoding_speed_bits_s": 678.0},
    1023: {"utilization": 0.995, "embedding_speed_bits_s": 706.0, "decoding_speed_bits_s": 672.4},
}

PAPER_TOP_P = {
    0.8: {
        "embedding_rate": 3.60,
        "utilization": 0.953,
        "sampling_atst_s_token": 1.53e-4,
        "sampling_to_inference_ratio": 0.02,
        "generation_speed_tokens_s": 125.8,
        "embedding_speed_bits_s": 461.7,
        "decoding_speed_bits_s": 421.4,
    },
    0.95: {
        "embedding_rate": 5.16,
        "utilization": 0.949,
        "sampling_atst_s_token": 1.57e-4,
        "sampling_to_inference_ratio": 0.02,
        "generation_speed_tokens_s": 130.6,
        "embedding_speed_bits_s": 628.2,
        "decoding_speed_bits_s": 560.4,
    },
    1.0: {
        "embedding_rate": 5.98,
        "utilization": 0.974,
        "sampling_atst_s_token": 7.21e-4,
        "sampling_to_inference_ratio": 0.11,
        "generation_speed_tokens_s": 132.3,
        "embedding_speed_bits_s": 755.4,
        "decoding_speed_bits_s": 715.6,
    },
}

MetricParts = Callable[[list[dict[str, Any]]], tuple[float, float]]


def percentile(values: list[float], probability: float) -> float:
    if not values or not 0 <= probability <= 1:
        raise ValueError("percentile requires values and a probability in [0, 1]")
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def ratio_parts(rows: list[dict[str, Any]], numerator: str, denominator: str) -> tuple[float, float]:
    return sum(float(row[numerator]) for row in rows), sum(
        float(row[denominator]) for row in rows
    )


METRICS: dict[str, MetricParts] = {
    "embedding_rate": lambda rows: ratio_parts(rows, "encoded_bits", "token_count"),
    "utilization": lambda rows: ratio_parts(rows, "encoded_bits", "entropy_bits"),
    "embedding_speed_bits_s": lambda rows: ratio_parts(
        rows, "encoded_bits", "generation_seconds"
    ),
    "decoding_speed_bits_s": lambda rows: ratio_parts(rows, "encoded_bits", "decode_seconds"),
    "sampling_atst_s_token": lambda rows: ratio_parts(
        rows, "sampling_seconds", "token_count"
    ),
    "sampling_to_inference_ratio": lambda rows: ratio_parts(
        rows, "sampling_seconds", "model_seconds"
    ),
    "generation_speed_tokens_s": lambda rows: ratio_parts(
        rows, "token_count", "generation_seconds"
    ),
}


def aggregate_metric(rows: list[dict[str, Any]], metric: str) -> float:
    numerator, denominator = METRICS[metric](rows)
    if denominator <= 0:
        raise ValueError(f"non-positive denominator for {metric}")
    return numerator / denominator


def bootstrap_metric(
    rows: list[dict[str, Any]], metric: str, repetitions: int, seed: int
) -> tuple[float, float]:
    if len(rows) < 2 or repetitions < 1:
        raise ValueError("bootstrap requires at least two rows and one repetition")
    generator = random.Random(seed)
    estimates = []
    for _ in range(repetitions):
        sample = [generator.choice(rows) for _ in rows]
        estimates.append(aggregate_metric(sample, metric))
    return percentile(estimates, 0.025), percentile(estimates, 0.975)


def relative_error(observed: float, published: float) -> float:
    if published == 0:
        raise ValueError("published comparator must be non-zero")
    return abs(observed - published) / abs(published)


def analyze_report(
    report: dict[str, Any], *, repetitions: int, seed: int, capacity_tolerance: float
) -> dict[str, Any]:
    expected = int(report["progress"]["expected_trials"])
    rows = report.get("rows", [])
    if report.get("phase") != "completed" or len(rows) != expected:
        raise ValueError("official reproduction report is incomplete")
    if any(row.get("status") not in {"completed", "budget_exhausted"} for row in rows):
        raise ValueError("official reproduction report contains non-terminal trials")

    grouped: dict[tuple[int, float], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["block_size"]), float(row["top_p"])].append(row)

    configurations = []
    capacity_checks = []
    all_decode_success = True
    for index, ((block_size, top_p), selected) in enumerate(sorted(grouped.items())):
        completed = [row for row in selected if row["status"] == "completed"]
        eligible = [row for row in completed if not bool(row["token_ambiguity"])]
        if len(eligible) < 2:
            raise ValueError(f"configuration {(block_size, top_p)} has insufficient eligible trials")
        decode_success = sum(bool(row["decode_success"]) for row in eligible)
        all_decode_success &= decode_success == len(eligible)
        metrics = {}
        for offset, metric in enumerate(METRICS):
            low, high = bootstrap_metric(
                eligible, metric, repetitions, seed + index * 100 + offset
            )
            metrics[metric] = {
                "value": aggregate_metric(eligible, metric),
                "bootstrap_ci95": [low, high],
            }
        published = {}
        if top_p == 1.0 and block_size in PAPER_TABLE2:
            published["paper_table2"] = PAPER_TABLE2[block_size]
            error = relative_error(metrics["utilization"]["value"], PAPER_TABLE2[block_size]["utilization"])
            capacity_checks.append(
                {
                    "source": "paper_table2",
                    "block_size": block_size,
                    "top_p": top_p,
                    "metric": "utilization",
                    "relative_error": error,
                    "pass": error <= capacity_tolerance,
                }
            )
        if block_size == 64 and top_p in PAPER_TOP_P:
            published["paper_tables3_4"] = PAPER_TOP_P[top_p]
            for metric in ("embedding_rate", "utilization"):
                error = relative_error(metrics[metric]["value"], PAPER_TOP_P[top_p][metric])
                capacity_checks.append(
                    {
                        "source": "paper_table4",
                        "block_size": block_size,
                        "top_p": top_p,
                        "metric": metric,
                        "relative_error": error,
                        "pass": error <= capacity_tolerance,
                    }
                )
        configurations.append(
            {
                "block_size": block_size,
                "top_p": top_p,
                "trials": len(selected),
                "completed": len(completed),
                "budget_exhausted": sum(row["status"] == "budget_exhausted" for row in selected),
                "token_ambiguity": sum(bool(row["token_ambiguity"]) for row in completed),
                "eligible": len(eligible),
                "decode_success": decode_success,
                "metrics": metrics,
                "published": published,
            }
        )

    budget_exhausted = sum(item["budget_exhausted"] for item in configurations)
    completed_trials = sum(item["completed"] for item in configurations)
    overall_pass = all_decode_success and all(check["pass"] for check in capacity_checks)
    return {
        "schema": "sparsamp-official-reproduction-analysis-v1",
        "source_phase": report["phase"],
        "source_environment": report["environment"],
        "bootstrap_repetitions": repetitions,
        "bootstrap_seed": seed,
        "capacity_relative_error_tolerance": capacity_tolerance,
        "configurations": configurations,
        "acceptance": {
            "decode_without_token_ambiguity": {
                "pass": all_decode_success,
                "successes": sum(item["decode_success"] for item in configurations),
                "trials": sum(item["eligible"] for item in configurations),
            },
            "capacity_within_tolerance": {
                "pass": all(check["pass"] for check in capacity_checks),
                "passed": sum(check["pass"] for check in capacity_checks),
                "checks": len(capacity_checks),
                "details": capacity_checks,
            },
            "budget_completion": {
                "completed": completed_trials,
                "budget_exhausted": budget_exhausted,
                "configured": len(rows),
            },
            "overall_pass": overall_pass,
            "overall_status": (
                "PASS_WITH_LIMITATIONS" if overall_pass and budget_exhausted else (
                    "PASS" if overall_pass else "FAIL"
                )
            ),
        },
    }


def markdown_report(analysis: dict[str, Any]) -> str:
    acceptance = analysis["acceptance"]
    lines = [
        "# R002 Official SparSamp Matrix Reproduction",
        "",
        "## Scope",
        "",
        "This is a compatibility reproduction of the published GPT-2 protocol using the unchanged",
        "Zenodo 15025436 algorithm code with a modern CUDA-enabled PyTorch stack and Transformers",
        "4.41.2. It is not a strict recreation of the artifact's Torch 2.2.2 environment.",
        "",
        "## Results",
        "",
        "| block | top-p | complete | budget exhausted | TA | eligible | decode | bits/token | utilization (95% CI) | paper utilization | relative error |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    checks = {
        (item["block_size"], item["top_p"], item["metric"]): item
        for item in acceptance["capacity_within_tolerance"]["details"]
    }
    for item in analysis["configurations"]:
        metric = item["metrics"]
        util = metric["utilization"]
        published = None
        error = None
        key = (item["block_size"], item["top_p"], "utilization")
        if key in checks:
            error = checks[key]["relative_error"]
            if item["block_size"] == 64 and "paper_tables3_4" in item["published"]:
                published = item["published"]["paper_tables3_4"]["utilization"]
            elif "paper_table2" in item["published"]:
                published = item["published"]["paper_table2"]["utilization"]
        lines.append(
            f"| {item['block_size']} | {item['top_p']:.2f} | {item['completed']} | "
            f"{item['budget_exhausted']} | {item['token_ambiguity']} | {item['eligible']} | "
            f"{item['decode_success']}/{item['eligible']} | "
            f"{metric['embedding_rate']['value']:.3f} | {util['value']:.3f} "
            f"[{util['bootstrap_ci95'][0]:.3f}, {util['bootstrap_ci95'][1]:.3f}] | "
            f"{published:.3f} | {error:.2%} |"
        )
    decode = acceptance["decode_without_token_ambiguity"]
    capacity = acceptance["capacity_within_tolerance"]
    budget = acceptance["budget_completion"]
    lines.extend(
        [
            "",
            "## Acceptance",
            "",
            f"- Decode gate: **{'PASS' if decode['pass'] else 'FAIL'}**, "
            f"{decode['successes']}/{decode['trials']} eligible trials.",
            f"- Capacity gate: **{'PASS' if capacity['pass'] else 'FAIL'}**, "
            f"{capacity['passed']}/{capacity['checks']} comparisons within "
            f"{analysis['capacity_relative_error_tolerance']:.0%} relative error.",
            f"- Budget completion: {budget['completed']}/{budget['configured']} completed; "
            f"{budget['budget_exhausted']} trials did not finish a message block within the 200-token ceiling.",
            f"- Overall: **{acceptance['overall_status']}**.",
            "",
            "## Interpretation Boundaries",
            "",
            "- Token Ambiguity is reported separately and excluded from the paper's no-TA decoding denominator.",
            "- Bootstrap intervals resample IMDB contexts within each configuration.",
            "- Sampling and throughput values are descriptive because the reproduction GPU differs from the paper.",
            "- The unchanged algorithm source was used, but the compatibility environment does not establish strict",
            "  byte-for-byte reproducibility under the artifact's original dependency versions.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_csv(path: Path, analysis: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "block_size",
                "top_p",
                "completed",
                "budget_exhausted",
                "token_ambiguity",
                "eligible",
                "decode_success",
                "embedding_rate",
                "utilization",
                "utilization_ci95_low",
                "utilization_ci95_high",
                "sampling_atst_s_token",
                "sampling_to_inference_ratio",
                "generation_speed_tokens_s",
                "embedding_speed_bits_s",
                "decoding_speed_bits_s",
            ],
        )
        writer.writeheader()
        for item in analysis["configurations"]:
            metrics = item["metrics"]
            writer.writerow(
                {
                    "block_size": item["block_size"],
                    "top_p": item["top_p"],
                    "completed": item["completed"],
                    "budget_exhausted": item["budget_exhausted"],
                    "token_ambiguity": item["token_ambiguity"],
                    "eligible": item["eligible"],
                    "decode_success": item["decode_success"],
                    "embedding_rate": metrics["embedding_rate"]["value"],
                    "utilization": metrics["utilization"]["value"],
                    "utilization_ci95_low": metrics["utilization"]["bootstrap_ci95"][0],
                    "utilization_ci95_high": metrics["utilization"]["bootstrap_ci95"][1],
                    "sampling_atst_s_token": metrics["sampling_atst_s_token"]["value"],
                    "sampling_to_inference_ratio": metrics["sampling_to_inference_ratio"]["value"],
                    "generation_speed_tokens_s": metrics["generation_speed_tokens_s"]["value"],
                    "embedding_speed_bits_s": metrics["embedding_speed_bits_s"]["value"],
                    "decoding_speed_bits_s": metrics["decoding_speed_bits_s"]["value"],
                }
            )


def write_figure(path: Path, analysis: dict[str, Any]) -> None:
    """Write SVG, PDF and 300-dpi PNG comparisons for Table 2 utilization."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    matplotlib.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 9,
            "axes.labelsize": 10,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "figure.dpi": 300,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
        }
    )
    rows = [
        item
        for item in analysis["configurations"]
        if item["top_p"] == 1.0 and item["block_size"] in PAPER_TABLE2
    ]
    rows.sort(key=lambda item: item["block_size"])
    x = list(range(len(rows)))
    observed = [item["metrics"]["utilization"]["value"] for item in rows]
    low = [item["metrics"]["utilization"]["bootstrap_ci95"][0] for item in rows]
    high = [item["metrics"]["utilization"]["bootstrap_ci95"][1] for item in rows]
    published = [PAPER_TABLE2[item["block_size"]]["utilization"] for item in rows]
    errors = [
        [value - lower for value, lower in zip(observed, low, strict=True)],
        [upper - value for value, upper in zip(observed, high, strict=True)],
    ]
    fig, ax = plt.subplots(figsize=(6.9, 4.2))
    ax.errorbar(
        x,
        observed,
        yerr=errors,
        color="#0077BB",
        marker="o",
        linewidth=1.8,
        capsize=3,
        label="Compatibility reproduction (95% CI)",
    )
    ax.plot(
        x,
        published,
        color="#CC3311",
        marker="s",
        linestyle="--",
        linewidth=1.5,
        label="Published Table 2",
    )
    ax.set_xticks(x, [str(item["block_size"]) for item in rows])
    ax.set_xlabel("Message block length")
    ax.set_ylabel("Entropy utilization")
    ax.set_ylim(0, 1.05)
    ax.grid(axis="y", color="#d9dee5", linewidth=0.6)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    fig.savefig(path.with_suffix(".pdf"))
    fig.savefig(path.with_suffix(".png"), dpi=300)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--figure", type=Path, required=True)
    parser.add_argument("--bootstrap", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260721)
    parser.add_argument("--capacity-tolerance", type=float, default=0.05)
    args = parser.parse_args()
    report = json.loads(args.input.read_text(encoding="utf-8"))
    analysis = analyze_report(
        report,
        repetitions=args.bootstrap,
        seed=args.seed,
        capacity_tolerance=args.capacity_tolerance,
    )
    analysis["source"] = str(args.input)
    analysis["source_sha256"] = hashlib.sha256(args.input.read_bytes()).hexdigest()
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown_report(analysis), encoding="utf-8")
    write_csv(args.csv, analysis)
    write_figure(args.figure, analysis)
    artifact_paths = {
        "source_csv": args.csv,
        "figure_svg": args.figure,
        "figure_pdf": args.figure.with_suffix(".pdf"),
        "figure_png": args.figure.with_suffix(".png"),
    }
    analysis["artifacts"] = {
        name: {
            "path": path.as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for name, path in artifact_paths.items()
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(analysis, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(analysis["acceptance"], indent=2))
    return 0 if analysis["acceptance"]["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
