"""Generate the manuscript figures and auditable source-data tables."""

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
CB = ["#0077BB", "#EE7733", "#009988", "#CC3311", "#BBBBBB", "#000000"]


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
    if len(prompt_ids) < 2:
        raise ValueError("cluster interval requires at least two prompts")
    generator = random.Random(seed)
    estimates = []
    for _ in range(repetitions):
        sampled = []
        for _ in prompt_ids:
            sampled.extend(grouped[generator.choice(prompt_ids)])
        estimates.append(mean(metric(row) for row in sampled))
    return percentile(estimates, 0.025), percentile(estimates, 0.975)


def selected_rows(path: Path, selected_seed: int = 0) -> list[dict[str, Any]]:
    report = json.loads(path.read_text(encoding="utf-8"))
    rows = [
        row
        for row in report["rows"]
        if int(row["seed"]) == selected_seed and bool(row.get("replay_completed"))
    ]
    if len(rows) != 20 or len({int(row["prompt_index"]) for row in rows}) != 20:
        raise ValueError(f"expected 20 complete prompt rows in {path}")
    return sorted(rows, key=lambda row: int(row["prompt_index"]))


def summarize_variant(
    rows: list[dict[str, Any]], repetitions: int, seed: int
) -> dict[str, dict[str, Any]]:
    metrics: dict[str, Callable[[dict[str, Any]], float]] = {
        "correction_rate": lambda row: float(row["correction_rate"]),
        "retained_source_mass": lambda row: float(row["mean_contract_source_mass"]),
        "truncation_kl_nats": lambda row: float(row["mean_contract_truncation_kl_nats"]),
        "contract_exact_rate": lambda row: float(row["shared_contract_exact_rate"]),
        "sentence_complete_rate": lambda row: float(bool(row["sentence_complete"])),
        "corrected_exact_rate": lambda row: float(bool(row["corrected_exact"])),
        "uncorrected_exact_rate": lambda row: float(bool(row["uncorrected_exact"])),
    }
    result = {}
    for offset, (name, metric) in enumerate(metrics.items()):
        low, high = cluster_interval(
            rows, metric, repetitions=repetitions, seed=seed + offset
        )
        result[name] = {
            "mean": mean(metric(row) for row in rows),
            "ci95_low": low,
            "ci95_high": high,
        }
    return result


def configure_matplotlib() -> Any:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    matplotlib.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "figure.dpi": 300,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
        }
    )
    return plt


def save_figure(figure: Any, output_dir: Path, stem: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_dir / f"{stem}.pdf")
    figure.savefig(output_dir / f"{stem}.png", dpi=300)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def figure1(plt: Any, output_dir: Path) -> None:
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    fig, ax = plt.subplots(figsize=(6.9, 3.8))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    boxes = [
        (0.04, 0.62, 0.19, 0.22, "Reference run", "FP16 trajectory\n$x_{1:n}$"),
        (0.30, 0.62, 0.19, 0.22, "Target audit", "Evaluate on each\nreference prefix"),
        (0.56, 0.62, 0.19, 0.22, "Sparse record", "Store $(t,x_t)$ only\nwhen choices differ"),
        (0.78, 0.18, 0.18, 0.22, "Target replay", "Apply corrections\nbefore extension"),
        (0.52, 0.18, 0.18, 0.22, "Exact output", "$y_{1:n}=x_{1:n}$\nunder fixed target"),
    ]
    for index, (x, y, width, height, title, body) in enumerate(boxes):
        color = CB[index % 4]
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                width,
                height,
                boxstyle="round,pad=0.012,rounding_size=0.015",
                linewidth=1.4,
                edgecolor=color,
                facecolor="white",
            )
        )
        ax.text(x + width / 2, y + height * 0.67, title, ha="center", va="center", weight="bold")
        ax.text(x + width / 2, y + height * 0.30, body, ha="center", va="center", fontsize=8)
    arrows = [
        ((0.23, 0.73), (0.30, 0.73)),
        ((0.49, 0.73), (0.56, 0.73)),
        ((0.75, 0.70), (0.84, 0.40)),
        ((0.78, 0.29), (0.70, 0.29)),
    ]
    for start, end in arrows:
        ax.add_patch(
            FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=12, linewidth=1.2, color="#333333")
        )
    ax.text(0.5, 0.95, "Sparse precision replay certificate", ha="center", va="center", fontsize=12, weight="bold")
    ax.text(
        0.04,
        0.07,
        "Public contract: quantized relative logits, canonical token order, integer mass and public seed",
        fontsize=8,
        color="#333333",
    )
    save_figure(fig, output_dir, "figure_01_workflow")
    plt.close(fig)


def figure2(
    plt: Any, analysis: dict[str, Any], output_dir: Path, source_dir: Path
) -> None:
    prompt_rows = analysis["prompt_table"]
    write_csv(
        source_dir / "figure_02_source.csv",
        list(prompt_rows[0]),
        prompt_rows,
    )
    fig, axes = plt.subplots(1, 2, figsize=(6.9, 3.6), gridspec_kw={"width_ratios": [0.8, 1.6]})
    axes[0].bar(
        [0, 1],
        [analysis["groups"]["overall"]["uncorrected_exact"], analysis["groups"]["overall"]["corrected_exact"]],
        color=[CB[4], CB[0]],
        edgecolor="black",
        linewidth=0.5,
    )
    axes[0].set_xticks([0, 1], ["Seed only", "Certificate"])
    axes[0].set_ylabel("Exact trajectories (n of 60)")
    axes[0].set_ylim(0, 66)
    axes[0].set_title("a", loc="left", weight="bold")
    for index, value in enumerate([10, 60]):
        axes[0].text(index, value + 1.5, str(value), ha="center")

    for language, color, marker, label in (("en", CB[0], "o", "English"), ("zh", CB[1], "s", "Chinese")):
        selected = [row for row in prompt_rows if row["language"] == language]
        axes[1].scatter(
            [int(row["prompt_index"]) + 1 for row in selected],
            [100 * float(row["mean_correction_rate"]) for row in selected],
            color=color,
            marker=marker,
            s=28,
            label=label,
            edgecolor="black",
            linewidth=0.35,
        )
    axes[1].axhline(
        100 * analysis["groups"]["overall"]["correction_rate"]["mean"],
        color=CB[2],
        linestyle="--",
        linewidth=1.2,
        label="Overall mean",
    )
    axes[1].set_xlabel("Prompt index")
    axes[1].set_ylabel("Mean corrections per trajectory (%)")
    axes[1].set_xlim(0.3, 20.7)
    axes[1].set_ylim(0, 4.2)
    axes[1].set_xticks([1, 5, 10, 15, 20])
    axes[1].legend(frameon=False, ncol=1)
    axes[1].set_title("b", loc="left", weight="bold")
    fig.tight_layout()
    save_figure(fig, output_dir, "figure_02_replay_scale")
    plt.close(fig)


def grouped_interval_figure(
    plt: Any,
    variants: dict[str, dict[str, dict[str, Any]]],
    names: list[str],
    labels: list[str],
    metrics: list[tuple[str, str, float]],
    output_dir: Path,
    source_path: Path,
    stem: str,
) -> None:
    source_rows = []
    for name, label in zip(names, labels, strict=True):
        for metric, _, _ in metrics:
            value = variants[name][metric]
            source_rows.append({"variant": label, "metric": metric, **value})
    write_csv(
        source_path,
        ["variant", "metric", "mean", "ci95_low", "ci95_high"],
        source_rows,
    )
    columns = 3 if len(metrics) == 3 else (2 if len(metrics) > 2 else len(metrics))
    rows = (len(metrics) + columns - 1) // columns
    fig, axes = plt.subplots(rows, columns, figsize=(6.9, 2.8 * rows), squeeze=False)
    for index, (metric, ylabel, ymax) in enumerate(metrics):
        ax = axes[index // columns][index % columns]
        values = [variants[name][metric]["mean"] for name in names]
        errors = [
            [variants[name][metric]["mean"] - variants[name][metric]["ci95_low"] for name in names],
            [variants[name][metric]["ci95_high"] - variants[name][metric]["mean"] for name in names],
        ]
        ax.bar(
            range(len(names)),
            values,
            color=[CB[i] for i in range(len(names))],
            edgecolor="black",
            linewidth=0.5,
            width=0.62,
        )
        ax.errorbar(range(len(names)), values, yerr=errors, fmt="none", ecolor="black", capsize=3, linewidth=0.9)
        ax.set_xticks(range(len(names)), labels)
        ax.set_ylabel(ylabel)
        ax.set_ylim(0, ymax)
        ax.set_title(chr(ord("a") + index), loc="left", weight="bold")
    for index in range(len(metrics), rows * columns):
        axes[index // columns][index % columns].axis("off")
    fig.tight_layout()
    save_figure(fig, output_dir, stem)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scale", type=Path, default=ROOT / "outputs/R044_qwen_replay_scale_analysis.json")
    parser.add_argument("--forward", type=Path, default=ROOT / "outputs/R044_qwen_replay_scale.json")
    parser.add_argument("--top4", type=Path, default=ROOT / "outputs/R045_qwen_contract_k4.json")
    parser.add_argument("--reverse", type=Path, default=ROOT / "outputs/R046_qwen_reverse_precision.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "paper/figures")
    parser.add_argument("--source-dir", type=Path, default=ROOT / "paper/source_data")
    parser.add_argument("--bootstrap", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260720)
    args = parser.parse_args()

    scale_analysis = json.loads(args.scale.read_text(encoding="utf-8"))
    variants = {
        "forward_top2": summarize_variant(
            selected_rows(args.forward), args.bootstrap, args.seed
        ),
        "forward_top4": summarize_variant(
            selected_rows(args.top4), args.bootstrap, args.seed + 100
        ),
        "reverse_top2": summarize_variant(
            selected_rows(args.reverse), args.bootstrap, args.seed + 200
        ),
    }
    plt = configure_matplotlib()
    figure1(plt, args.output_dir)
    figure2(plt, scale_analysis, args.output_dir, args.source_dir)
    grouped_interval_figure(
        plt,
        variants,
        ["forward_top2", "forward_top4"],
        ["top-2", "top-4"],
        [
            ("retained_source_mass", "Retained source mass", 1.0),
            ("truncation_kl_nats", "Truncation component (nats/token)", 0.5),
            ("correction_rate", "Correction rate", 0.04),
            ("contract_exact_rate", "Shared-contract exact rate", 1.0),
        ],
        args.output_dir,
        args.source_dir / "figure_03_source.csv",
        "figure_03_contract_width",
    )
    grouped_interval_figure(
        plt,
        variants,
        ["forward_top2", "reverse_top2"],
        ["FP16 to BF16", "BF16 to FP16"],
        [
            ("correction_rate", "Correction rate", 0.04),
            ("retained_source_mass", "Retained source mass", 1.0),
            ("sentence_complete_rate", "Sentence completion rate", 1.05),
        ],
        args.output_dir,
        args.source_dir / "figure_04_source.csv",
        "figure_04_precision_direction",
    )

    transformation = {
        "script": repo_path(Path(__file__)),
        "sha256": sha256(Path(__file__)),
    }
    trace = {
        "schema": "manuscript-figure-trace-v2",
        "inputs": {
            "scale": {"path": repo_path(args.scale), "sha256": sha256(args.scale)},
            "forward": {"path": repo_path(args.forward), "sha256": sha256(args.forward)},
            "top4": {"path": repo_path(args.top4), "sha256": sha256(args.top4)},
            "reverse": {"path": repo_path(args.reverse), "sha256": sha256(args.reverse)},
        },
        "transformation": transformation,
        "bootstrap": {"repetitions": args.bootstrap, "seed": args.seed},
        "figures": [
            {
                "artifact_id": "fig-1",
                "source_data": "paper/FIGURE_PLAN.md",
                "transformation": {
                    **transformation,
                    "operation": "conceptual workflow rendering from the documented algorithm",
                },
                "caption_claim": "A target-specific sparse correction record reconstructs the selected reference trajectory under a fixed target environment.",
                "supported_manuscript_claims": [
                    {
                        "claim": "During replay, corrections are applied before extending the prefix, which prevents a local disagreement from cascading.",
                        "locator": "Introduction",
                    }
                ],
                "limitations": ["Conceptual workflow; not an empirical result."],
            },
            {
                "artifact_id": "fig-2",
                "source_data": repo_path(args.source_dir / "figure_02_source.csv"),
                "transformation": {
                    **transformation,
                    "operation": "exact-replay counts and prompt-level correction-rate plotting",
                },
                "caption_claim": "Certificates recovered 60 of 60 trajectories while prompt-level correction rates remained low.",
                "supported_manuscript_claims": [
                    {
                        "claim": "Certificate-corrected replay recovered 60 of 60 token trajectories, whereas uncorrected replay recovered 10 of 60 (Table 1 and Fig. 2a).",
                        "locator": "Results: Exact replay scales across bilingual prompts",
                    },
                    {
                        "claim": "The mean correction rate was 2.16% (prompt-cluster bootstrap 95% confidence interval, 1.80-2.53%), with a maximum trial rate of 6.15% and prompt-level variation shown in Fig. 2b.",
                        "locator": "Results: Exact replay scales across bilingual prompts",
                    },
                ],
                "limitations": ["Fixed prompt set on one model and GPU stack."],
            },
            {
                "artifact_id": "fig-3",
                "source_data": repo_path(args.source_dir / "figure_03_source.csv"),
                "transformation": {
                    **transformation,
                    "operation": "paired prompt-cluster contract-width summary plotting",
                },
                "caption_claim": "Top-four retained more source mass and reduced the truncation component but did not reduce correction density.",
                "supported_manuscript_claims": [
                    {
                        "claim": "The distributional improvement did not produce a reliability improvement.",
                        "locator": "Results: Contract width exposes a distribution-reliability Pareto frontier",
                    }
                ],
                "limitations": ["One public seed per contract-width condition."],
            },
            {
                "artifact_id": "fig-4",
                "source_data": repo_path(args.source_dir / "figure_04_source.csv"),
                "transformation": {
                    **transformation,
                    "operation": "paired prompt-cluster precision-direction summary plotting",
                },
                "caption_claim": "Correction density and retained mass were similar after reversing FP16 and BF16 within the tested stack.",
                "supported_manuscript_claims": [
                    {
                        "claim": "These data support bidirectional precision replay on the tested model and GPU stack.",
                        "locator": "Results: Replay is stable in both FP16/BF16 directions within the tested environment",
                    }
                ],
                "limitations": ["One public seed per precision direction; same GPU stack."],
            },
        ],
    }
    args.source_dir.mkdir(parents=True, exist_ok=True)
    (args.source_dir / "figure_trace.json").write_text(
        json.dumps(trace, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    print(json.dumps({"figures": 4, "output_dir": str(args.output_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
