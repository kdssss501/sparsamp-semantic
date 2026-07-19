from __future__ import annotations

from sparsamp_semantic.microframe import MicroframeCodec, MicroframeConfig
from sparsamp_semantic.providers.mock import MockProvider


KEY = b"0123456789abcdef0123456789abcdef"


def test_authenticated_microframes_round_trip_and_reset_state() -> None:
    codec = MicroframeCodec(
        MicroframeConfig(window_tokens=12, symbol_bytes=1, auth_tag_bits=8)
    )
    provider = MockProvider()
    encoded = codec.encode(provider.start("r026 round trip"), b"AB", KEY)

    decoded = codec.decode(provider.start("r026 round trip"), encoded.token_ids, KEY)

    assert decoded.success
    assert decoded.payload_bytes == b"AB"
    assert len(decoded.records) == 2
    assert all(record.completed for record in decoded.records)
    assert all(record.authenticated is True for record in decoded.records)


def test_window_corruption_is_local_and_authentication_marks_erasure() -> None:
    codec = MicroframeCodec(
        MicroframeConfig(window_tokens=12, symbol_bytes=1, auth_tag_bits=8)
    )
    provider = MockProvider()
    encoded = codec.encode(provider.start("r026 corruption"), b"AB", KEY)
    corrupted = list(encoded.token_ids)
    corrupted[0] = "0:3" if corrupted[0] != "0:3" else "0:2"

    decoded = codec.decode(provider.start("r026 corruption"), corrupted, KEY)

    assert not decoded.success
    assert decoded.erasure_count >= 1
    assert decoded.records[0].erasure_reason in {"authentication_failed", "ArithmeticError"}
    # The decoder still advances through and audits the next independent window.
    assert len(decoded.records) == 2
    assert decoded.records[1].window_index == 1


def test_short_window_is_reported_as_erasure() -> None:
    codec = MicroframeCodec(
        MicroframeConfig(window_tokens=12, symbol_bytes=1, auth_tag_bits=8)
    )
    provider = MockProvider()
    encoded = codec.encode(provider.start("r026 short"), b"A", KEY)

    decoded = codec.decode(
        provider.start("r026 short"), encoded.token_ids[: encoded.records[0].token_end - 1], KEY
    )

    assert not decoded.success
    assert decoded.records[0].erasure_reason == "short_window"


def test_block_size_includes_authentication_bits() -> None:
    config = MicroframeConfig(symbol_bytes=2, auth_tag_bits=12)
    assert config.block_size == 28


def test_reed_solomon_recovers_one_authenticated_window_erasure() -> None:
    codec = MicroframeCodec(
        MicroframeConfig(window_tokens=12, symbol_bytes=1, auth_tag_bits=8, parity_bytes=2)
    )
    provider = MockProvider()
    encoded = codec.encode(provider.start("r026 rs"), b"AB", KEY)
    corrupted = list(encoded.token_ids)
    corrupted[0] = "0:3" if corrupted[0] != "0:3" else "0:2"

    decoded = codec.decode(provider.start("r026 rs"), corrupted, KEY)

    assert decoded.success
    assert decoded.payload_bytes == b"AB"
    assert decoded.erasure_count >= 1
