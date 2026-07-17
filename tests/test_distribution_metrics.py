from __future__ import annotations

from fractions import Fraction
from math import isclose, log

import pytest

from sparsamp_semantic.types import DistributionSnapshot, TokenCandidate


def _snapshot() -> DistributionSnapshot:
    return DistributionSnapshot(
        candidates=(
            TokenCandidate(token_id=0, text="a", probability=0.5),
            TokenCandidate(token_id=1, text="b", probability=0.3),
            TokenCandidate(token_id=2, text="c", probability=0.2),
        )
    )


def test_matching_distribution_has_zero_forward_kl_and_tv() -> None:
    snapshot = _snapshot()
    implemented = (Fraction(1, 2), Fraction(3, 10), Fraction(1, 5))

    assert isclose(snapshot.forward_kl_to_nats(implemented), 0.0, abs_tol=1e-15)
    assert isclose(snapshot.total_variation_to(implemented), 0.0, abs_tol=1e-15)


def test_forward_quantization_kl_and_tv_match_definitions() -> None:
    snapshot = _snapshot()
    implemented = (Fraction(3, 5), Fraction(1, 4), Fraction(3, 20))
    expected_kl = 0.5 * log(0.5 / 0.6) + 0.3 * log(0.3 / 0.25) + 0.2 * log(0.2 / 0.15)
    expected_tv = 0.5 * (abs(0.5 - 0.6) + abs(0.3 - 0.25) + abs(0.2 - 0.15))

    assert isclose(snapshot.forward_kl_to_nats(implemented), expected_kl, rel_tol=1e-14)
    assert isclose(snapshot.total_variation_to(implemented), expected_tv, rel_tol=1e-14)


def test_forward_kl_is_infinite_when_implemented_support_is_missing() -> None:
    assert _snapshot().forward_kl_to_nats((Fraction(1, 2), Fraction(1, 2), 0)) == float(
        "inf"
    )


def test_distribution_metrics_validate_shape_and_mass() -> None:
    snapshot = _snapshot()
    with pytest.raises(ValueError, match="align"):
        snapshot.forward_kl_to_nats((0.5, 0.5))
    with pytest.raises(ValueError, match="positive mass"):
        snapshot.total_variation_to((0, 0, 0))
    with pytest.raises(ValueError, match="non-negative"):
        snapshot.forward_kl_to_nats((0.6, 0.5, -0.1))
