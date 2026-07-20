from __future__ import annotations

import hashlib
from fractions import Fraction
from typing import Hashable

from sparsamp_semantic.byte_sliced import ByteSlicedCodec, ByteSlicedConfig
from sparsamp_semantic.contract_list import (
    ContractListByteDecoder,
    ContractListConfig,
    _State,
    _child_symbol_values,
    _prune_states,
    enumerate_contracts,
)
from sparsamp_semantic.providers.base import Provider, ProviderSession
from sparsamp_semantic.types import DistributionSnapshot, TokenCandidate
from sparsamp_semantic.core import _ceil_fraction


class BinarySession(ProviderSession):
    def __init__(self, prompt: str) -> None:
        self.prompt = prompt
        self.items: list[int] = []

    @property
    def context_id(self) -> bytes:
        return hashlib.sha256(self.prompt.encode()).digest()

    @property
    def generated_token_ids(self) -> tuple[Hashable, ...]:
        return tuple(self.items)

    def next_distribution(self) -> DistributionSnapshot:
        return DistributionSnapshot(
            candidates=(
                TokenCandidate(0, "0", 0.5, rank=0),
                TokenCandidate(1, "1", 0.5, rank=1),
            ),
            native_token_id=0,
            metadata={"quantized_logit_bins": {0: 0, 1: 0}},
        )

    def append(self, token_id: Hashable) -> None:
        if token_id not in {0, 1}:
            raise ValueError("outside binary support")
        self.items.append(int(token_id))

    def render(self) -> str:
        return "".join(str(item) for item in self.items)


class BinaryProvider(Provider):
    def start(self, prompt: str) -> ProviderSession:
        return BinarySession(prompt)


def test_contract_envelope_deduplicates_equivalent_common_bin_shifts() -> None:
    snapshot = DistributionSnapshot(
        candidates=tuple(TokenCandidate(i, str(i), 0.25, rank=i) for i in range(4)),
        metadata={"quantized_logit_bins": {0: 0, 1: -1, 2: -2, 3: -3}},
    )
    contracts = enumerate_contracts(snapshot, ContractListConfig(top_k=4, bin_radius=1))
    assert contracts
    assert len({(item.token_ids, item.probabilities) for item in contracts}) == len(contracts)
    assert all(sum(item.probabilities) == 1 for item in contracts)


def test_contract_list_contains_mock_true_symbols_without_reference_distributions() -> None:
    key = b"contract-list-test-key"
    prompt = "contract list mock"
    payload = b"\x5a"
    provider = BinaryProvider()
    encoded = ByteSlicedCodec(ByteSlicedConfig(window_tokens=8, parity_bytes=0)).encode(
        provider.start(prompt), payload, key
    )
    session = provider.start(prompt)
    result = ContractListByteDecoder(
        ContractListConfig(window_tokens=8, top_k=2, bin_radius=0, beam_width=4096)
    ).decode(session, encoded.token_ids, key, stream_context_id=provider.start(prompt).context_id)
    assert result.error is None
    assert payload[0] in result.windows[0].candidates


def test_contract_list_requires_original_stream_context() -> None:
    config = ContractListConfig()
    assert config.top_k == 4
    assert ContractListByteDecoder(config).config.bin_radius == 1


def test_residual_symbol_mapping_matches_modular_inverse() -> None:
    parent = tuple(range(8))
    assert _child_symbol_values(parent, 3, 4) == (3, 4, 5, 6)
    assert _child_symbol_values(parent, -2, 4) == (6, 7, 0, 1)
    child = _child_symbol_values(parent, -2, 4)
    assert _child_symbol_values(child, 3, 1) == (1,)


def test_residual_mapping_matches_exhaustive_encoder_transition() -> None:
    symbol_values = tuple(range(256))
    n_value = len(symbol_values)
    for lower, upper, random_value in (
        (Fraction(0), Fraction(3, 10), Fraction(17, 97)),
        (Fraction(3, 10), Fraction(1), Fraction(17, 97)),
        (Fraction(0), Fraction(1, 2), Fraction(99, 101)),
        (Fraction(1, 2), Fraction(1), Fraction(99, 101)),
    ):
        temp0 = _ceil_fraction((lower - random_value) * n_value)
        temp1 = _ceil_fraction((upper - random_value) * n_value)
        child = _child_symbol_values(symbol_values, temp0, temp1 - temp0)
        observed: dict[int, int] = {}
        for current_index, symbol in enumerate(symbol_values):
            sample = (Fraction(current_index, n_value) + random_value) % 1
            if lower <= sample < upper:
                wrapped = current_index + random_value * n_value >= n_value
                child_index = current_index - n_value - temp0 if wrapped else current_index - temp0
                observed[child_index] = symbol
        assert tuple(observed[index] for index in range(len(observed))) == child


def test_symbol_stratified_pruning_retains_low_cost_state_per_symbol() -> None:
    raw = [_State((symbol,), 1000 + symbol) for symbol in range(256)]
    raw.extend(_State((symbol, (symbol + 1) % 256), symbol) for symbol in range(100))
    states = {state.symbol_values: state for state in raw}
    config = ContractListConfig(beam_width=256, symbol_quota=1)
    retained, pruned = _prune_states(states, config)
    assert len(retained) == 256
    assert pruned == 100
    assert set(range(256)) == {
        symbol for state in retained for symbol in state.symbol_values
    }


def test_symbol_quota_requires_sufficient_beam_width() -> None:
    try:
        ContractListConfig(beam_width=255, symbol_quota=1)
    except ValueError as error:
        assert "256 * quota" in str(error)
    else:
        raise AssertionError("expected invalid symbol quota to fail")
