from fractions import Fraction

import pytest

from sparsamp_semantic.contract_transition import (
    aligned_count_total_variation,
    classify_contract_transition,
    rank_cutoff_gap,
)


def test_rank_cutoff_gap_uses_ordered_integer_bins() -> None:
    assert rank_cutoff_gap((0, -1, -3, -3), cutoff=2) == 2
    with pytest.raises(ValueError, match="non-increasing"):
        rank_cutoff_gap((0, -2, -1), cutoff=2)


def test_aligned_count_tv_is_exact_and_token_order_invariant() -> None:
    assert aligned_count_total_variation((1, 2), (6, 4), (2, 1), (3, 7)) == Fraction(1, 10)
    assert aligned_count_total_variation((1, 2), (6, 4), (1, 3), (6, 4)) is None


def test_transition_separates_support_and_mass_flips() -> None:
    support = classify_contract_transition(
        reference_token_ids=(1, 2),
        reference_counts=(6, 4),
        reference_choice=2,
        target_token_ids=(1, 3),
        target_counts=(6, 4),
        target_choice=3,
    )
    mass = classify_contract_transition(
        reference_token_ids=(1, 2),
        reference_counts=(6, 4),
        reference_choice=1,
        target_token_ids=(2, 1),
        target_counts=(7, 3),
        target_choice=2,
    )
    stable = classify_contract_transition(
        reference_token_ids=(1, 2),
        reference_counts=(6, 4),
        reference_choice=1,
        target_token_ids=(1, 3),
        target_counts=(6, 4),
        target_choice=1,
    )
    assert support.cause == "support_flip"
    assert mass.cause == "mass_flip"
    assert mass.count_total_variation == Fraction(3, 10)
    assert stable.cause == "no_flip"


def test_identical_contract_cannot_flip() -> None:
    with pytest.raises(ValueError, match="identical discrete contracts"):
        classify_contract_transition(
            reference_token_ids=(1, 2),
            reference_counts=(6, 4),
            reference_choice=1,
            target_token_ids=(1, 2),
            target_counts=(6, 4),
            target_choice=2,
        )
