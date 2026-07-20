"""Bounded soft list recovery over short Reed-Solomon codebooks."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Iterable, Mapping, Sequence


Score = tuple[int, int]


@dataclass(frozen=True)
class ListRecoveryConfig:
    payload_bytes: int = 2
    parity_bytes: int = 2
    cost_threshold: int = 1
    enumeration_limit: int = 1 << 16

    def __post_init__(self) -> None:
        if self.payload_bytes < 1 or self.parity_bytes < 1:
            raise ValueError("payload and parity bytes must be positive")
        if self.payload_bytes + self.parity_bytes > 255:
            raise ValueError("RS codeword must contain at most 255 bytes")
        if self.cost_threshold < 0 or self.enumeration_limit < 1:
            raise ValueError("cost threshold and enumeration limit must be non-negative")
        if 256**self.payload_bytes > self.enumeration_limit:
            raise ValueError("payload codebook exceeds enumeration limit")


@dataclass(frozen=True)
class ListRecoveryResult:
    payload: bytes | None
    best_score: Score
    best_tie_count: int
    runner_up_score: Score | None
    enumerated_payloads: int

    @property
    def unique(self) -> bool:
        return self.payload is not None and self.best_tie_count == 1


def candidate_cost_map(
    candidates: Sequence[int], costs: Sequence[int]
) -> dict[int, int]:
    if len(candidates) != len(costs):
        raise ValueError("candidate and cost lengths differ")
    result: dict[int, int] = {}
    for candidate, cost in zip(candidates, costs, strict=True):
        if not 0 <= int(candidate) <= 255 or int(cost) < 0:
            raise ValueError("candidate bytes and costs must be non-negative")
        value = int(candidate)
        result[value] = min(int(cost), result.get(value, int(cost)))
    return result


def score_codeword(
    codeword: bytes, cost_maps: Sequence[Mapping[int, int]], cost_threshold: int
) -> Score:
    """Return misses first, then accumulated in-list contract cost."""

    if len(codeword) != len(cost_maps):
        raise ValueError("codeword and candidate-list lengths differ")
    misses = 0
    observed_cost = 0
    for symbol, costs in zip(codeword, cost_maps, strict=True):
        cost = costs.get(symbol)
        if cost is None or cost > cost_threshold:
            misses += 1
        else:
            observed_cost += cost
    return misses, observed_cost


def iter_rs_payload_scores(
    cost_maps: Sequence[Mapping[int, int]], config: ListRecoveryConfig
) -> Iterable[tuple[bytes, Score]]:
    if len(cost_maps) != config.payload_bytes + config.parity_bytes:
        raise ValueError("candidate-list count does not match RS codeword length")
    try:
        from reedsolo import RSCodec
    except ImportError as error:
        raise RuntimeError("list recovery requires the optional reedsolo package") from error

    codec = RSCodec(config.parity_bytes)
    for values in product(range(256), repeat=config.payload_bytes):
        payload = bytes(values)
        codeword = bytes(codec.encode(payload))
        yield payload, score_codeword(codeword, cost_maps, config.cost_threshold)


def decode_rs_lists(
    windows: Sequence[tuple[Sequence[int], Sequence[int]]],
    config: ListRecoveryConfig | None = None,
) -> ListRecoveryResult:
    """Select the unique minimum-loss payload without an expected-message oracle."""

    active_config = config or ListRecoveryConfig()
    cost_maps = [candidate_cost_map(candidates, costs) for candidates, costs in windows]
    best_score: Score | None = None
    runner_up: Score | None = None
    best_payload: bytes | None = None
    best_ties = 0
    enumerated = 0
    for payload, score in iter_rs_payload_scores(cost_maps, active_config):
        enumerated += 1
        if best_score is None or score < best_score:
            runner_up = best_score
            best_score = score
            best_payload = payload
            best_ties = 1
        elif score == best_score:
            best_ties += 1
            best_payload = None
        elif runner_up is None or score < runner_up:
            runner_up = score
    if best_score is None:
        raise RuntimeError("empty payload codebook")
    return ListRecoveryResult(
        best_payload, best_score, best_ties, runner_up, enumerated
    )
