from __future__ import annotations

from sparsamp_semantic.core import CodecConfig, SparSampCodec
from sparsamp_semantic.finishing import FinishingConfig, finish_session
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


def test_authenticated_payload_ignores_native_finishing_blocks() -> None:
    key = b"0123456789abcdef0123456789abcdef"
    prompt = "Finish the visible sentence after embedding."
    payload = PayloadCodec(repetitions=1)
    codec = SparSampCodec(CodecConfig(block_size=16, max_tokens=10000))
    provider = MockProvider()
    session = provider.start(prompt)

    payload_bits = payload.seal("A-17", key, nonce=bytes(range(12)))
    encoded = codec.encode(session, payload_bits, key)
    finished = finish_session(session, FinishingConfig(mode="fixed", max_tokens=12))
    decoded = codec.decode(provider.start(prompt), list(finished.token_ids), key)

    assert finished.tail_token_count == 12
    assert payload.open(decoded.bits, key) == "A-17"
    assert len(finished.token_ids) > len(encoded.token_ids)
