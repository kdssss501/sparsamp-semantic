"""Reference-only decision screens for top-k support replacements.

The screen models the nearest feasible top-2 support change: rank three replaces
rank two.  It is deliberately a *screen*, rather than a complete finite-
precision certificate: the claim holds under the calibrated nearest-challenger
model and must be validated on independent replay traces.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .probability_contract import allocate_logit_bin_mass
from .replay_certificate import ReplayContractConfig, public_replay_fraction


@dataclass(frozen=True)
class NearestChallengerWitness:
    """A public counterfactual decision for one reference contract step."""

    rank2_rank3_gap_bins: int
    challenger_eligible: bool
    counterfactual_token_id: int | None
    decision_sensitive: bool


def _choice_from_contract(
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
    cumulative = 0
    for token_id, count in zip(ids, allocation.counts, strict=True):
        cumulative += count
        if mass_index < cumulative:
            return token_id
    raise RuntimeError("integer mass allocation did not cover the public sample")


def nearest_challenger_witness(
    envelope_token_ids: Sequence[int],
    envelope_logit_bins: Sequence[int],
    reference_token_id: int,
    *,
    step: int,
    context: bytes,
    config: ReplayContractConfig,
    support_gap_bins: int,
) -> NearestChallengerWitness:
    """Screen a rank-3-for-rank-2 replacement using only reference features.

    If the reference rank-2/rank-3 gap exceeds the frozen calibration radius,
    rank three is not an admissible nearest challenger.  Otherwise we replay
    the same public fraction on the counterfactual support ``{rank1, rank3}``.
    A correction is needed only when that counterfactual changes the public
    token decision.
    """

    ids = tuple(int(value) for value in envelope_token_ids)
    bins = tuple(int(value) for value in envelope_logit_bins)
    if len(ids) != len(bins) or len(ids) < 3:
        raise ValueError("the support screen requires aligned top-3 envelope data")
    if len(set(ids)) != len(ids):
        raise ValueError("envelope token IDs must be unique")
    if support_gap_bins < 0:
        raise ValueError("support gap threshold must be non-negative")
    if any(left < right for left, right in zip(bins, bins[1:], strict=False)):
        raise ValueError("envelope logits must be sorted in descending rank order")

    gap = bins[1] - bins[2]
    eligible = gap <= support_gap_bins
    if not eligible:
        return NearestChallengerWitness(gap, False, None, False)
    counterfactual = _choice_from_contract(
        (ids[0], ids[2]),
        (bins[0], bins[2]),
        step=step,
        context=context,
        config=config,
    )
    return NearestChallengerWitness(
        rank2_rank3_gap_bins=gap,
        challenger_eligible=True,
        counterfactual_token_id=counterfactual,
        decision_sensitive=counterfactual != int(reference_token_id),
    )
