from __future__ import annotations

from sparsamp_semantic.byte_sliced import ByteSlicedCodec, ByteSlicedConfig
from sparsamp_semantic.payload import PayloadCodec, bits_to_bytes, bytes_to_bits
from sparsamp_semantic.providers.mock import MockProvider


KEY = b"0123456789abcdef0123456789abcdef"


def test_byte_sliced_rs_round_trip() -> None:
    codec = ByteSlicedCodec(ByteSlicedConfig(window_tokens=8, parity_bytes=2))
    provider = MockProvider()

    encoded = codec.encode(provider.start("r029 bytes"), b"AB", KEY)
    decoded = codec.decode(provider.start("r029 bytes"), encoded.token_ids, KEY)

    assert decoded.success
    assert decoded.payload_bytes == b"AB"
    assert len(encoded.records) == 4
    assert encoded.payload_bits_per_token == 0.5


def test_byte_sliced_payload_codec_authenticates_recovered_message() -> None:
    payload = PayloadCodec().seal("可读的隐藏消息", KEY, nonce=bytes(range(12)))
    payload_bytes = bits_to_bytes(payload)
    codec = ByteSlicedCodec(ByteSlicedConfig(window_tokens=8, parity_bytes=2))
    provider = MockProvider()

    encoded = codec.encode(provider.start("r029 authenticated"), payload_bytes, KEY)
    decoded = codec.decode(provider.start("r029 authenticated"), encoded.token_ids, KEY)

    assert decoded.success
    assert decoded.payload_bytes is not None
    assert PayloadCodec().open(bytes_to_bits(decoded.payload_bytes), KEY) == "可读的隐藏消息"


def test_byte_sliced_guard_aborts_with_fixed_window_count() -> None:
    codec = ByteSlicedCodec(
        ByteSlicedConfig(window_tokens=8, parity_bytes=2, cdf_uncertainty_bound=1e-2)
    )
    provider = MockProvider()

    encoded = codec.encode(provider.start("r029 guard"), b"AB", KEY)

    assert len(encoded.token_ids) == 32
    assert all(record.guard_aborted for record in encoded.records)
