"""Analyze a scaled cross-precision replay report with prompt-cluster intervals."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev
from typing import Any, Callable


def wilson_interval(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if not 0 <= successes <= trials or trials < 1:
        raise ValueError("successes and trials must define a non-empty binomial sample")
    proportion = successes / trials
    denominator = 1 + z * z / trials
    center = (proportion + z * z / (2 * trials)) / denominator
    margin = z * math.sqrt(
        proportion * (1 - proportion) / trials + z * z / (4 * trials * trials)
    ) / denominator
    low = 0.0 if successes == 0 else max(0.0, center - margin)
    high = 1.0 if successes == trials else min(1.0, center + margin)
    return low, high


def percentile(values: list[float], probability: float) -> float:
    if not values or not 0 <= probability <= 1:
        raise ValueError("percentile requires values and a probability in [0, 1]")
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def cluster_bootstrap_mean(
    rows: list[dict[str, Any]],
    metric: Callable[[dict[str, Any]], float],
    *,
    repetitions: int,
    seed: int,
) -> tuple[float, float]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["prompt_index"])].append(row)
    prompt_ids = sorted(grouped)
    if len(prompt_ids) < 2 or repetitions < 1:
        raise ValueError("cluster bootstrap requires at least two prompts and one repetition")
    generator = random.Random(seed)
    estimates: list[float] = []
    for _ in range(repetitions):
        sampled_rows: list[dict[str, Any]] = []
        for _ in prompt_ids:
            sampled_rows.extend(grouped[generator.choice(prompt_ids)])
        estimates.append(mean(metric(row) for row in sampled_rows))
    return percentile(estimates, 0.025), percentile(estimates, 0.975)


def metric_summary(
    rows: list[dict[str, Any]], key: str, repetitions: int, seed: int
) -> dict[str, float]:
    values = [float(row[key]) for row in rows]
    low, high = cluster_bootstrap_mean(
        rows, lambda row: float(row[key]), repetitions=repetitions, seed=seed
    )
    return {
        "mean": mean(values),
        "std": stdev(values) if len(values) > 1 else 0.0,
        "ci95_low": low,
        "ci95_high": high,
        "min": min(values),
        "max": max(values),
    }


def group_summary(rows: list[dict[str, Any]], repetitions: int, seed: int) -> dict[str, Any]:
    total = len(rows)
    corrected = sum(bool(row["corrected_exact"]) for row in rows)
    uncorrected = sum(bool(row["uncorrected_exact"]) for row in rows)
    complete = sum(bool(row["sentence_complete"]) for row in rows)
    return {
        "trials": total,
        "prompts": len({int(row["prompt_index"]) for row in rows}),
        "corrected_exact": corrected,
        "corrected_exact_wilson95": wilson_interval(corrected, total),
        "uncorrected_exact": uncorrected,
        "uncorrected_exact_wilson95": wilson_interval(uncorrected, total),
        "sentence_complete": complete,
        "sentence_complete_wilson95": wilson_interval(complete, total),
        "correction_rate": metric_summary(rows, "correction_rate", repetitions, seed),
        "record_ratio": metric_summary(
            rows, "sparse_to_full_payload_ratio", repetitions, seed + 1
        ),
        "token_count": metric_summary(rows, "token_count", repetitions, seed + 2),
        "contract_exact_rate": metric_summary(
            rows, "shared_contract_exact_rate", repetitions, seed + 3
        ),
        "contract_source_mass": metric_summary(
            rows, "mean_contract_source_mass", repetitions, seed + 4
        ),
        "contract_truncation_kl_nats": metric_summary(
            rows, "mean_contract_truncation_kl_nats", repetitions, seed + 5
        ),
    }


def prompt_table(rows: list[dict[str, Any]], english_prompts: int) -> list[dict[str, Any]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["prompt_index"])].append(row)
    table = []
    for prompt_index in sorted(grouped):
        selected = grouped[prompt_index]
        table.append(
            {
                "prompt_index": prompt_index,
                "language": "en" if prompt_index < english_prompts else "zh",
                "seeds": len(selected),
                "corrected_exact": sum(bool(row["corrected_exact"]) for row in selected),
                "uncorrected_exact": sum(bool(row["uncorrected_exact"]) for row in selected),
                "sentence_complete": sum(bool(row["sentence_complete"]) for row in selected),
                "mean_correction_rate": mean(float(row["correction_rate"]) for row in selected),
                "max_correction_rate": max(float(row["correction_rate"]) for row in selected),
                "mean_token_count": mean(int(row["token_count"]) for row in selected),
                "max_reference_rank": max(
                    int(row["max_reference_rank_in_replay"]) for row in selected
                ),
            }
        )
    return table


def markdown_report(analysis: dict[str, Any]) -> str:
    overall = analysis["groups"]["overall"]
    lines = [
        "# R044 Scale Analysis",
        "",
        "## Main Results",
        "",
        "| Group | Trials | Corrected exact | Uncorrected exact | Sentence complete | Mean correction rate (cluster 95% CI) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name in ("overall", "english", "chinese"):
        value = analysis["groups"][name]
        rate = value["correction_rate"]
        lines.append(
            f"| {name} | {value['trials']} | {value['corrected_exact']}/{value['trials']} | "
            f"{value['uncorrected_exact']}/{value['trials']} | "
            f"{value['sentence_complete']}/{value['trials']} | "
            f"{rate['mean']:.4f} [{rate['ci95_low']:.4f}, {rate['ci95_high']:.4f}] |"
        )
    lines.extend(
        [
            "",
            "## Prompt-Level Raw Table",
            "",
            "| Prompt | Lang | Seeds | Corrected | Uncorrected | Complete | Mean correction | Max correction | Mean tokens | Max rank |",
            "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in analysis["prompt_table"]:
        lines.append(
            f"| {row['prompt_index']} | {row['language']} | {row['seeds']} | "
            f"{row['corrected_exact']} | {row['uncorrected_exact']} | "
            f"{row['sentence_complete']} | {row['mean_correction_rate']:.4f} | "
            f"{row['max_correction_rate']:.4f} | {row['mean_token_count']:.2f} | "
            f"{row['max_reference_rank']} |"
        )
    correction = overall["correction_rate"]
    lines.extend(
        [
            "",
            "## Key Findings",
            "",
            f"1. Corrected replay recovered {overall['corrected_exact']}/{overall['trials']} trajectories; the Wilson 95% interval is [{overall['corrected_exact_wilson95'][0]:.4f}, {overall['corrected_exact_wilson95'][1]:.4f}].",
            f"2. Mean correction rate was {correction['mean']:.4f}, with prompt-cluster bootstrap 95% CI [{correction['ci95_low']:.4f}, {correction['ci95_high']:.4f}].",
            f"3. Without corrections, only {overall['uncorrected_exact']}/{overall['trials']} trajectories matched exactly.",
            f"4. Sentence completion was {overall['sentence_complete']}/{overall['trials']}; failed completions remain in the primary denominator.",
            "5. Top-4 missed one reference token, while top-8 covered every reference token in the scale run.",
            "",
            "## Boundaries",
            "",
            "- Seeds within a prompt are not treated as independent prompt samples; continuous-metric intervals resample prompts as clusters.",
            "- Wilson intervals describe the 60 observed trajectories and do not establish cross-model or cross-hardware generality.",
            "- Text completion is a structural endpoint check, not a blinded human-quality evaluation.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--bootstrap", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260720)
    parser.add_argument("--english-prompts", type=int, default=10)
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    rows = [row for row in report["rows"] if bool(row.get("replay_completed"))]
    if len(rows) != int(report["progress"]["expected_trials"]):
        raise ValueError("scale report is incomplete")
    english = [row for row in rows if int(row["prompt_index"]) < args.english_prompts]
    chinese = [row for row in rows if int(row["prompt_index"]) >= args.english_prompts]
    analysis = {
        "schema": "precision-replay-scale-analysis-v1",
        "source": str(args.input),
        "source_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "source_result_signature": report["result_signature"],
        "bootstrap_repetitions": args.bootstrap,
        "bootstrap_seed": args.seed,
        "groups": {
            "overall": group_summary(rows, args.bootstrap, args.seed),
            "english": group_summary(english, args.bootstrap, args.seed + 100),
            "chinese": group_summary(chinese, args.bootstrap, args.seed + 200),
        },
        "prompt_table": prompt_table(rows, args.english_prompts),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(analysis, indent=2, ensure_ascii=True), encoding="utf-8")
    args.markdown.write_text(markdown_report(analysis), encoding="utf-8")
    print(json.dumps(analysis["groups"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
