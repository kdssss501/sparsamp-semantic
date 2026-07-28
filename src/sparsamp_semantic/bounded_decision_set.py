"""Finite abstract interpretation for public top-k contract decisions."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product
from typing import Sequence

from .probability_contract import allocate_logit_bin_mass
from .replay_certificate import ReplayContractConfig, public_replay_fraction


@dataclass(frozen=True)
class BoundedDecisionWitness:
    """All public decisions admitted by a bounded reference-envelope model."""

    possible_token_ids: tuple[int, ...]
    feasible_pair_count: int
    feasible_contract_count: int
    unknown_tail_possible: bool
    decision_invariant: bool


def _contract_choice(
    token_ids: Sequence[int],
    logit_bins: Sequence[int],
    *,
    step: int,
    context: bytes,
    config: ReplayContractConfig,
) -> int:
    ordered = sorted(zip(token_ids, logit_bins, strict=True), key=lambda item: item[0])
    ids = tuple(int(token_id) for token_id, _ in ordered)
    bins = tuple(int(logit_bin) for _, logit_bin in ordered)
    allocation = allocate_logit_bin_mass(
        ids,
        bins,
        quantum=config.logit_quantum,
        temperature=config.temperature,
        mass_bits=config.mass_bits,
    )
    fraction = public_replay_fraction(step, context, config.public_seed)
    mass_index = fraction.numerator * allocation.total_mass // fraction.denominator
    total = 0
    for token_id, count in zip(ids, allocation.counts, strict=True):
        total += count
        if mass_index < total:
            return token_id
    raise RuntimeError("integer mass allocation did not cover the public sample")


def _feasible_pairs(lower: tuple[int, ...], upper: tuple[int, ...]) -> tuple[tuple[int, int], ...]:
    pairs: list[tuple[int, int]] = []
    for first, second in combinations(range(len(lower)), 2):
        other_lower = max(
            (value for index, value in enumerate(lower) if index not in {first, second}),
            default=-10**9,
        )
        if min(upper[first], upper[second]) >= other_lower:
            pairs.append((first, second))
    return tuple(pairs)


def bounded_decision_witness(
    envelope_token_ids: Sequence[int],
    envelope_logit_bins: Sequence[int],
    reference_token_id: int,
    *,
    step: int,
    context: bytes,
    config: ReplayContractConfig,
    bin_shift_radius: int,
) -> BoundedDecisionWitness:
    """Enumerate public choices under bounded logit-bin perturbations.

    This is an intentionally conservative finite abstraction.  It includes
    every envelope pair that can be top-2 under interval endpoints, every
    integer bin assignment for that pair, and an unknown-tail alarm whenever a
    token below the stored envelope could itself join top-2.
    """

    ids = tuple(int(value) for value in envelope_token_ids)
    bins = tuple(int(value) for value in envelope_logit_bins)
    if len(ids) != len(bins) or len(ids) < 3:
        raise ValueError("bounded decisions require aligned top-3 envelope data")
    if len(set(ids)) != len(ids):
        raise ValueError("envelope token IDs must be unique")
    if bin_shift_radius < 0:
        raise ValueError("bin shift radius must be non-negative")
    if any(left < right for left, right in zip(bins, bins[1:], strict=False)):
        raise ValueError("envelope logits must be sorted in descending rank order")

    lower = tuple(value - bin_shift_radius for value in bins)
    upper = tuple(value + bin_shift_radius for value in bins)
    pairs = _feasible_pairs(lower, upper)
    possible: set[int] = set()
    contract_count = 0
    for first, second in pairs:
        for first_bin, second_bin in product(
            range(lower[first], upper[first] + 1),
            range(lower[second], upper[second] + 1),
        ):
            possible.add(
                _contract_choice(
                    (ids[first], ids[second]),
                    (first_bin, second_bin),
                    step=step,
                    context=context,
                    config=config,
                )
            )
            contract_count += 1

    second_highest_lower = sorted(lower, reverse=True)[1]
    unknown_tail = upper[-1] >= second_highest_lower
    invariant = not unknown_tail and possible == {int(reference_token_id)}
    return BoundedDecisionWitness(
        possible_token_ids=tuple(sorted(possible)),
        feasible_pair_count=len(pairs),
        feasible_contract_count=contract_count,
        unknown_tail_possible=unknown_tail,
        decision_invariant=invariant,
    )
