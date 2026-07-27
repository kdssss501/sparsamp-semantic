"""Pure diagnostics for transitions between discrete probability contracts."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Literal, Sequence


TransitionCause = Literal["no_flip", "support_flip", "mass_flip"]


@dataclass(frozen=True)
class ContractTransition:
    """One reference-to-target transition under a shared public sample."""

    cause: TransitionCause
    support_exact: bool
    counts_exact: bool
    decision_exact: bool
    support_overlap: int
    count_total_variation: Fraction | None


def rank_cutoff_gap(logit_bins: Sequence[int], *, cutoff: int) -> int:
    """Return the integer-bin gap across one rank cutoff."""

    bins = tuple(int(value) for value in logit_bins)
    if not 1 <= cutoff < len(bins):
        raise ValueError("cutoff must have candidates on both sides")
    if any(left < right for left, right in zip(bins, bins[1:], strict=False)):
        raise ValueError("logit bins must be in non-increasing rank order")
    return bins[cutoff - 1] - bins[cutoff]


def aligned_count_total_variation(
    reference_token_ids: Sequence[int],
    reference_counts: Sequence[int],
    target_token_ids: Sequence[int],
    target_counts: Sequence[int],
) -> Fraction | None:
    """Return exact count TV when the two contracts have identical support."""

    reference_ids = tuple(int(value) for value in reference_token_ids)
    target_ids = tuple(int(value) for value in target_token_ids)
    reference_values = tuple(int(value) for value in reference_counts)
    target_values = tuple(int(value) for value in target_counts)
    if len(reference_ids) != len(reference_values) or len(target_ids) != len(target_values):
        raise ValueError("token IDs and counts must align")
    if len(set(reference_ids)) != len(reference_ids) or len(set(target_ids)) != len(target_ids):
        raise ValueError("contract support must not contain duplicate token IDs")
    if any(value < 0 for value in (*reference_values, *target_values)):
        raise ValueError("contract counts must be non-negative")
    if set(reference_ids) != set(target_ids):
        return None
    reference_total = sum(reference_values)
    target_total = sum(target_values)
    if reference_total < 1 or reference_total != target_total:
        raise ValueError("aligned contracts must have equal positive total mass")
    reference = dict(zip(reference_ids, reference_values, strict=True))
    target = dict(zip(target_ids, target_values, strict=True))
    l1 = sum(abs(reference[token_id] - target[token_id]) for token_id in reference)
    return Fraction(l1, 2 * reference_total)


def classify_contract_transition(
    *,
    reference_token_ids: Sequence[int],
    reference_counts: Sequence[int],
    reference_choice: int,
    target_token_ids: Sequence[int],
    target_counts: Sequence[int],
    target_choice: int,
) -> ContractTransition:
    """Separate decision flips caused by support and mass transitions."""

    reference_ids = tuple(int(value) for value in reference_token_ids)
    target_ids = tuple(int(value) for value in target_token_ids)
    support_exact = set(reference_ids) == set(target_ids)
    tv = aligned_count_total_variation(
        reference_ids,
        reference_counts,
        target_ids,
        target_counts,
    )
    counts_exact = support_exact and tv == 0
    decision_exact = int(reference_choice) == int(target_choice)
    if decision_exact:
        cause: TransitionCause = "no_flip"
    elif not support_exact:
        cause = "support_flip"
    elif not counts_exact:
        cause = "mass_flip"
    else:
        raise ValueError("identical discrete contracts cannot produce different choices")
    return ContractTransition(
        cause=cause,
        support_exact=support_exact,
        counts_exact=counts_exact,
        decision_exact=decision_exact,
        support_overlap=len(set(reference_ids) & set(target_ids)),
        count_total_variation=tv,
    )
