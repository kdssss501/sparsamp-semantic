"""Bounded list decoding for finite-precision byte-sliced SparSamp."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations, product
from typing import Any, Hashable

from .core import _ceil_fraction
from .prf import HmacRandomStream
from .probability_contract import allocate_logit_bin_mass
from .providers.base import ProviderSession
from .types import DistributionSnapshot


@dataclass(frozen=True)
class ContractListConfig:
    window_tokens: int = 32
    top_k: int = 4
    bin_radius: int = 1
    logit_quantum: float = 0.5
    bin_mass_bits: int = 16
    temperature: float = 1.2
    beam_width: int = 4096

    def __post_init__(self) -> None:
        if self.window_tokens < 1 or self.top_k < 2 or self.bin_radius < 0:
            raise ValueError("invalid window, top-k, or bin radius")
        if self.logit_quantum <= 0 or self.temperature <= 0:
            raise ValueError("quantum and temperature must be positive")
        if not 16 <= self.bin_mass_bits <= 52 or self.beam_width < 1:
            raise ValueError("invalid mass bits or beam width")


@dataclass(frozen=True)
class _Contract:
    token_ids: tuple[int, int]
    probabilities: tuple[Fraction, Fraction]
    cost: int


@dataclass(frozen=True)
class _State:
    n_value: int
    temp0_values: tuple[int, ...]
    n_values: tuple[int, ...]
    cost: int


@dataclass(frozen=True)
class ContractListWindow:
    window_index: int
    candidates: tuple[int, ...]
    candidate_costs: tuple[int, ...]
    peak_active_states: int
    pruned_states: int
    exhausted: bool


@dataclass(frozen=True)
class ContractListResult:
    windows: tuple[ContractListWindow, ...]
    consumed_tokens: int
    error: str | None = None


def enumerate_contracts(
    snapshot: DistributionSnapshot, config: ContractListConfig
) -> tuple[_Contract, ...]:
    """Enumerate and deduplicate the local support/bin hypothesis envelope."""

    ranked = sorted(snapshot.candidates, key=lambda candidate: int(candidate.rank))
    if len(ranked) < config.top_k:
        raise ValueError("snapshot has fewer candidates than contract-list top_k")
    ranked = ranked[: config.top_k]
    bins_raw = snapshot.metadata.get("quantized_logit_bins")
    if not isinstance(bins_raw, dict):
        raise ValueError("snapshot does not expose quantized_logit_bins")
    bins = {int(token_id): int(value) for token_id, value in bins_raw.items()}
    best: dict[tuple[tuple[int, int], tuple[int, int]], _Contract] = {}
    for left, right in combinations(ranked, 2):
        pair = sorted((left, right), key=lambda candidate: int(candidate.token_id))
        token_ids = (int(pair[0].token_id), int(pair[1].token_id))
        rank_cost = int(left.rank) + int(right.rank) - 1
        for offsets in product(
            range(-config.bin_radius, config.bin_radius + 1), repeat=2
        ):
            logit_bins = [bins[token_id] + offset for token_id, offset in zip(token_ids, offsets)]
            allocation = allocate_logit_bin_mass(
                token_ids,
                logit_bins,
                quantum=config.logit_quantum,
                temperature=config.temperature,
                mass_bits=config.bin_mass_bits,
            )
            cost = rank_cost + sum(abs(offset) for offset in offsets)
            contract = _Contract(token_ids, allocation.probabilities, cost)
            key = (token_ids, allocation.counts)
            if key not in best or cost < best[key].cost:
                best[key] = contract
    return tuple(sorted(best.values(), key=lambda item: (item.cost, item.token_ids, item.probabilities)))


def _recover_symbol(temp0_values: tuple[int, ...], n_values: tuple[int, ...]) -> int:
    index = len(temp0_values) - 2
    value = temp0_values[index + 1]
    while index >= 0:
        previous_n = n_values[index]
        value = temp0_values[index] + ((value + previous_n) % previous_n)
        index -= 1
    return value % 256


class ContractListByteDecoder:
    """Decode per-window symbol lists without access to the FP32 reference distribution."""

    def __init__(self, config: ContractListConfig | None = None) -> None:
        self.config = config or ContractListConfig()

    @staticmethod
    def _domain(window_index: int) -> bytes:
        return b"sparsamp-r029-byte-window\0" + window_index.to_bytes(8, "big")

    def decode(
        self,
        session: ProviderSession,
        token_ids: tuple[Hashable, ...] | list[Hashable],
        key: bytes,
        *,
        stream_context_id: bytes,
    ) -> ContractListResult:
        stream = HmacRandomStream(key, stream_context_id)
        window_count = (len(token_ids) + self.config.window_tokens - 1) // self.config.window_tokens
        windows: list[ContractListWindow] = []
        consumed = 0
        for window_index in range(window_count):
            active = {_State(256, (), (), 0)}
            resolved: dict[int, int] = {}
            peak = 1
            pruned = 0
            exhausted = False
            for local_step in range(self.config.window_tokens):
                if consumed >= len(token_ids):
                    exhausted = True
                    break
                observed = int(token_ids[consumed])
                snapshot = session.next_distribution()
                contracts = [
                    contract
                    for contract in enumerate_contracts(snapshot, self.config)
                    if observed in contract.token_ids
                ]
                r = stream.fraction(local_step, domain=self._domain(window_index))
                next_states: dict[tuple[Any, ...], _State] = {}
                for state in active:
                    for contract in contracts:
                        candidate_index = contract.token_ids.index(observed)
                        lower = sum(contract.probabilities[:candidate_index], start=Fraction(0))
                        upper = lower + contract.probabilities[candidate_index]
                        temp0 = _ceil_fraction((lower - r) * state.n_value)
                        temp1 = _ceil_fraction((upper - r) * state.n_value)
                        new_n = temp1 - temp0
                        if new_n < 1:
                            continue
                        temp0s = state.temp0_values + (temp0,)
                        n_values = state.n_values + (new_n,)
                        cost = state.cost + contract.cost
                        if new_n == 1:
                            symbol = _recover_symbol(temp0s, n_values)
                            resolved[symbol] = min(cost, resolved.get(symbol, cost))
                            continue
                        new_state = _State(new_n, temp0s, n_values, cost)
                        state_key = (new_n, temp0s, n_values)
                        old = next_states.get(state_key)
                        if old is None or cost < old.cost:
                            next_states[state_key] = new_state
                ordered = sorted(
                    next_states.values(),
                    key=lambda item: (item.cost, item.n_value, item.temp0_values),
                )
                if len(ordered) > self.config.beam_width:
                    pruned += len(ordered) - self.config.beam_width
                    ordered = ordered[: self.config.beam_width]
                active = set(ordered)
                peak = max(peak, len(active))
                try:
                    session.append(observed)
                except ValueError as error:
                    return ContractListResult(tuple(windows), consumed, str(error))
                consumed += 1
            ranked_symbols = sorted(resolved, key=lambda symbol: (resolved[symbol], symbol))
            windows.append(
                ContractListWindow(
                    window_index,
                    tuple(ranked_symbols),
                    tuple(resolved[symbol] for symbol in ranked_symbols),
                    peak,
                    pruned,
                    exhausted or not resolved,
                )
            )
        return ContractListResult(tuple(windows), consumed)
