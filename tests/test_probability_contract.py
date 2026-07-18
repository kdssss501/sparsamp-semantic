from __future__ import annotations

from fractions import Fraction

import pytest

from sparsamp_semantic.probability_contract import (
    allocate_integer_mass,
    decimal_quantized_probabilities,
    validate_probability_contract,
)


def test_largest_remainder_is_exact_and_breaks_ties_by_candidate_order() -> None:
    allocation = allocate_integer_mass(
        (Fraction(1, 3), Fraction(1, 3), Fraction(1, 3)),
        mass_bits=16,
        preserve_support=False,
    )

    assert allocation.total_mass == 1 << 16
    assert allocation.counts == (21846, 21845, 21845)
    assert sum(allocation.probabilities, start=Fraction(0)) == 1


def test_support_preserving_allocation_keeps_tiny_positive_candidates() -> None:
    target = (Fraction(9_999_999_999, 10_000_000_000), Fraction(1, 10_000_000_000))

    lossy = allocate_integer_mass(target, mass_bits=16, preserve_support=False)
    preserved = allocate_integer_mass(target, mass_bits=16, preserve_support=True)

    assert lossy.counts[1] == 0
    assert preserved.counts[1] == 1
    assert all(count > 0 for count in preserved.counts)


def test_non_preserving_largest_remainder_has_sub_unit_per_candidate_error() -> None:
    target = (Fraction(2, 5), Fraction(3, 10), Fraction(1, 5), Fraction(1, 10))
    allocation = allocate_integer_mass(target, mass_bits=16, preserve_support=False)
    unit = Fraction(1, allocation.total_mass)

    assert all(
        abs(implemented - expected) < unit
        for implemented, expected in zip(allocation.probabilities, target, strict=True)
    )


def test_integer_contract_is_stable_to_small_probability_drift() -> None:
    first = allocate_integer_mass((0.4, 0.3, 0.2, 0.1), mass_bits=16, preserve_support=True)
    drifted = allocate_integer_mass(
        (0.400000001, 0.299999999, 0.200000001, 0.099999999),
        mass_bits=16,
        preserve_support=True,
    )

    assert first.counts == drifted.counts


def test_probability_contract_validation_rejects_ambiguous_or_invalid_modes() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        validate_probability_contract("1e-15", 32)
    with pytest.raises(ValueError, match=r"\[16, 52\]"):
        allocate_integer_mass((0.5, 0.5), mass_bits=8)
    with pytest.raises(ValueError, match="non-negative"):
        allocate_integer_mass((0.6, -0.1, 0.5), mass_bits=16)


def test_decimal_contract_remains_normalized_and_positive() -> None:
    probabilities = decimal_quantized_probabilities((0.4, 0.3, 0.2, 0.1), "1e-15")

    assert sum(probabilities, start=Fraction(0)) == 1
    assert all(value > 0 for value in probabilities)
