from __future__ import annotations

import pytest

from sparsamp_semantic.payload import PayloadCodec, recover_repeated_bits, repeat_bits


@pytest.mark.parametrize("repetitions", [1, 3, 5])
def test_payload_round_trip(repetitions: int) -> None:
    codec = PayloadCodec(repetitions=repetitions)
    key = b"0123456789abcdef0123456789abcdef"
    bits = codec.seal("可读文本中的隐藏消息", key)

    assert codec.open(bits + "0" * 64, key) == "可读文本中的隐藏消息"


def test_payload_rejects_wrong_key() -> None:
    codec = PayloadCodec()
    bits = codec.seal("secret", b"0123456789abcdef0123456789abcdef")
    with pytest.raises(Exception):
        codec.open(bits, b"fedcba9876543210fedcba9876543210")


def test_repetition_code_corrects_one_error() -> None:
    encoded = list(repeat_bits("101", 3))
    encoded[1] = "0"
    assert recover_repeated_bits("".join(encoded), 3) == "101"


def test_explicit_nonce_makes_payload_reproducible() -> None:
    codec = PayloadCodec()
    key = b"0123456789abcdef"
    nonce = bytes(range(12))
    assert codec.seal("message", key, nonce=nonce) == codec.seal("message", key, nonce=nonce)


def test_nonce_must_be_12_bytes() -> None:
    with pytest.raises(ValueError, match="exactly 12 bytes"):
        PayloadCodec().seal("message", b"0123456789abcdef", nonce=b"short")
