"""Compact, versioned serialization for sparse replay manifests."""

from __future__ import annotations

import json
from typing import Any

from .replay_certificate import ReplayCorrection, ReplayManifest


MAGIC = b"SPRC\x01"
PACKAGE_MAGIC = b"SPRP\x01"
TRIAL_MAGIC = b"TR\x01"


def encode_uvarint(value: int) -> bytes:
    if value < 0:
        raise ValueError("unsigned varint cannot encode a negative value")
    output = bytearray()
    while value >= 0x80:
        output.append((value & 0x7F) | 0x80)
        value >>= 7
    output.append(value)
    return bytes(output)


def decode_uvarint(data: bytes, offset: int = 0) -> tuple[int, int]:
    value = 0
    shift = 0
    while offset < len(data):
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, offset
        shift += 7
        if shift > 63:
            raise ValueError("unsigned varint exceeds 64 bits")
    raise ValueError("truncated unsigned varint")


def encode_manifest(manifest: ReplayManifest) -> bytes:
    output = bytearray(MAGIC)
    output.extend(encode_uvarint(manifest.token_count))
    output.extend(encode_uvarint(len(manifest.corrections)))
    previous_step = -1
    for correction in manifest.corrections:
        gap = correction.step - previous_step - 1
        output.extend(encode_uvarint(gap))
        output.extend(encode_uvarint(correction.token_id))
        previous_step = correction.step
    return bytes(output)


def decode_manifest(data: bytes) -> ReplayManifest:
    if not data.startswith(MAGIC):
        raise ValueError("invalid sparse replay certificate magic")
    offset = len(MAGIC)
    token_count, offset = decode_uvarint(data, offset)
    correction_count, offset = decode_uvarint(data, offset)
    corrections = []
    previous_step = -1
    for _ in range(correction_count):
        gap, offset = decode_uvarint(data, offset)
        token_id, offset = decode_uvarint(data, offset)
        step = previous_step + gap + 1
        corrections.append(ReplayCorrection(step=step, token_id=token_id))
        previous_step = step
    if offset != len(data):
        raise ValueError("sparse replay certificate has trailing bytes")
    return ReplayManifest(token_count=token_count, corrections=tuple(corrections))


def canonical_json_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _signature_bytes(value: str, name: str) -> bytes:
    try:
        encoded = bytes.fromhex(value)
    except ValueError as error:
        raise ValueError(f"{name} must be hexadecimal") from error
    if len(encoded) != 32:
        raise ValueError(f"{name} must encode a SHA-256 digest")
    return encoded


def encode_referenced_package_header(
    *, bundle_signature: str, model_signature: str, environment_signature: str
) -> bytes:
    """Identify externally shared contracts without repeating their JSON content."""

    return b"".join(
        (
            PACKAGE_MAGIC,
            _signature_bytes(bundle_signature, "bundle signature"),
            _signature_bytes(model_signature, "model signature"),
            _signature_bytes(environment_signature, "environment signature"),
        )
    )


def encode_trial_record(
    *,
    prompt_index: int,
    seed: int,
    policy: str,
    token_count: int,
    reference_token_sha256: str,
    payload: bytes,
) -> bytes:
    if prompt_index < 0 or seed < 0 or token_count < 1:
        raise ValueError("trial indices and token count are out of range")
    policy_code = {"seeded": 0, "greedy": 1}.get(policy)
    if policy_code is None:
        raise ValueError("unsupported replay policy")
    output = bytearray(TRIAL_MAGIC)
    output.extend(encode_uvarint(prompt_index))
    output.extend(encode_uvarint(seed))
    output.append(policy_code)
    output.extend(encode_uvarint(token_count))
    output.extend(_signature_bytes(reference_token_sha256, "reference token signature"))
    output.extend(encode_uvarint(len(payload)))
    output.extend(payload)
    return bytes(output)
