"""Generate Figures 1-4 and their tabular source data from frozen R044-R046 outputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures"
SOURCE = OUT / "source_data"
OKABE_ITO = {
    "orange": "#E69F00",
    "sky": "#56B4E9",
    "green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermillion": "#D55E00",
    "pink": "#CC79A7",
    "black": "#2A2A2A",
    "gray": "#8A8A8A",
}


plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "legend.fontsize": 8,
        "legend.frameon": False,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.18,
        "grid.linestyle": "-",
        "lines.linewidth": 1.6,
        "lines.markersize": 4.5,
    }
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("source-data CSV cannot be empty")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def save(fig: plt.Figure, stem: str) -> None:
    fig.savefig(OUT / f"{stem}.pdf")
    fig.savefig(OUT / f"{stem}.png", dpi=300)
    plt.close(fig)


def box(ax: plt.Axes, xy: tuple[float, float], size: tuple[float, float], text: str, color: str) -> None:
    patch = FancyBboxPatch(
        xy,
        *size,
        boxstyle="round,pad=0.02,rounding_size=0.025",
        facecolor=color,
        edgecolor="#555555",
        linewidth=0.8,
    )
    ax.add_patch(patch)
    ax.text(xy[0] + size[0] / 2, xy[1] + size[1] / 2, text, ha="center", va="center")


def arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float], dashed: bool = False) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=10,
            linewidth=1.1,
            linestyle="--" if dashed else "-",
            color="#5F6368",
        )
    )


def figure1() -> None:
    fig, ax = plt.subplots(figsize=(7.2, 3.25))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.03, 0.98, "a", fontweight="bold", fontsize=11, va="top")
    ax.text(0.36, 0.98, "b", fontweight="bold", fontsize=11, va="top")
    ax.text(0.69, 0.98, "c", fontweight="bold", fontsize=11, va="top")
    ax.text(0.16, 0.90, "Reference trajectory", ha="center", fontweight="bold")
    ax.text(0.50, 0.90, "Target manifest construction", ha="center", fontweight="bold")
    ax.text(0.83, 0.90, "Fresh target replay", ha="center", fontweight="bold")

    box(ax, (0.03, 0.60), (0.26, 0.16), "Reference precision\nnext-token logits", "#D9EDF7")
    box(ax, (0.03, 0.32), (0.26, 0.16), "Top-16 validation envelope", "#EAF4FB")
    box(ax, (0.03, 0.05), (0.26, 0.16), "Public top-k contract\n(k = 2 or 4)", "#FFF0D6")
    arrow(ax, (0.16, 0.60), (0.16, 0.48))
    arrow(ax, (0.16, 0.32), (0.16, 0.21))

    box(ax, (0.37, 0.60), (0.26, 0.16), "Same reference prefix\nin target precision", "#DFF3EA")
    box(ax, (0.37, 0.32), (0.26, 0.16), "Canonical token-ID order\ninteger mass allocation", "#EAF7F1")
    box(ax, (0.37, 0.05), (0.26, 0.16), "Record (step, token) only\nwhen target choice differs", "#FCE5DF")
    arrow(ax, (0.50, 0.60), (0.50, 0.48))
    arrow(ax, (0.50, 0.32), (0.50, 0.21))
    arrow(ax, (0.29, 0.13), (0.37, 0.13), dashed=True)

    box(ax, (0.70, 0.60), (0.26, 0.16), "Recompute target contract", "#DFF3EA")
    box(ax, (0.70, 0.32), (0.26, 0.16), "Apply sparse correction\nbefore extending prefix", "#FCE5DF")
    box(ax, (0.70, 0.05), (0.26, 0.16), "Exact reference token path\nunder stated contract", "#EAF4FB")
    arrow(ax, (0.83, 0.60), (0.83, 0.48))
    arrow(ax, (0.83, 0.32), (0.83, 0.21))
    arrow(ax, (0.63, 0.13), (0.70, 0.40), dashed=True)
    save(fig, "fig1_method_overview")
    write_csv(
        SOURCE / "figure1_components.csv",
        [
            {"stage": "reference", "operation": "top-16 validation envelope"},
            {"stage": "reference", "operation": "public top-k integer contract"},
            {"stage": "construction", "operation": "target evaluation on reference prefix"},
            {"stage": "construction", "operation": "sparse disagreement record"},
            {"stage": "replay", "operation": "correction before prefix extension"},
        ],
    )


def figure2(main: dict[str, Any], analysis: dict[str, Any]) -> None:
    rows = main["rows"]
    trial_rows = [
        {
            "prompt_index": row["prompt_index"],
            "language": "zh" if int(row["prompt_index"]) >= 10 else "en",
            "seed": row["seed"],
            "token_count": row["token_count"],
            "corrected_exact": int(bool(row["corrected_exact"])),
            "uncorrected_exact": int(bool(row["uncorrected_exact"])),
            "correction_rate": row["correction_rate"],
            "legacy_record_ratio": row["sparse_to_full_payload_ratio"],
            "sentence_complete": int(bool(row["sentence_complete"])),
        }
        for row in rows
    ]
    write_csv(SOURCE / "figure2_trials.csv", trial_rows)
    overall = analysis["groups"]["overall"]
    language_rows = []
    for language, key in (("English", "english"), ("Chinese", "chinese")):
        metric = analysis["groups"][key]["correction_rate"]
        language_rows.append(
            {
                "language": language,
                "mean": metric["mean"],
                "ci95_low": metric["ci95_low"],
                "ci95_high": metric["ci95_high"],
            }
        )
    write_csv(SOURCE / "figure2_language_summary.csv", language_rows)

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.1))
    ax = axes[0, 0]
    bars = ax.bar(
        [0, 1],
        [overall["corrected_exact"], overall["uncorrected_exact"]],
        color=[OKABE_ITO["green"], OKABE_ITO["gray"]],
        width=0.6,
    )
    ax.set_xticks([0, 1], ["Corrected", "Uncorrected"])
    ax.set_ylabel("Exact trajectories (of 60)")
    ax.set_ylim(0, 66)
    ax.bar_label(bars, labels=["60/60", "10/60"], padding=2)
    ax.set_title("a  Exact token replay", loc="left", fontweight="bold")

    ax = axes[0, 1]
    for language, color, marker in (("en", OKABE_ITO["blue"], "o"), ("zh", OKABE_ITO["orange"], "s")):
        selected = [row for row in analysis["prompt_table"] if row["language"] == language]
        ax.scatter(
            [row["prompt_index"] for row in selected],
            [100 * row["mean_correction_rate"] for row in selected],
            label="English" if language == "en" else "Chinese",
            color=color,
            marker=marker,
        )
    ax.set_xlabel("Prompt index")
    ax.set_ylabel("Mean correction rate (%)")
    ax.legend(ncol=2)
    ax.set_title("b  Prompt-cluster correction density", loc="left", fontweight="bold")

    ax = axes[1, 0]
    for position, row, color in zip(
        [0, 1], language_rows, [OKABE_ITO["blue"], OKABE_ITO["orange"]], strict=True
    ):
        mean_value = 100 * row["mean"]
        ax.errorbar(
            position,
            mean_value,
            yerr=[[mean_value - 100 * row["ci95_low"]], [100 * row["ci95_high"] - mean_value]],
            fmt="o",
            color=color,
            capsize=4,
        )
    ax.set_xticks([0, 1], ["English", "Chinese"])
    ax.set_ylabel("Correction rate (%)")
    ax.set_title("c  Prompt-cluster bootstrap 95% CI", loc="left", fontweight="bold")

    ax = axes[1, 1]
    values = np.array([100 * row["legacy_record_ratio"] for row in trial_rows])
    jitter = np.linspace(-0.10, 0.10, len(values))
    ax.scatter(jitter, values, s=15, alpha=0.65, color=OKABE_ITO["sky"], edgecolor="none")
    ax.boxplot(values, positions=[0], widths=0.32, showfliers=False)
    ax.set_xticks([0], ["Payload-only\nlegacy estimate"])
    ax.set_ylabel("Sparse/full fixed-width ratio (%)")
    ax.set_title("d  Trial-level legacy record ratio", loc="left", fontweight="bold")
    fig.tight_layout()
    save(fig, "fig2_main_scale")


def metric_row(label: str, variant: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"variant": label, "trials": variant["trials"]}
    for name in (
        "correction_rate",
        "contract_source_mass",
        "contract_truncation_kl_nats",
        "quantization_tv",
        "contract_exact_rate",
        "sentence_complete_rate",
        "corrected_exact_rate",
        "uncorrected_exact_rate",
    ):
        metric = variant["metrics"][name]
        result[name] = metric["value"]
        result[f"{name}_ci95_low"] = metric["ci95"][0]
        result[f"{name}_ci95_high"] = metric["ci95"][1]
    return result


def point_panel(
    ax: plt.Axes,
    rows: list[dict[str, Any]],
    metric: str,
    title: str,
    *,
    percent: bool = False,
) -> None:
    scale = 100 if percent else 1
    colors = [OKABE_ITO["blue"], OKABE_ITO["vermillion"]]
    for index, (row, color) in enumerate(zip(rows, colors, strict=True)):
        value = scale * row[metric]
        ax.errorbar(
            index,
            value,
            yerr=[
                [value - scale * row[f"{metric}_ci95_low"]],
                [scale * row[f"{metric}_ci95_high"] - value],
            ],
            fmt="o",
            color=color,
            capsize=3,
        )
    ax.set_xticks(range(len(rows)), [row["variant"] for row in rows])
    ax.set_title(title, loc="left", fontweight="bold")


def figure3(ablation: dict[str, Any]) -> None:
    rows = [
        metric_row("Top-2", ablation["variants"]["forward_top2"]),
        metric_row("Top-4", ablation["variants"]["forward_top4"]),
    ]
    write_csv(SOURCE / "figure3_contract_width.csv", rows)
    fig, axes = plt.subplots(2, 3, figsize=(7.2, 4.7))
    panels = [
        ("contract_source_mass", "a  Retained source mass", True),
        ("contract_truncation_kl_nats", "b  Truncation component", False),
        ("correction_rate", "c  Correction rate", True),
        ("contract_exact_rate", "d  Shared-contract exactness", True),
        ("sentence_complete_rate", "e  Sentence completion", True),
        ("uncorrected_exact_rate", "f  Uncorrected exact replay", True),
    ]
    for ax, (metric, title, percent) in zip(axes.flat, panels, strict=True):
        point_panel(ax, rows, metric, title, percent=percent)
        ax.set_ylabel("%" if percent else "nats/token")
    fig.tight_layout()
    save(fig, "fig3_contract_width")


def figure4(ablation: dict[str, Any]) -> None:
    rows = [
        metric_row("FP16→BF16", ablation["variants"]["forward_top2"]),
        metric_row("BF16→FP16", ablation["variants"]["reverse_top2"]),
    ]
    write_csv(SOURCE / "figure4_precision_direction.csv", rows)
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.6))
    panels = [
        ("corrected_exact_rate", "a  Corrected exact replay", True),
        ("correction_rate", "b  Correction rate", True),
        ("contract_source_mass", "c  Retained source mass", True),
        ("sentence_complete_rate", "d  Sentence completion", True),
    ]
    for ax, (metric, title, percent) in zip(axes.flat, panels, strict=True):
        point_panel(ax, rows, metric, title, percent=percent)
        ax.set_ylabel("%")
        if metric == "corrected_exact_rate":
            ax.set_ylim(0, 105)
    fig.tight_layout()
    save(fig, "fig4_precision_direction")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    main_report = read_json(ROOT / "outputs" / "R044_qwen_replay_scale.json")
    main_analysis = read_json(ROOT / "outputs" / "R044_qwen_replay_scale_analysis.json")
    ablation = read_json(ROOT / "outputs" / "R046_precision_replay_ablation_analysis.json")
    figure1()
    figure2(main_report, main_analysis)
    figure3(ablation)
    figure4(ablation)
    print("Generated Figures 1-4 as PDF and 300 DPI PNG with CSV source data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
