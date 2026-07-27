from __future__ import annotations

from fractions import Fraction

import pytest

from sparsamp_semantic.conformal_replay import (
    boundary_margin,
    build_reference_only_certificate,
    fraction_to_mass_index,
    required_trajectory_radius,
    split_conformal_upper_radius,
    trajectory_correction_radii,
)
from sparsamp_semantic.replay_certificate import ReplayContractConfig, decision_context


def test_boundary_margin_respects_half_open_integer_intervals() -> None:
    assert boundary_margin((4, 6), 2).minimum_slack == 1
    assert boundary_margin((4, 6), 3).minimum_slack == 0
    assert boundary_margin((4, 6), 4).minimum_slack == 0
    assert boundary_margin((4, 6), 5).minimum_slack == 1

    assert not boundary_margin((4, 6), 3).is_ambiguous(0)
    assert boundary_margin((4, 6), 3).is_ambiguous(1)
    assert not boundary_margin((4, 6), 2).is_ambiguous(1)
    assert boundary_margin((4, 6), 2).is_ambiguous(2)


def test_boundary_margin_covers_every_internal_boundary() -> None:
    margin = boundary_margin((2, 3, 5), 4)
    assert margin.minimum_slack == 0
    assert margin.is_ambiguous(1)

    singleton = boundary_margin((10,), 9)
    assert singleton.minimum_slack is None
    assert not singleton.is_ambiguous(10)


def test_fraction_to_mass_index_is_exact_at_endpoints() -> None:
    assert fraction_to_mass_index(Fraction(0), 16) == 0
    assert fraction_to_mass_index(Fraction(1, 4), 16) == 4
    assert fraction_to_mass_index(Fraction(15, 16), 16) == 15

    with pytest.raises(ValueError, match=r"\[0, 1\)"):
        fraction_to_mass_index(Fraction(1), 16)


def test_split_conformal_radius_uses_finite_sample_order_statistic() -> None:
    calibrated = split_conformal_upper_radius(range(10), alpha=0.2)
    assert calibrated.order_rank == 9
    assert calibrated.radius == 8
    assert calibrated.finite

    unavailable = split_conformal_upper_radius(range(10), alpha=0.05)
    assert unavailable.order_rank == 11
    assert unavailable.radius is None
    assert not unavailable.finite


def test_required_radius_and_reference_only_manifest_share_the_same_margin() -> None:
    config = ReplayContractConfig(public_seed=3, mass_bits=4)
    context = decision_context("mock", "prompt", config)
    counts = ((8, 8), (8, 8), (8, 8))
    margins = []
    for step in range(3):
        certificate = build_reference_only_certificate(
            (10, 20, 30),
            counts,
            context=context,
            public_seed=3,
            radius=step,
        )
        margins.append(set(certificate.ambiguous_steps))

    correction_steps = (1,)
    radius = required_trajectory_radius(
        counts, correction_steps, context=context, public_seed=3
    )
    assert trajectory_correction_radii(
        counts, correction_steps, context=context, public_seed=3
    ) == (radius,)
    certificate = build_reference_only_certificate(
        (10, 20, 30),
        counts,
        context=context,
        public_seed=3,
        radius=radius,
    )
    assert 1 in certificate.ambiguous_steps
    assert certificate.manifest.apply(1, 999) == 20
    assert margins[0] == set()


def test_exhaustive_boundary_perturbations_never_flip_a_certified_step() -> None:
    counts = (7, 9)
    for mass_index in range(sum(counts)):
        margin = boundary_margin(counts, mass_index)
        for radius in range(5):
            nominal = mass_index >= counts[0]
            possible = {
                mass_index >= boundary
                for boundary in range(
                    max(0, counts[0] - radius),
                    min(sum(counts), counts[0] + radius) + 1,
                )
            }
            if not margin.is_ambiguous(radius):
                assert possible == {nominal}
