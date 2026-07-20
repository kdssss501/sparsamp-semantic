from __future__ import annotations

from scripts.audit_byte_sliced_aead import (
    KEY,
    authenticated_message,
    bit_errors,
    message_frame,
    raw_symbol_errors,
    variant_name,
)
from sparsamp_semantic.byte_sliced import ByteSlicedCodec, ByteSlicedConfig
from sparsamp_semantic.providers.mock import MockProvider


def test_message_frame_is_deterministic_and_context_bound() -> None:
    first = message_frame("Trust tests.", 0, 0)
    assert first == message_frame("Trust tests.", 0, 0)
    assert first != message_frame("Trust tests.", 1, 0)
    assert first != message_frame("Protect meaning.", 0, 1)


def test_authenticated_message_requires_valid_aead_frame() -> None:
    frame = message_frame("Trust tests.", 0, 0)
    assert authenticated_message(frame, "Trust tests.") == (True, None)
    corrupted = bytes([frame[0] ^ 1]) + frame[1:]
    ok, error = authenticated_message(corrupted, "Trust tests.")
    assert not ok
    assert error and "magic" in error


def test_aead_helpers_report_missing_and_extra_frame_bits() -> None:
    frame = message_frame("Trust tests.", 0, 0)
    assert bit_errors(frame, frame) == 0
    assert bit_errors(frame, None) == len(frame) * 8
    assert raw_symbol_errors(b"\x01\x02", []) == 2


def test_variant_name_is_stable() -> None:
    assert variant_name(2, None) == "parity=2,q=none"
    assert variant_name(2, 0.0625) == "parity=2,q=0.0625"


def test_mock_byte_sliced_frame_authenticates_end_to_end() -> None:
    message = "Trust tests."
    frame = message_frame(message, 0, 0)
    codec = ByteSlicedCodec(ByteSlicedConfig(window_tokens=8, parity_bytes=2))
    provider = MockProvider()

    encoded = codec.encode(provider.start("R030 mock"), frame, KEY)
    decoded = codec.decode(provider.start("R030 mock"), encoded.token_ids, KEY)

    assert decoded.payload_bytes == frame
    assert authenticated_message(decoded.payload_bytes, message) == (True, None)
