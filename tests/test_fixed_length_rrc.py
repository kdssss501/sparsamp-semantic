from __future__ import annotations

import pytest

from sparsamp_semantic.core import IncompleteEncodeError
from sparsamp_semantic.fixed_length_rrc import (
    FixedLengthCoverSampler,
    FixedLengthDecodeError,
    FixedLengthRotationRangeCodec,
    FixedLengthRrcConfig,
)
from sparsamp_semantic.providers.mock import MockProvider


KEY = b"0123456789abcdef"
PAYLOAD = "1010101011001100"


def _codec(**overrides: object) -> FixedLengthRotationRangeCodec:
    values: dict[str, object] = {
        "payload_bits": len(PAYLOAD),
        "total_tokens": 64,
        "tag_bits": 32,
    }
    values.update(overrides)
    return FixedLengthRotationRangeCodec(FixedLengthRrcConfig(**values))


def test_fixed_length_rrc_round_trip_hides_embedding_boundary() -> None:
    provider = MockProvider()
    codec = _codec()

    encoded = codec.encode(provider.start("fixed prompt"), PAYLOAD, KEY)
    decoded = codec.decode(provider.start("fixed prompt"), encoded.token_ids, KEY)

    assert len(encoded.token_ids) == codec.config.total_tokens
    assert 0 < encoded.embedded_token_count < codec.config.total_tokens
    assert encoded.padding_token_count == codec.config.total_tokens - encoded.embedded_token_count
    assert encoded.payload_embedded
    assert encoded.embedded_bits == len(PAYLOAD)
    assert decoded.bits == PAYLOAD
    assert decoded.authenticated_prefix_tokens <= encoded.embedded_token_count
    assert decoded.consumed_tokens == codec.config.total_tokens


def test_padding_uses_non_embedding_records_after_verified_prefix() -> None:
    encoded = _codec().encode(MockProvider().start("records"), PAYLOAD, KEY)

    assert len(encoded.records) == len(encoded.token_ids)
    assert all(record.embedded for record in encoded.records[: encoded.embedded_token_count])
    assert all(not record.embedded for record in encoded.records[encoded.embedded_token_count :])
    assert sum(record.block_completed for record in encoded.records) == 1


def test_fixed_length_rrc_is_deterministic_for_same_context_and_key() -> None:
    codec = _codec()
    provider = MockProvider()

    first = codec.encode(provider.start("same"), PAYLOAD, KEY)
    second = codec.encode(provider.start("same"), PAYLOAD, KEY)

    assert first.token_ids == second.token_ids
    assert first.embedded_token_count == second.embedded_token_count


@pytest.mark.parametrize(
    ("prompt", "key"),
    [
        ("wrong prompt", KEY),
        ("fixed prompt", b"fedcba9876543210"),
    ],
)
def test_fixed_length_rrc_rejects_wrong_context_or_key(prompt: str, key: bytes) -> None:
    codec = _codec()
    encoded = codec.encode(MockProvider().start("fixed prompt"), PAYLOAD, KEY)

    with pytest.raises(FixedLengthDecodeError, match="no authenticated"):
        codec.decode(MockProvider().start(prompt), encoded.token_ids, key)


def test_tampering_an_embedded_token_breaks_authentication() -> None:
    codec = _codec()
    encoded = codec.encode(MockProvider().start("tamper"), PAYLOAD, KEY)
    tampered = list(encoded.token_ids)
    tampered_step = min(3, encoded.embedded_token_count - 1)
    tampered[tampered_step] = f"{tampered_step}:3"

    with pytest.raises(FixedLengthDecodeError, match="no authenticated"):
        codec.decode(MockProvider().start("tamper"), tampered, KEY)


def test_tampering_only_padding_preserves_authenticated_payload() -> None:
    codec = _codec()
    encoded = codec.encode(MockProvider().start("padding"), PAYLOAD, KEY)
    tampered = list(encoded.token_ids)
    padding_step = encoded.embedded_token_count
    tampered[padding_step] = f"{padding_step}:3"

    decoded = codec.decode(MockProvider().start("padding"), tampered, KEY)

    assert decoded.bits == PAYLOAD


def test_fixed_length_decode_requires_the_public_token_count() -> None:
    codec = _codec()
    encoded = codec.encode(MockProvider().start("length"), PAYLOAD, KEY)

    with pytest.raises(ValueError, match="exactly 64 tokens"):
        codec.decode(MockProvider().start("length"), encoded.token_ids[:-1], KEY)


def test_decoder_stops_at_authenticated_prefix_before_long_padding_collapses() -> None:
    codec = _codec(total_tokens=256)
    encoded = codec.encode(MockProvider().start("long-padding"), PAYLOAD, KEY)

    decoded = codec.decode(MockProvider().start("long-padding"), encoded.token_ids, KEY)

    assert decoded.bits == PAYLOAD
    assert decoded.authenticated_prefix_tokens <= encoded.embedded_token_count
    assert encoded.padding_token_count > 200


def test_insufficient_budget_raises_by_default() -> None:
    codec = _codec(total_tokens=1)

    with pytest.raises(IncompleteEncodeError) as captured:
        codec.encode(MockProvider().start("short"), PAYLOAD, KEY)

    assert len(captured.value.token_ids) == 1


def test_cover_failure_mode_returns_fixed_length_without_claiming_success() -> None:
    codec = _codec(total_tokens=1, failure_mode="cover")

    encoded = codec.encode(MockProvider().start("short"), PAYLOAD, KEY)

    assert len(encoded.token_ids) == 1
    assert not encoded.payload_embedded
    assert encoded.embedded_bits == 0
    with pytest.raises(FixedLengthDecodeError):
        codec.decode(MockProvider().start("short"), encoded.token_ids, KEY)


def test_generate_cover_uses_exact_public_length_and_no_embedded_records() -> None:
    codec = _codec(total_tokens=12)

    cover = codec.generate_cover(MockProvider().start("cover"), KEY)

    assert len(cover.token_ids) == 12
    assert cover.embedded_token_count == 0
    assert cover.padding_token_count == 12
    assert not cover.payload_embedded
    assert all(not record.embedded for record in cover.records)


def test_cover_sampler_uses_payload_seed_only_to_vary_cover_randomness() -> None:
    config = FixedLengthRrcConfig(payload_bits=16, total_tokens=24, tag_bits=32)
    sampler = FixedLengthCoverSampler(config)

    first = sampler.encode(MockProvider().start("cover-sampler"), PAYLOAD, KEY)
    repeated = sampler.encode(MockProvider().start("cover-sampler"), PAYLOAD, KEY)
    changed = sampler.encode(MockProvider().start("cover-sampler"), PAYLOAD[::-1], KEY)

    assert first.token_ids == repeated.token_ids
    assert first.token_ids != changed.token_ids
    assert not first.payload_embedded
    assert all(record.forward_quantization_kl_nats >= 0 for record in first.records)


@pytest.mark.parametrize(
    "config",
    [
        {"payload_bits": 0, "total_tokens": 10, "tag_bits": 32},
        {"payload_bits": 8, "total_tokens": 0, "tag_bits": 32},
        {"payload_bits": 8, "total_tokens": 10, "tag_bits": 31},
        {"payload_bits": 8, "total_tokens": 10, "tag_bits": 257},
        {
            "payload_bits": 8,
            "total_tokens": 10,
            "tag_bits": 32,
            "failure_mode": "invalid",
        },
    ],
)
def test_fixed_length_config_rejects_invalid_values(config: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        FixedLengthRrcConfig(**config)
