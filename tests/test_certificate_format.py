import pytest

from sparsamp_semantic.certificate_format import (
    decode_manifest,
    decode_uvarint,
    encode_manifest,
    encode_referenced_package_header,
    encode_trial_record,
    encode_uvarint,
)
from sparsamp_semantic.replay_certificate import ReplayCorrection, ReplayManifest


@pytest.mark.parametrize("value", [0, 1, 127, 128, 255, 16384, 2**32])
def test_unsigned_varint_round_trip(value: int) -> None:
    encoded = encode_uvarint(value)
    assert decode_uvarint(encoded) == (value, len(encoded))


def test_manifest_binary_round_trip() -> None:
    manifest = ReplayManifest(
        token_count=96,
        corrections=(ReplayCorrection(0, 151935), ReplayCorrection(31, 42)),
    )
    assert decode_manifest(encode_manifest(manifest)) == manifest


def test_manifest_binary_rejects_truncation_and_trailing_bytes() -> None:
    encoded = encode_manifest(
        ReplayManifest(token_count=8, corrections=(ReplayCorrection(2, 7),))
    )
    with pytest.raises(ValueError, match="truncated"):
        decode_manifest(encoded[:-1])
    with pytest.raises(ValueError, match="trailing"):
        decode_manifest(encoded + b"x")


def test_referenced_package_uses_fixed_signatures_and_compact_trial_record() -> None:
    signature = "ab" * 32
    header = encode_referenced_package_header(
        bundle_signature=signature,
        model_signature=signature,
        environment_signature=signature,
    )
    record = encode_trial_record(
        prompt_index=1,
        seed=2,
        policy="seeded",
        token_count=64,
        reference_token_sha256=signature,
        payload=b"payload",
    )
    assert len(header) == 101
    assert record.endswith(b"payload")
    assert len(record) < 64
