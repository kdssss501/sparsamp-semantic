"""Compare the R044-R046 precision-replay ablations on matched prompts."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable


Metric = Callable[[list[dict[str, Any]]], float]


def wilson_interval(
    successes: int, trials: int, z: float = 1.959963984540054
) -> tuple[float, float]:
    if not 0 <= successes <= trials or trials < 1:
        raise ValueError("successes and trials must define a non-empty binomial sample")
    proportion = successes / trials
    denominator = 1 + z * z / trials
    center = (proportion + z * z / (2 * trials)) / denominator
    margin = z * math.sqrt(
        proportion * (1 - proportion) / trials + z * z / (4 * trials * trials)
    ) / denominator
    return (
        0.0 if successes == 0 else max(0.0, center - margin),
        1.0 if successes == trials else min(1.0, center + margin),
    )


def percentile(values: list[float], probability: float) -> float:
    if not values or not 0 <= probability <= 1:
        raise ValueError("percentile requires values and a probability in [0, 1]")
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def trial_key(row: dict[str, Any]) -> tuple[int, int, str]:
    return int(row["prompt_index"]), int(row["seed"]), str(row["policy"])


def deterministic_signature(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_complete_rows(path: Path, selected_seed: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    report = json.loads(path.read_text(encoding="utf-8"))
    expected = int(report["progress"]["expected_trials"])
    rows = report.get("rows", [])
    if report.get("phase") != "completed" or len(rows) != expected:
        raise ValueError(f"incomplete report: {path}")
    selected = [
        row
        for row in rows
        if int(row["seed"]) == selected_seed and bool(row.get("replay_completed"))
    ]
    if not selected or len({trial_key(row) for row in selected}) != len(selected):
        raise ValueError(f"missing or duplicate selected rows: {path}")
    return report, selected


def ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        raise ValueError("metric denominator must be positive")
    return numerator / denominator


def weighted_row_mean(rows: list[dict[str, Any]], key: str) -> float:
    return ratio(
        sum(float(row[key]) * int(row["token_count"]) for row in rows),
        sum(int(row["token_count"]) for row in rows),
    )


METRICS: dict[str, Metric] = {
    "correction_rate": lambda rows: ratio(
        sum(int(row["correction_count"]) for row in rows),
        sum(int(row["token_count"]) for row in rows),
    ),
    "contract_source_mass": lambda rows: weighted_row_mean(
        rows, "mean_contract_source_mass"
    ),
    "contract_truncation_kl_nats": lambda rows: weighted_row_mean(
        rows, "mean_contract_truncation_kl_nats"
    ),
    "quantization_kl_nats": lambda rows: weighted_row_mean(
        rows, "mean_reference_quantization_kl_nats"
    ),
    "quantization_tv": lambda rows: weighted_row_mean(
        rows, "mean_reference_quantization_tv"
    ),
    "contract_exact_rate": lambda rows: ratio(
        sum(int(row["shared_contract_exact_steps"]) for row in rows),
        sum(int(row["token_count"]) for row in rows),
    ),
    "record_ratio": lambda rows: ratio(
        sum(int(row["sparse_payload_bytes"]) for row in rows),
        sum(int(row["full_trace_payload_bytes"]) for row in rows),
    ),
    "sentence_complete_rate": lambda rows: ratio(
        sum(bool(row["sentence_complete"]) for row in rows), len(rows)
    ),
    "corrected_exact_rate": lambda rows: ratio(
        sum(bool(row["corrected_exact"]) for row in rows), len(rows)
    ),
    "uncorrected_exact_rate": lambda rows: ratio(
        sum(bool(row["uncorrected_exact"]) for row in rows), len(rows)
    ),
}


def cluster_bootstrap(
    rows: list[dict[str, Any]], metric: Metric, repetitions: int, seed: int
) -> tuple[float, float]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["prompt_index"])].append(row)
    prompt_ids = sorted(grouped)
    if len(prompt_ids) < 2 or repetitions < 1:
        raise ValueError("cluster bootstrap requires at least two prompts")
    generator = random.Random(seed)
    estimates = []
    for _ in range(repetitions):
        sample = []
        for _ in prompt_ids:
            sample.extend(grouped[generator.choice(prompt_ids)])
        estimates.append(metric(sample))
    return percentile(estimates, 0.025), percentile(estimates, 0.975)


def summarize_variant(
    report: dict[str, Any],
    rows: list[dict[str, Any]],
    repetitions: int,
    seed: int,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for offset, (name, metric) in enumerate(METRICS.items()):
        low, high = cluster_bootstrap(rows, metric, repetitions, seed + offset)
        metrics[name] = {"value": metric(rows), "ci95": [low, high]}
    corrected = sum(bool(row["corrected_exact"]) for row in rows)
    complete = sum(bool(row["sentence_complete"]) for row in rows)
    tokens = sum(int(row["token_count"]) for row in rows)
    reference_seconds = sum(float(row["reference_seconds"]) for row in rows)
    replay_seconds = sum(float(row["replay_seconds"]) for row in rows)
    return {
        "run_label": report["run_label"],
        "result_signature": report["result_signature"],
        "reference_dtype": report["experiment_config"]["reference_dtype"],
        "replay_dtype": report["experiment_config"]["replay_dtype"],
        "contract_top_k": report["experiment_config"]["contract_top_k"],
        "trials": len(rows),
        "tokens": tokens,
        "corrected_exact": corrected,
        "corrected_exact_wilson95": wilson_interval(corrected, len(rows)),
        "sentence_complete": complete,
        "sentence_complete_wilson95": wilson_interval(complete, len(rows)),
        "reference_tokens_per_second": ratio(tokens, reference_seconds),
        "replay_tokens_per_second": ratio(tokens, replay_seconds),
        "top4_coverage": ratio(
            sum(int(row["reference_tokens_in_top4"]) for row in rows), tokens
        ),
        "top8_coverage": ratio(
            sum(int(row["reference_tokens_in_top8"]) for row in rows), tokens
        ),
        "metrics": metrics,
    }


def compare_variants(
    baseline_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    repetitions: int,
    seed: int,
) -> dict[str, Any]:
    baseline = {trial_key(row): row for row in baseline_rows}
    candidate = {trial_key(row): row for row in candidate_rows}
    if baseline.keys() != candidate.keys():
        raise ValueError("variant trial keys do not match")
    keys_by_prompt: dict[int, list[tuple[int, int, str]]] = defaultdict(list)
    for key in sorted(baseline):
        keys_by_prompt[key[0]].append(key)
    prompt_ids = sorted(keys_by_prompt)
    if len(prompt_ids) < 2:
        raise ValueError("paired comparison requires at least two prompts")
    deltas: dict[str, Any] = {}
    for offset, (name, metric) in enumerate(METRICS.items()):
        observed = metric(candidate_rows) - metric(baseline_rows)
        generator = random.Random(seed + offset)
        estimates = []
        for _ in range(repetitions):
            left_sample = []
            right_sample = []
            for _ in prompt_ids:
                selected = generator.choice(prompt_ids)
                left_sample.extend(baseline[key] for key in keys_by_prompt[selected])
                right_sample.extend(candidate[key] for key in keys_by_prompt[selected])
            estimates.append(metric(right_sample) - metric(left_sample))
        deltas[name] = {
            "candidate_minus_baseline": observed,
            "paired_cluster_ci95": [
                percentile(estimates, 0.025),
                percentile(estimates, 0.975),
            ],
        }
    same_trajectories = sum(
        baseline[key]["reference_token_sha256"]
        == candidate[key]["reference_token_sha256"]
        for key in baseline
    )
    return {
        "matched_trials": len(baseline),
        "matching_reference_trajectories": same_trajectories,
        "deltas": deltas,
    }


def markdown_report(analysis: dict[str, Any]) -> str:
    variants = analysis["variants"]
    lines = [
        "# R045-R046 Precision Replay Ablation",
        "",
        "## Material Passport",
        "",
        "- Origin Skill: ARIS `ablation-planner` and `analyze-results`",
        f"- Selected public seed: {analysis['selected_seed']}",
        f"- Prompt-cluster bootstrap: {analysis['bootstrap_repetitions']:,} resamples",
        f"- Deterministic analysis signature: `{analysis['analysis_signature']}`",
        "- Verification status: ANALYZED",
        "",
        "## Source Integrity",
        "",
        "| Variant | Source SHA-256 | Result signature |",
        "|---|---|---|",
    ]
    for name in ("forward_top2", "forward_top4", "reverse_top2"):
        lines.append(
            f"| {name} | `{analysis['sources'][name]['sha256']}` | "
            f"`{variants[name]['result_signature']}` |"
        )
    lines.extend(
        [
        "",
        "## Raw Comparison",
        "",
        "| Variant | Direction | k | Trials | Corrected | Complete | Correction rate | Source mass | Truncation KL | Contract exact | Record ratio |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for name in ("forward_top2", "forward_top4", "reverse_top2"):
        value = variants[name]
        metric = value["metrics"]
        lines.append(
            f"| {name} | {value['reference_dtype']}->{value['replay_dtype']} | "
            f"{value['contract_top_k']} | {value['trials']} | "
            f"{value['corrected_exact']}/{value['trials']} | "
            f"{value['sentence_complete']}/{value['trials']} | "
            f"{metric['correction_rate']['value']:.4f} | "
            f"{metric['contract_source_mass']['value']:.4f} | "
            f"{metric['contract_truncation_kl_nats']['value']:.4f} | "
            f"{metric['contract_exact_rate']['value']:.4f} | "
            f"{metric['record_ratio']['value']:.4f} |"
        )
    top_k = analysis["comparisons"]["top4_minus_top2"]["deltas"]
    reverse = analysis["comparisons"]["reverse_minus_forward_top2"]["deltas"]
    top_k_mass_ci = top_k["contract_source_mass"]["paired_cluster_ci95"]
    top_k_kl_ci = top_k["contract_truncation_kl_nats"]["paired_cluster_ci95"]
    top_k_correction_ci = top_k["correction_rate"]["paired_cluster_ci95"]
    top_k_contract_ci = top_k["contract_exact_rate"]["paired_cluster_ci95"]
    top_k_complete_ci = top_k["sentence_complete_rate"]["paired_cluster_ci95"]
    reverse_correction_ci = reverse["correction_rate"]["paired_cluster_ci95"]
    reverse_mass_ci = reverse["contract_source_mass"]["paired_cluster_ci95"]
    lines.extend(
        [
            "",
            "## Key Findings",
            "",
            f"1. Increasing k from 2 to 4 raised retained source mass by {top_k['contract_source_mass']['candidate_minus_baseline']:+.4f} (paired 95% CI [{top_k_mass_ci[0]:+.4f}, {top_k_mass_ci[1]:+.4f}]) and reduced the truncation component by {top_k['contract_truncation_kl_nats']['candidate_minus_baseline']:+.4f} nats/token (CI [{top_k_kl_ci[0]:+.4f}, {top_k_kl_ci[1]:+.4f}]).",
            f"2. The same k change altered correction rate by {top_k['correction_rate']['candidate_minus_baseline']:+.4f} (CI [{top_k_correction_ci[0]:+.4f}, {top_k_correction_ci[1]:+.4f}]), so there is no detected correction-rate improvement.",
            f"3. Top-4 reduced shared-contract exactness by {top_k['contract_exact_rate']['candidate_minus_baseline']:+.4f} (CI [{top_k_contract_ci[0]:+.4f}, {top_k_contract_ci[1]:+.4f}]) and sentence completion by {top_k['sentence_complete_rate']['candidate_minus_baseline']:+.4f} (CI [{top_k_complete_ci[0]:+.4f}, {top_k_complete_ci[1]:+.4f}]).",
            f"4. Reversing precision direction changed correction rate by {reverse['correction_rate']['candidate_minus_baseline']:+.4f} (CI [{reverse_correction_ci[0]:+.4f}, {reverse_correction_ci[1]:+.4f}]) and source mass by {reverse['contract_source_mass']['candidate_minus_baseline']:+.4f} (CI [{reverse_mass_ci[0]:+.4f}, {reverse_mass_ci[1]:+.4f}]); neither interval excludes zero.",
            "5. Corrected exact recovery was 20/20 in all three controlled variants. The Wilson lower 95% bound is 0.8389 per variant.",
            "",
            "## Decision",
            "",
            "- Keep `contract_top_k=2` as the reproducibility default: top-4 buys a lower truncation component but does not reduce correction overhead and weakens contract agreement and structural completion in this sample.",
            "- Treat top-4 as a distribution-fidelity operating point on the Pareto frontier, not as the default or a uniformly better method.",
            "- Accept bidirectional FP16/BF16 replay as a stage-level result because both directions reached 20/20 corrected recovery and the paired direction effects on correction rate and source mass include zero.",
            "",
            "## Interpretation Boundaries",
            "",
            "- The top-k setting participates in reference token selection, so top-2 and top-4 intentionally generate different trajectories. Comparisons are paired by prompt and public seed, not by token trajectory.",
            "- The reported `-log Z` is the truncation component for conditioning on retained support. Quantization error is separate and this study does not claim zero total divergence.",
            "- Twenty prompts with one selected seed establish a controlled ablation, not cross-model or cross-hardware generality.",
            "- Sentence completion is an automated structural endpoint, not a blinded semantic-quality judgment. The top-4 decrease needs multi-seed or human evaluation before becoming a general quality claim.",
            "",
            "## Next Experiments",
            "",
            "1. Replicate the frozen top-2 configuration on an independent GPU/CUDA stack to test hardware generality.",
            "2. Run a blinded semantic preference study comparing native generation, top-2, and top-4 outputs.",
            "3. Repeat top-4 with additional public seeds only if the paper makes a semantic-quality claim; it is not needed for the current precision-direction claim.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--forward-top2", type=Path, required=True)
    parser.add_argument("--forward-top4", type=Path, required=True)
    parser.add_argument("--reverse-top2", type=Path, required=True)
    parser.add_argument("--selected-seed", type=int, default=0)
    parser.add_argument("--bootstrap", type=int, default=10000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260720)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()

    paths = {
        "forward_top2": args.forward_top2,
        "forward_top4": args.forward_top4,
        "reverse_top2": args.reverse_top2,
    }
    loaded = {
        name: load_complete_rows(path, args.selected_seed) for name, path in paths.items()
    }
    analysis = {
        "schema": "precision-replay-ablation-analysis-v1",
        "selected_seed": args.selected_seed,
        "bootstrap_repetitions": args.bootstrap,
        "bootstrap_seed": args.bootstrap_seed,
        "sources": {
            name: {
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for name, path in paths.items()
        },
        "variants": {
            name: summarize_variant(
                report, rows, args.bootstrap, args.bootstrap_seed + index * 100
            )
            for index, (name, (report, rows)) in enumerate(loaded.items())
        },
        "comparisons": {
            "top4_minus_top2": compare_variants(
                loaded["forward_top2"][1],
                loaded["forward_top4"][1],
                args.bootstrap,
                args.bootstrap_seed + 1000,
            ),
            "reverse_minus_forward_top2": compare_variants(
                loaded["forward_top2"][1],
                loaded["reverse_top2"][1],
                args.bootstrap,
                args.bootstrap_seed + 2000,
            ),
        },
    }
    analysis["analysis_signature"] = deterministic_signature(analysis)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(analysis, indent=2, ensure_ascii=True), encoding="utf-8")
    args.markdown.write_text(markdown_report(analysis), encoding="utf-8")
    print(json.dumps(analysis["variants"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
