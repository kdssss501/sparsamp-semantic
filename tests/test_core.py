from __future__ import annotations

import pytest

from sparsamp_semantic.core import CodecConfig, SparSampCodec
from sparsamp_semantic.providers.mock import MockProvider


@pytest.mark.parametrize("block_size", [2, 4, 8, 16, 32, 64])
def test_mock_round_trip(block_size: int) -> None:
    bits = "10110100101101101001011100101100"
    codec = SparSampCodec(CodecConfig(block_size=block_size, max_tokens=5000))
    provider = MockProvider()
    key = b"0123456789abcdef0123456789abcdef"
    prompt = "Explain why deterministic tests matter."

    encoded = codec.encode(provider.start(prompt), bits, key)
    decoded = codec.decode(provider.start(prompt), list(encoded.token_ids), key)

    assert decoded.bits[: len(bits)] == bits
    assert encoded.text
    assert encoded.bits_per_token > 0


def test_encoding_is_deterministic_for_same_context() -> None:
    codec = SparSampCodec(CodecConfig(block_size=8, max_tokens=1000))
    provider = MockProvider()
    key = b"0123456789abcdef0123456789abcdef"
    bits = "0110100101101110"
    prompt = "A fixed prompt"

    first = codec.encode(provider.start(prompt), bits, key)
    second = codec.encode(provider.start(prompt), bits, key)

    assert first.token_ids == second.token_ids
    assert first.text == second.text


def test_wrong_prompt_fails_or_changes_bits() -> None:
    codec = SparSampCodec(CodecConfig(block_size=8, max_tokens=1000))
    provider = MockProvider()
    key = b"0123456789abcdef0123456789abcdef"
    encoded = codec.encode(provider.start("prompt-a"), "10100101", key)

    decoded = codec.decode(provider.start("prompt-b"), list(encoded.token_ids), key)
    assert decoded.bits != "10100101"
