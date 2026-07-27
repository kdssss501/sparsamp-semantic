"""Reference-only replay certificates from discrete sampling margins."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import ceil
from typing import Sequence

from .replay_certificate import (
    ReplayCorrection,
    ReplayManifest,
    public_replay_fraction,
)


@dataclass(frozen=True)
class BoundaryMargin:
    """Distance from one integer sample to the nearest movable CDF boundary."""

    mass_index: int
    total_mass: int
    minimum_slack: int | None

    def is_ambiguous(self, radius: int) -> bool:
        """Return whether a boundary displacement of ``radius`` may flip the choice."""

        if radius < 0:
            raise ValueError("boundary radius must be non-negative")
        return self.minimum_slack is not None and self.minimum_slack < radius


@dataclass(frozen=True)
class ConformalRadius:
    """Finite-sample split-conformal upper radius for exchangeable scores."""

    alpha: float
    calibration_size: int
    order_rank: int
    radius: int | None

    @property
    def finite(self) -> bool:
        return self.radius is not None


@dataclass(frozen=True)
class ReferenceOnlyCertificate:
    """A manifest that repairs every reference step inside the calibrated margin."""

    manifest: ReplayManifest
    ambiguous_steps: tuple[int, ...]
    radius: int


def fraction_to_mass_index(sample: Fraction, total_mass: int) -> int:
    """Map an exact fraction in [0, 1) to a public integer-mass sample."""

    if not 0 <= sample < 1:
        raise ValueError("sample fraction must lie in [0, 1)")
    if total_mass < 1:
        raise ValueError("total mass must be positive")
    return sample.numerator * total_mass // sample.denominator


def boundary_margin(counts: Sequence[int], mass_index: int) -> BoundaryMargin:
    """Compute exact directional slack to each internal cumulative boundary.

    For a boundary ``b`` to the right of sample ``s``, ``b-s-1`` integer moves are
    harmless; the next move crosses the sample. For a boundary at or left of the
    sample, ``s-b`` moves are harmless. This asymmetric convention matches the
    half-open sampling intervals ``[previous_boundary, next_boundary)``.
    """

    values = tuple(int(value) for value in counts)
    if not values or any(value < 0 for value in values):
        raise ValueError("counts must be a non-empty non-negative sequence")
    total_mass = sum(values)
    if total_mass < 1:
        raise ValueError("counts must sum to positive mass")
    if not 0 <= mass_index < total_mass:
        raise ValueError("mass index lies outside the integer mass")

    cumulative = 0
    slacks: list[int] = []
    for count in values[:-1]:
        cumulative += count
        slack = mass_index - cumulative if cumulative <= mass_index else cumulative - mass_index - 1
        slacks.append(slack)
    return BoundaryMargin(
        mass_index=mass_index,
        total_mass=total_mass,
        minimum_slack=min(slacks) if slacks else None,
    )


def contract_boundary_margin(
    counts: Sequence[int], *, step: int, context: bytes, public_seed: int
) -> BoundaryMargin:
    """Compute a step margin using the same public fraction as replay sampling."""

    total_mass = sum(int(value) for value in counts)
    sample = public_replay_fraction(step, context, public_seed)
    return boundary_margin(counts, fraction_to_mass_index(sample, total_mass))


def split_conformal_upper_radius(
    calibration_scores: Sequence[int], *, alpha: float
) -> ConformalRadius:
    """Return the standard split-conformal upper quantile.

    The order rank is ``ceil((n + 1) * (1 - alpha))``. When that rank exceeds
    the calibration size, no finite distribution-free upper radius is available;
    ``radius`` is then ``None`` rather than an invented extrapolation.
    """

    if not 0 < alpha < 1:
        raise ValueError("alpha must lie in (0, 1)")
    scores = sorted(int(value) for value in calibration_scores)
    if not scores or any(value < 0 for value in scores):
        raise ValueError("calibration scores must be non-empty and non-negative")
    rank = ceil((len(scores) + 1) * (1 - alpha))
    radius = scores[rank - 1] if rank <= len(scores) else None
    return ConformalRadius(alpha, len(scores), rank, radius)


def required_trajectory_radius(
    contract_counts: Sequence[Sequence[int]],
    correction_steps: Sequence[int],
    *,
    context: bytes,
    public_seed: int,
) -> int:
    """Return the smallest integer radius that flags every observed correction."""

    return max(
        trajectory_correction_radii(
            contract_counts,
            correction_steps,
            context=context,
            public_seed=public_seed,
        ),
        default=0,
    )


def trajectory_correction_radii(
    contract_counts: Sequence[Sequence[int]],
    correction_steps: Sequence[int],
    *,
    context: bytes,
    public_seed: int,
) -> tuple[int, ...]:
    """Return the boundary radius required by each target correction."""

    steps = tuple(int(step) for step in correction_steps)
    if len(set(steps)) != len(steps) or any(not 0 <= step < len(contract_counts) for step in steps):
        raise ValueError("correction steps must be unique and in range")
    radii: list[int] = []
    for step in steps:
        margin = contract_boundary_margin(
            contract_counts[step], step=step, context=context, public_seed=public_seed
        )
        if margin.minimum_slack is None:
            raise ValueError("a one-candidate contract cannot explain a correction")
        radii.append(margin.minimum_slack + 1)
    return tuple(radii)


def build_reference_only_certificate(
    reference_token_ids: Sequence[int],
    contract_counts: Sequence[Sequence[int]],
    *,
    context: bytes,
    public_seed: int,
    radius: int,
) -> ReferenceOnlyCertificate:
    """Repair all reference steps whose integer sampling margin is below ``radius``."""

    tokens = tuple(int(token) for token in reference_token_ids)
    if not tokens or len(tokens) != len(contract_counts):
        raise ValueError("reference tokens and contracts must have equal positive length")
    if radius < 0:
        raise ValueError("boundary radius must be non-negative")

    ambiguous: list[int] = []
    corrections: list[ReplayCorrection] = []
    for step, (token_id, counts) in enumerate(zip(tokens, contract_counts, strict=True)):
        margin = contract_boundary_margin(
            counts, step=step, context=context, public_seed=public_seed
        )
        if margin.is_ambiguous(radius):
            ambiguous.append(step)
            corrections.append(ReplayCorrection(step=step, token_id=token_id))
    return ReferenceOnlyCertificate(
        manifest=ReplayManifest(token_count=len(tokens), corrections=tuple(corrections)),
        ambiguous_steps=tuple(ambiguous),
        radius=radius,
    )
