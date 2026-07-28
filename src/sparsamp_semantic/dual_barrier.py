"""Reference-only dual-barrier certificates for discrete contract replay."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .replay_certificate import ReplayCorrection, ReplayManifest


@dataclass(frozen=True)
class DualBarrierThresholds:
    """Frozen support-gap and integer-boundary thresholds."""

    support_gap_bins: int
    mass_radius: int

    def __post_init__(self) -> None:
        if self.support_gap_bins < 0 or self.mass_radius < 0:
            raise ValueError("dual-barrier thresholds must be non-negative")


@dataclass(frozen=True)
class DualBarrierCertificate:
    """Sparse reference-token manifest and its two construction reasons."""

    manifest: ReplayManifest
    support_steps: tuple[int, ...]
    mass_steps: tuple[int, ...]
    ambiguous_steps: tuple[int, ...]


def build_dual_barrier_certificate(
    reference_token_ids: Sequence[int],
    rank_cutoff_gaps: Sequence[int],
    boundary_slacks: Sequence[int | None],
    thresholds: DualBarrierThresholds,
) -> DualBarrierCertificate:
    """Flag steps near either a support cutoff or an integer CDF boundary."""

    tokens = tuple(int(value) for value in reference_token_ids)
    gaps = tuple(int(value) for value in rank_cutoff_gaps)
    slacks = tuple(None if value is None else int(value) for value in boundary_slacks)
    if not tokens or len(tokens) != len(gaps) or len(tokens) != len(slacks):
        raise ValueError("tokens, gaps, and slacks must have equal positive length")
    if any(value < 0 for value in gaps) or any(
        value is not None and value < 0 for value in slacks
    ):
        raise ValueError("reference barrier features must be non-negative")

    support_steps = tuple(
        step for step, gap in enumerate(gaps) if gap <= thresholds.support_gap_bins
    )
    mass_steps = tuple(
        step
        for step, slack in enumerate(slacks)
        if slack is not None and slack < thresholds.mass_radius
    )
    ambiguous_steps = tuple(sorted(set(support_steps) | set(mass_steps)))
    manifest = ReplayManifest(
        token_count=len(tokens),
        corrections=tuple(
            ReplayCorrection(step=step, token_id=tokens[step])
            for step in ambiguous_steps
        ),
    )
    return DualBarrierCertificate(
        manifest=manifest,
        support_steps=support_steps,
        mass_steps=mass_steps,
        ambiguous_steps=ambiguous_steps,
    )
