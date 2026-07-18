from __future__ import annotations

import pytest

from sparsamp_semantic.core import CodecConfig, IncompleteEncodeError, SparSampCodec
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


def test_integer_mass_core_round_trip_preserves_support() -> None:
    codec = SparSampCodec(
        CodecConfig(
            block_size=16,
            max_tokens=1000,
            probability_quantum=None,
            probability_mass_bits=16,
            preserve_probability_support=True,
        )
    )
    provider = MockProvider()
    key = b"0123456789abcdef0123456789abcdef"
    bits = "10110100101101101001011100101100"

    encoded = codec.encode(provider.start("integer core"), bits, key)
    decoded = codec.decode(provider.start("integer core"), encoded.token_ids, key)

    assert decoded.bits[: len(bits)] == bits
    assert encoded.quantization_support_loss_count == 0
    assert encoded.forward_quantization_kl_nats >= 0


def test_support_adaptive_waterfill_core_round_trip_records_effective_bits() -> None:
    codec = SparSampCodec(
        CodecConfig(
            block_size=8,
            max_tokens=1000,
            probability_quantum=None,
            probability_mass_headroom_bits=3,
            probability_support_strategy="waterfill",
            preserve_probability_support=True,
        )
    )
    provider = MockProvider()
    key = b"0123456789abcdef0123456789abcdef"
    bits = "1011010010110100"

    encoded = codec.encode(provider.start("adaptive integer core"), bits, key)
    decoded = codec.decode(provider.start("adaptive integer core"), encoded.token_ids, key)

    assert decoded.bits[: len(bits)] == bits
    assert all(record.effective_probability_mass_bits == 5 for record in encoded.records)


def test_wrong_prompt_fails_or_changes_bits() -> None:
    codec = SparSampCodec(CodecConfig(block_size=8, max_tokens=1000))
    provider = MockProvider()
    key = b"0123456789abcdef0123456789abcdef"
    encoded = codec.encode(provider.start("prompt-a"), "10100101", key)

    decoded = codec.decode(provider.start("prompt-b"), list(encoded.token_ids), key)
    assert decoded.bits != "10100101"


def test_incomplete_encode_error_retains_partial_progress() -> None:
    provider = MockProvider()
    codec = SparSampCodec(CodecConfig(block_size=8, max_tokens=1))
    with pytest.raises(IncompleteEncodeError) as captured:
        codec.encode(provider.start("short budget"), "10100101" * 4, b"0123456789abcdef")
    error = captured.value
    assert len(error.token_ids) == 1
    assert len(error.records) == 1
    assert error.total_blocks == 4
    assert 0 <= error.completed_blocks < error.total_blocks
