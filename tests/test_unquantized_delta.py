from fractions import Fraction

from scripts.audit_unquantized_delta import unquantized_choice
from sparsamp_semantic.types import TokenCandidate


def candidate(token_id: int, probability: float, rank: int) -> TokenCandidate:
    return TokenCandidate(
        token_id=token_id,
        text=str(token_id),
        probability=probability,
        rank=rank,
    )


def test_unquantized_choice_uses_ranked_support_and_canonical_order() -> None:
    candidates = (
        candidate(30, 0.6, 0),
        candidate(10, 0.3, 1),
        candidate(20, 0.1, 2),
    )

    assert unquantized_choice(candidates, Fraction(0), 2) == 10
    assert unquantized_choice(candidates, Fraction(1, 4), 2) == 10
    assert unquantized_choice(candidates, Fraction(1, 2), 2) == 30


def test_unquantized_choice_renormalizes_selected_support() -> None:
    candidates = (
        candidate(1, 0.4, 0),
        candidate(2, 0.3, 1),
        candidate(3, 0.3, 2),
    )

    assert unquantized_choice(candidates, Fraction(3, 5), 2) == 2


def test_unquantized_choice_caps_at_positive_support() -> None:
    candidates = (candidate(9, 1.0, 0),)

    assert unquantized_choice(candidates, Fraction(3, 5), 16) == 9
