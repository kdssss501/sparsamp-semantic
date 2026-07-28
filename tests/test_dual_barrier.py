import pytest

from sparsamp_semantic.dual_barrier import (
    DualBarrierThresholds,
    build_dual_barrier_certificate,
)


def test_dual_barrier_unions_support_and_mass_reasons() -> None:
    result = build_dual_barrier_certificate(
        (10, 20, 30, 40),
        (0, 3, 2, 5),
        (8, 0, 4, 1),
        DualBarrierThresholds(support_gap_bins=2, mass_radius=2),
    )
    assert result.support_steps == (0, 2)
    assert result.mass_steps == (1, 3)
    assert result.ambiguous_steps == (0, 1, 2, 3)
    assert [item.token_id for item in result.manifest.corrections] == [10, 20, 30, 40]


def test_dual_barrier_uses_closed_gap_and_open_mass_radius() -> None:
    result = build_dual_barrier_certificate(
        (10, 20),
        (2, 3),
        (2, 1),
        DualBarrierThresholds(support_gap_bins=2, mass_radius=2),
    )
    assert result.support_steps == (0,)
    assert result.mass_steps == (1,)

    with pytest.raises(ValueError, match="non-negative"):
        DualBarrierThresholds(-1, 0)
