"""Generate auditable Table 1 source data from frozen replay artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repo_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def cluster_interval(
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
    generator = random.Random(seed)
    estimates = []
    for _ in range(repetitions):
        sampled = []
        for _ in prompt_ids:
            sampled.extend(grouped[generator.choice(prompt_ids)])
        estimates.append(mean(metric(row) for row in sampled))
    return percentile(estimates, 0.025), percentile(estimates, 0.975)


def selected_rows(path: Path) -> list[dict[str, Any]]:
    report = json.loads(path.read_text(encoding="utf-8"))
    rows = [
        row
        for row in report["rows"]
        if int(row["seed"]) == 0 and bool(row.get("replay_completed"))
    ]
    if len(rows) != 20 or len({int(row["prompt_index"]) for row in rows}) != 20:
        raise ValueError(f"expected 20 complete seed-0 prompt rows in {path}")
    return sorted(rows, key=lambda row: int(row["prompt_index"]))


def summarize_variant(
    setting: str,
    path: Path,
    *,
    repetitions: int,
    seed: int,
) -> dict[str, Any]:
    rows = selected_rows(path)

    def correction(row: dict[str, Any]) -> float:
        return float(row["correction_rate"])

    def ratio(row: dict[str, Any]) -> float:
        return float(row["sparse_to_full_payload_ratio"])

    correction_ci = cluster_interval(rows, correction, repetitions=repetitions, seed=seed)
    ratio_ci = cluster_interval(rows, ratio, repetitions=repetitions, seed=seed + 6)
    return {
        "setting": setting,
        "trials": len(rows),
        "corrected_exact": sum(bool(row["corrected_exact"]) for row in rows),
        "uncorrected_exact": sum(bool(row["uncorrected_exact"]) for row in rows),
        "correction_rate": mean(correction(row) for row in rows),
        "correction_ci_low": correction_ci[0],
        "correction_ci_high": correction_ci[1],
        "legacy_payload_ratio": mean(ratio(row) for row in rows),
        "legacy_payload_ci_low": ratio_ci[0],
        "legacy_payload_ci_high": ratio_ci[1],
        "sentence_complete": sum(bool(row["sentence_complete"]) for row in rows),
        "source": repo_path(path),
    }


def manuscript_row(row: dict[str, Any], *, legacy_label: bool = False) -> str:
    trials = int(row["trials"])
    ratio_prefix = (
        f"{100 * row['legacy_payload_ratio']:.2f}% legacy fixed-width"
        if legacy_label
        else f"{100 * row['legacy_payload_ratio']:.2f}%"
    )
    return (
        f"| {row['setting']} | {trials} | {row['corrected_exact']}/{trials} | "
        f"{row['uncorrected_exact']}/{trials} | {100 * row['correction_rate']:.2f}% "
        f"[{100 * row['correction_ci_low']:.2f}, {100 * row['correction_ci_high']:.2f}] | "
        f"{ratio_prefix} [{100 * row['legacy_payload_ci_low']:.2f}, "
        f"{100 * row['legacy_payload_ci_high']:.2f}] | {row['sentence_complete']}/{trials} |"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scale",
        type=Path,
        default=ROOT / "outputs/R044_qwen_replay_scale_analysis.json",
    )
    parser.add_argument(
        "--forward",
        type=Path,
        default=ROOT / "outputs/R044_qwen_replay_scale.json",
    )
    parser.add_argument(
        "--top4",
        type=Path,
        default=ROOT / "outputs/R045_qwen_contract_k4.json",
    )
    parser.add_argument(
        "--reverse",
        type=Path,
        default=ROOT / "outputs/R046_qwen_reverse_precision.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "paper/source_data/table_01_source.csv",
    )
    parser.add_argument(
        "--trace",
        type=Path,
        default=ROOT / "paper/source_data/table_trace.json",
    )
    parser.add_argument("--bootstrap", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260720)
    args = parser.parse_args()

    scale = json.loads(args.scale.read_text(encoding="utf-8"))
    overall = scale["groups"]["overall"]
    rows = [
        {
            "setting": "FP16 to BF16, top-2, main scale",
            "trials": overall["trials"],
            "corrected_exact": overall["corrected_exact"],
            "uncorrected_exact": overall["uncorrected_exact"],
            "correction_rate": overall["correction_rate"]["mean"],
            "correction_ci_low": overall["correction_rate"]["ci95_low"],
            "correction_ci_high": overall["correction_rate"]["ci95_high"],
            "legacy_payload_ratio": overall["record_ratio"]["mean"],
            "legacy_payload_ci_low": overall["record_ratio"]["ci95_low"],
            "legacy_payload_ci_high": overall["record_ratio"]["ci95_high"],
            "sentence_complete": overall["sentence_complete"],
            "source": repo_path(args.scale),
        },
        summarize_variant(
            "FP16 to BF16, top-2, ablation subset",
            args.forward,
            repetitions=args.bootstrap,
            seed=args.seed,
        ),
        summarize_variant(
            "FP16 to BF16, top-4",
            args.top4,
            repetitions=args.bootstrap,
            seed=args.seed + 100,
        ),
        summarize_variant(
            "BF16 to FP16, top-2",
            args.reverse,
            repetitions=args.bootstrap,
            seed=args.seed + 200,
        ),
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    transformation = {
        "script": repo_path(Path(__file__)),
        "sha256": sha256(Path(__file__)),
        "operation": "derive Table 1 counts, equal-trial means and prompt-cluster intervals",
    }
    trace = {
        "schema": "manuscript-table-trace-v1",
        "inputs": {
            "scale": {"path": repo_path(args.scale), "sha256": sha256(args.scale)},
            "forward": {"path": repo_path(args.forward), "sha256": sha256(args.forward)},
            "top4": {"path": repo_path(args.top4), "sha256": sha256(args.top4)},
            "reverse": {"path": repo_path(args.reverse), "sha256": sha256(args.reverse)},
        },
        "bootstrap": {"repetitions": args.bootstrap, "seed": args.seed},
        "tables": [
            {
                "artifact_id": "table-1",
                "source_data": repo_path(args.output),
                "transformation": transformation,
                "caption_claim": "Cross-precision replay results for Qwen2.5-1.5B-Instruct.",
                "supported_manuscript_claims": [
                    {
                        "claim": "Certificate-corrected replay recovered 60 of 60 token trajectories, whereas uncorrected replay recovered 10 of 60 (Table 1 and Fig. 2a).",
                        "locator": "Results: Exact replay scales across bilingual prompts",
                    }
                ],
                "manuscript_rows": [
                    manuscript_row(rows[0], legacy_label=True),
                    *(manuscript_row(row) for row in rows[1:]),
                ],
                "limitations": [
                    "The three 20-trial variants use one public seed per prompt.",
                    "Intervals describe the fixed prompt set on one model and GPU stack.",
                ],
            }
        ],
    }
    args.trace.write_text(json.dumps(trace, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps({"rows": len(rows), "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
