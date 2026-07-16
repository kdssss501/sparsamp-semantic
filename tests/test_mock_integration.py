from __future__ import annotations

from sparsamp_semantic.core import CodecConfig, SparSampCodec
from sparsamp_semantic.payload import PayloadCodec
from sparsamp_semantic.providers.mock import MockProvider


def test_encrypted_text_round_trip() -> None:
    key = b"0123456789abcdef0123456789abcdef"
    prompt = "Write a coherent research summary."
    payload = PayloadCodec(repetitions=1)
    codec = SparSampCodec(CodecConfig(block_size=16, max_tokens=10000))
    provider = MockProvider()

    payload_bits = payload.seal("实验编号 A-17", key)
    encoded = codec.encode(provider.start(prompt), payload_bits, key)
    decoded = codec.decode(provider.start(prompt), list(encoded.token_ids), key)

    assert payload.open(decoded.bits, key) == "实验编号 A-17"
    assert "method" in encoded.text or "system" in encoded.text or "study" in encoded.text

