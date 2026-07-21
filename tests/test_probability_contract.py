from __future__ import annotations

from fractions import Fraction

import pytest

from sparsamp_semantic.probability_contract import (
    allocate_integer_mass,
    allocate_logit_bin_mass,
    audit_integer_mass,
    decimal_quantized_probabilities,
    support_preserving_tv_upper_bound,
    support_feasible_mass_bits,
    validate_probability_contract,
    waterfilled_support_target,
)


def test_logit_bin_mass_is_exact_positive_and_monotone() -> None:
    allocation = allocate_logit_bin_mass(
        (10, 20, 30),
        (0, -1, -4),
        quantum=0.25,
        temperature=1.0,
        mass_bits=16,
    )

    assert sum(allocation.counts) == 1 << 16
    assert all(count > 0 for count in allocation.counts)
    assert allocation.counts[0] > allocation.counts[1] > allocation.counts[2]


def test_logit_bin_mass_uses_token_id_for_order_independent_ties() -> None:
    first = allocate_logit_bin_mass(
        (30, 10, 20),
        (0, 0, 0),
        quantum=0.25,
        temperature=1.0,
        mass_bits=16,
    )
    second = allocate_logit_bin_mass(
        (10, 20, 30),
        (0, 0, 0),
        quantum=0.25,
        temperature=1.0,
        mass_bits=16,
    )

    first_by_token = dict(zip((30, 10, 20), first.counts, strict=True))
    second_by_token = dict(zip((10, 20, 30), second.counts, strict=True))
    assert first_by_token == second_by_token
    assert first_by_token[10] >= first_by_token[20] >= first_by_token[30]


def test_logit_bin_mass_rejects_invalid_contracts() -> None:
    with pytest.raises(ValueError, match="equal positive length"):
        allocate_logit_bin_mass(
            (10, 20), (0,), quantum=0.25, temperature=1.0, mass_bits=16
        )
    with pytest.raises(ValueError, match="unique"):
        allocate_logit_bin_mass(
            (10, 10), (0, -1), quantum=0.25, temperature=1.0, mass_bits=16
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
        validate_probability_contract(None, 8)
    with pytest.raises(ValueError, match=r"\[1, 52\]"):
        allocate_integer_mass((0.5, 0.5), mass_bits=0)
    with pytest.raises(ValueError, match="non-negative"):
        allocate_integer_mass((0.6, -0.1, 0.5), mass_bits=16)
    with pytest.raises(ValueError, match="mutually exclusive"):
        validate_probability_contract(None, 16, 3, "waterfill")


def test_decimal_contract_remains_normalized_and_positive() -> None:
    probabilities = decimal_quantized_probabilities((0.4, 0.3, 0.2, 0.1), "1e-15")

    assert sum(probabilities, start=Fraction(0)) == 1
    assert all(value > 0 for value in probabilities)


def test_support_feasible_bits_track_candidate_count_and_headroom() -> None:
    assert support_feasible_mass_bits(1) == 1
    assert support_feasible_mass_bits(4) == 2
    assert support_feasible_mass_bits(5) == 3
    assert support_feasible_mass_bits(5, headroom_bits=2) == 5


def test_low_mass_width_is_available_for_audit_but_must_preserve_support() -> None:
    allocation = allocate_integer_mass(
        (Fraction(2, 5), Fraction(3, 10), Fraction(1, 5), Fraction(1, 10)),
        mass_bits=2,
        preserve_support=True,
    )
    assert allocation.counts == (1, 1, 1, 1)

    with pytest.raises(ValueError, match="too small"):
        allocate_integer_mass(
            (Fraction(1, 3), Fraction(1, 3), Fraction(1, 3)),
            mass_bits=1,
            preserve_support=True,
        )


def test_waterfill_projection_and_apportionment_reduce_tail_overweighting() -> None:
    target = (Fraction(3, 5), Fraction(1, 4), Fraction(1, 10), Fraction(1, 20))

    projected = waterfilled_support_target(target, mass_bits=4)
    base = allocate_integer_mass(
        target, mass_bits=4, preserve_support=True, support_strategy="base"
    )
    waterfill = allocate_integer_mass(
        target, mass_bits=4, preserve_support=True, support_strategy="waterfill"
    )

    assert projected == (
        Fraction(45, 76),
        Fraction(75, 304),
        Fraction(15, 152),
        Fraction(1, 16),
    )
    assert base.counts == (8, 4, 2, 2)
    assert waterfill.counts == (9, 4, 2, 1)
    assert all(count > 0 for count in waterfill.counts)


def test_integer_mass_audit_reports_exact_tv_and_finite_kl() -> None:
    target = (Fraction(2, 5), Fraction(3, 10), Fraction(1, 5), Fraction(1, 10))
    allocation = allocate_integer_mass(target, mass_bits=4, preserve_support=True)

    audit = audit_integer_mass(target, allocation)

    assert audit.total_variation == Fraction(3, 80)
    assert audit.max_absolute_error == Fraction(1, 40)
    assert audit.target_to_implemented_kl_nats > 0
    assert audit.implemented_to_target_kl_nats > 0


def test_integer_mass_audit_reports_infinite_kl_when_support_is_removed() -> None:
    target = (Fraction(9_999_999_999, 10_000_000_000), Fraction(1, 10_000_000_000))
    allocation = allocate_integer_mass(target, mass_bits=16, preserve_support=False)

    audit = audit_integer_mass(target, allocation)

    assert audit.target_to_implemented_kl_nats == float("inf")


def test_support_preserving_tv_bound_covers_base_allocations() -> None:
    target = (Fraction(3, 5), Fraction(1, 4), Fraction(1, 10), Fraction(1, 20))
    allocation = allocate_integer_mass(
        target, mass_bits=4, preserve_support=True, support_strategy="base"
    )

    audit = audit_integer_mass(target, allocation)
    bound = support_preserving_tv_upper_bound(len(target), mass_bits=4)

    assert audit.total_variation < bound
    assert support_preserving_tv_upper_bound(1, mass_bits=16) == 0
    assert support_preserving_tv_upper_bound(2, mass_bits=16) == Fraction(1, 32768)
