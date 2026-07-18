from __future__ import annotations

import pytest

from sparsamp_semantic.core import IncompleteEncodeError
from sparsamp_semantic.providers.mock import MockProvider
from sparsamp_semantic.rrc import RrcConfig, RotationRangeCodec


KEY = b"0123456789abcdef0123456789abcdef"


@pytest.mark.parametrize("bit_length", [1, 13, 64, 128])
def test_verified_rrc_mock_round_trip(bit_length: int) -> None:
    bits = ("10110100" * 20)[:bit_length]
    codec = RotationRangeCodec(RrcConfig(message_bits=bit_length, max_tokens=1000))
    provider = MockProvider()
    prompt = "Explain rotation range coding."

    encoded = codec.encode(provider.start(prompt), bits, KEY)
    decoded = codec.decode(provider.start(prompt), encoded.token_ids, KEY)

    assert decoded.bits == bits
    assert encoded.padded_bits == 0
    assert encoded.records[-1].block_completed
    assert encoded.bits_per_token > 0


def test_paper_rrc_has_a_modular_wrap_counterexample() -> None:
    """Algorithm 3's local stop test does not survive every reverse rotation."""

    bits = ("10110100" * 20)[:64]
    codec = RotationRangeCodec(
        RrcConfig(message_bits=64, max_tokens=1000, termination_mode="paper")
    )
    provider = MockProvider()
    prompt = "Explain rotation range coding."

    encoded = codec.encode(provider.start(prompt), bits, KEY)
    decoded = codec.decode(provider.start(prompt), encoded.token_ids, KEY)

    assert decoded.bits != bits
    assert int(decoded.bits, 2) - int(bits, 2) == -2


def test_verified_rrc_extends_the_known_counterexample() -> None:
    bits = ("10110100" * 20)[:64]
    provider = MockProvider()
    prompt = "Explain rotation range coding."
    paper = RotationRangeCodec(
        RrcConfig(message_bits=64, max_tokens=1000, termination_mode="paper")
    ).encode(provider.start(prompt), bits, KEY)
    verified_codec = RotationRangeCodec(RrcConfig(message_bits=64, max_tokens=1000))
    verified = verified_codec.encode(provider.start(prompt), bits, KEY)
    decoded = verified_codec.decode(provider.start(prompt), verified.token_ids, KEY)

    assert decoded.bits == bits
    assert len(verified.token_ids) > len(paper.token_ids)


def test_rrc_is_deterministic_for_same_context() -> None:
    codec = RotationRangeCodec(RrcConfig(message_bits=32, max_tokens=100))
    provider = MockProvider()
    bits = "01101001011011100110111001100101"

    first = codec.encode(provider.start("fixed prompt"), bits, KEY)
    second = codec.encode(provider.start("fixed prompt"), bits, KEY)

    assert first.token_ids == second.token_ids
    assert first.text == second.text


def test_integer_mass_verified_rrc_round_trip() -> None:
    bits = "10110100101101101001011100101100"
    codec = RotationRangeCodec(
        RrcConfig(
            message_bits=len(bits),
            max_tokens=1000,
            probability_quantum=None,
            probability_mass_bits=16,
        )
    )
    provider = MockProvider()

    encoded = codec.encode(provider.start("integer rrc"), bits, KEY)
    decoded = codec.decode(provider.start("integer rrc"), encoded.token_ids, KEY)

    assert decoded.bits == bits
    assert encoded.quantization_support_loss_count == 0


def test_rrc_wrong_prompt_changes_recovered_payload() -> None:
    codec = RotationRangeCodec(RrcConfig(message_bits=32, max_tokens=100))
    provider = MockProvider()
    bits = "10100101101001011010010110100101"
    encoded = codec.encode(provider.start("prompt-a"), bits, KEY)

    decoded = codec.decode(provider.start("prompt-b"), encoded.token_ids, KEY)

    assert decoded.bits != bits


def test_rrc_rejects_wrong_payload_length() -> None:
    codec = RotationRangeCodec(RrcConfig(message_bits=16))

    with pytest.raises(ValueError, match="exactly 16 bits"):
        codec.encode(MockProvider().start("prompt"), "1010", KEY)


def test_rrc_incomplete_error_retains_generated_prefix() -> None:
    codec = RotationRangeCodec(RrcConfig(message_bits=128, max_tokens=1))

    with pytest.raises(IncompleteEncodeError) as captured:
        codec.encode(MockProvider().start("short budget"), "10" * 64, KEY)

    assert len(captured.value.token_ids) == 1
    assert captured.value.completed_bits == 0
    assert captured.value.total_blocks == 1
