from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "ccfa_bounded_decision"
FIGURES = OUT / "figures"
SOURCE = OUT / "source_data"

# Okabe-Ito palette: color-blind safe and legible in grayscale.
BLUE = "#0072B2"
ORANGE = "#E69F00"
GREEN = "#009E73"
RED = "#D55E00"
GRAY = "#6B7280"


def load(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "outputs" / name).read_text(encoding="utf-8"))


def configure() -> Any:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    matplotlib.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 8.5,
            "axes.titlesize": 9.5,
            "axes.labelsize": 8.5,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 7.5,
            "figure.dpi": 300,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "pdf.fonttype": 42,
        }
    )
    return plt


def save(fig: Any, stem: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / f"{stem}.pdf")
    fig.savefig(FIGURES / f"{stem}.png", dpi=300)


def write_csv(stem: str, rows: list[dict[str, Any]]) -> None:
    SOURCE.mkdir(parents=True, exist_ok=True)
    with (SOURCE / f"{stem}.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def frontier(plt: Any) -> None:
    r54 = load("R054_conformal_boundary_certificate.json")["primary"]["summary"]
    r56 = load("R056_dual_barrier_certificate.json")["heldout"]["summary"]
    r57 = load("R057_counterfactual_support_screen.json")["heldout"]["summary"]
    r58 = load("R058_bounded_decision_set.json")["heldout"]["summary"]
    r59 = load("R059_independent_bounded_decision.json")["pooled"]
    rows = [
        {
            "method": "R054 Boundary",
            "exact_trials": r54["exact_trials"],
            "trials": r54["trials"],
            "success_rate": r54["exact_trials"] / r54["trials"],
            "payload_to_full": r54["certificate_to_full_ratio"],
            "evidence": "development",
        },
        {
            "method": "R056 Dual barrier",
            "exact_trials": r56["exact_trials"],
            "trials": r56["trials"],
            "success_rate": r56["exact_trials"] / r56["trials"],
            "payload_to_full": r56["dual_to_full_ratio"],
            "evidence": "development",
        },
        {
            "method": "R057 Local screen",
            "exact_trials": r57["exact_trials"],
            "trials": r57["trials"],
            "success_rate": r57["exact_trials"] / r57["trials"],
            "payload_to_full": r57["to_full_ratio"],
            "evidence": "development",
        },
        {
            "method": "R058 BDS",
            "exact_trials": r58["exact_trials"],
            "trials": r58["trials"],
            "success_rate": r58["exact_trials"] / r58["trials"],
            "payload_to_full": r58["to_full_ratio"],
            "evidence": "development",
        },
        {
            "method": "R059 BDS",
            "exact_trials": r59["exact_trials"],
            "trials": r59["trials"],
            "success_rate": r59["exact_trials"] / r59["trials"],
            "payload_to_full": r59["to_full_ratio"],
            "evidence": "independent seeds",
        },
    ]
    write_csv("figure_04_frontier", rows)
    fig, ax = plt.subplots(figsize=(3.35, 2.55))
    label_offsets = {
        "R054 Boundary": (4, 5),
        "R056 Dual barrier": (5, 7),
        "R057 Local screen": (4, 5),
        "R058 BDS": (-48, 8),
        "R059 BDS": (-18, -17),
    }
    for row in rows:
        confirmed = row["evidence"] == "independent seeds"
        ax.scatter(
            100 * row["payload_to_full"],
            100 * row["success_rate"],
            s=78 if confirmed else 48,
            marker="*" if confirmed else "o",
            color=GREEN if confirmed else BLUE,
            edgecolor="black",
            linewidth=0.5,
            zorder=3,
        )
        ax.annotate(
            row["method"],
            (100 * row["payload_to_full"], 100 * row["success_rate"]),
            xytext=label_offsets[row["method"]],
            textcoords="offset points",
            fontsize=6.8,
        )
    ax.axhline(100, color=GRAY, linewidth=0.8, linestyle="--")
    ax.set(xlabel="Payload / full trace (%)", ylabel="Exact trial coverage (%)", xlim=(15, 122), ylim=(65, 103))
    ax.grid(axis="both", color="#E5E7EB", linewidth=0.6)
    save(fig, "figure_04_frontier")
    plt.close(fig)


def failure_anatomy(plt: Any) -> None:
    r56 = load("R056_dual_barrier_certificate.json")["heldout"]["summary"]
    rows = [
        {"failure": "Support flip", "count": r56["support_flips"]},
        {"failure": "Integer-mass flip", "count": r56["mass_flips"]},
    ]
    write_csv("figure_05_failure_anatomy", rows)
    fig, ax = plt.subplots(figsize=(3.35, 2.2))
    bars = ax.bar([r["failure"] for r in rows], [r["count"] for r in rows], color=[ORANGE, RED], width=0.62)
    ax.bar_label(bars, padding=3, fontsize=8)
    ax.set(ylabel="Observed FP16/BF16 decision flips", ylim=(0, max(r["count"] for r in rows) * 1.25))
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.6)
    save(fig, "figure_05_failure_anatomy")
    plt.close(fig)


def independent_confirmation(plt: Any) -> None:
    data = load("R059_independent_bounded_decision.json")
    rows = []
    for seed, summary in sorted(data["per_seed"].items(), key=lambda item: int(item[0])):
        rows.append(
            {
                "seed": int(seed),
                "exact_trials": summary["exact_trials"],
                "trials": summary["trials"],
                "payload_to_full": summary["to_full_ratio"],
                "payload_to_r056": summary["to_dual_ratio"],
                "contracts_per_token": summary["mean_contracts_per_token"],
            }
        )
    write_csv("figure_06_independent_confirmation", rows)
    fig, axes = plt.subplots(1, 2, figsize=(6.9, 2.35))
    labels = [f"Seed {row['seed']}" for row in rows]
    full = [100 * row["payload_to_full"] for row in rows]
    dual = [100 * row["payload_to_r056"] for row in rows]
    x = range(len(rows))
    axes[0].bar([i - 0.18 for i in x], full, width=0.36, color=BLUE, label="vs. full trace")
    axes[0].bar([i + 0.18 for i in x], dual, width=0.36, color=ORANGE, label="vs. R056")
    axes[0].set_xticks(list(x), labels)
    axes[0].set(ylabel="Relative payload (%)", ylim=(0, 100))
    axes[0].legend(frameon=False, loc="upper left")
    exact = [row["exact_trials"] for row in rows]
    bars = axes[1].bar(labels, exact, color=GREEN, width=0.58)
    axes[1].bar_label(bars, labels=[f"{row['exact_trials']}/{row['trials']}" for row in rows], padding=3)
    axes[1].set(ylabel="Exact trials", ylim=(0, 22))
    for ax in axes:
        ax.grid(axis="y", color="#E5E7EB", linewidth=0.6)
    save(fig, "figure_06_independent_confirmation")
    plt.close(fig)


def relative_improvement(plt: Any) -> None:
    pooled = load("R059_independent_bounded_decision.json")["pooled"]
    rows = [
        {"method": "R056 dual barrier", "relative_payload": 1.0},
        {"method": "R059 bounded set", "relative_payload": pooled["to_dual_ratio"]},
    ]
    write_csv("figure_07_relative_improvement", rows)
    fig, ax = plt.subplots(figsize=(3.35, 2.2))
    values = [100 * row["relative_payload"] for row in rows]
    bars = ax.bar([row["method"] for row in rows], values, color=[GRAY, GREEN], width=0.6)
    ax.bar_label(bars, labels=[f"{value:.1f}%" for value in values], padding=3, fontsize=8)
    reduction = 100 * (1 - pooled["to_dual_ratio"])
    ax.text(0.5, 0.78, f"{reduction:.2f}% payload reduction", transform=ax.transAxes, ha="center", color=GREEN, weight="bold")
    ax.set(ylabel="Payload relative to R056 (%)", ylim=(0, 112))
    ax.tick_params(axis="x", rotation=8)
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.6)
    save(fig, "figure_07_relative_improvement")
    plt.close(fig)


def main() -> int:
    plt = configure()
    frontier(plt)
    failure_anatomy(plt)
    independent_confirmation(plt)
    relative_improvement(plt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
