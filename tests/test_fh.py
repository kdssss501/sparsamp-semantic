from __future__ import annotations

import pytest

from sparsamp_semantic.fh import FhCodecConfig, FhSparSampCodec, select_block_size
from sparsamp_semantic.providers.mock import MockProvider


def test_controller_moves_from_small_to_large_blocks_with_capacity() -> None:
    config = FhCodecConfig(total_bits=128, max_tokens=192)

    assert select_block_size(config, remaining_bits=128, remaining_tokens=64, entropy_bits=1.0) == 8
    assert (
        select_block_size(config, remaining_bits=128, remaining_tokens=160, entropy_bits=1.0) == 16
    )
    assert (
        select_block_size(config, remaining_bits=128, remaining_tokens=192, entropy_bits=1.0) == 32
    )


@pytest.mark.parametrize("bit_length", [13, 64, 128])
def test_fh_mock_round_trip_without_padding(bit_length: int) -> None:
    bits = ("10110100" * 20)[:bit_length]
    codec = FhSparSampCodec(
        FhCodecConfig(total_bits=bit_length, block_sizes=(4, 8, 16), max_tokens=1000)
    )
    provider = MockProvider()
    key = b"0123456789abcdef0123456789abcdef"
    prompt = "Explain finite-horizon coding."

    encoded = codec.encode(provider.start(prompt), bits, key)
    decoded = codec.decode(provider.start(prompt), encoded.token_ids, key)

    assert decoded.bits == bits
    assert encoded.padded_bits == 0
    assert encoded.records[-1].completed_bits == bit_length
    assert all(record.block_size is None or record.block_size <= 16 for record in encoded.records)


def test_fh_rejects_payload_length_mismatch() -> None:
    codec = FhSparSampCodec(FhCodecConfig(total_bits=16))
    with pytest.raises(ValueError, match="exactly 16 bits"):
        codec.encode(MockProvider().start("prompt"), "1010", b"0123456789abcdef")


def test_scheduled_blocks_round_trip_and_match_requested_schedule() -> None:
    bits = "10110100" * 4
    codec = FhSparSampCodec(
        FhCodecConfig(
            total_bits=32,
            block_sizes=(8, 16),
            block_schedule=(16, 8, 8),
            max_tokens=500,
        )
    )
    provider = MockProvider()
    key = b"0123456789abcdef0123456789abcdef"
    encoded = codec.encode(provider.start("scheduled"), bits, key)
    decoded = codec.decode(provider.start("scheduled"), encoded.token_ids, key)

    assert decoded.bits == bits
    assert [record.block_size for record in encoded.records if record.block_completed] == [16, 8, 8]


def test_block_schedule_must_cover_public_payload_length() -> None:
    with pytest.raises(ValueError, match="sum to total_bits"):
        FhCodecConfig(total_bits=32, block_schedule=(16, 8))
