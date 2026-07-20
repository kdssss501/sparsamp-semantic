from __future__ import annotations

import hashlib
from typing import Hashable

from sparsamp_semantic.byte_sliced import ByteSlicedCodec, ByteSlicedConfig
from sparsamp_semantic.contract_list import ContractListByteDecoder, ContractListConfig, enumerate_contracts
from sparsamp_semantic.providers.base import Provider, ProviderSession
from sparsamp_semantic.types import DistributionSnapshot, TokenCandidate


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
