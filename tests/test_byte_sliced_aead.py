from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts.audit_byte_sliced_aead import (
    KEY,
    authenticated_message,
    bit_errors,
    build_report,
    experiment_config,
    load_checkpoint_rows,
    message_frame,
    raw_symbol_errors,
    trial_key,
    variant_name,
    write_report,
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


def test_checkpoint_resume_requires_exact_experiment_config(tmp_path) -> None:
    args = SimpleNamespace(
        run_label="R031",
        model="models/gpt2",
        device="cuda",
        reference_dtype="float32",
        replay_dtype="float16",
        top_p=0.95,
        window_tokens=8,
    )
    variants = [(16, 0.0625)]
    row = {
        "prompt_index": 0,
        "message_index": 0,
        "parity_bytes": 16,
        "logit_quantum": 0.0625,
    }
    output = tmp_path / "checkpoint.json"
    write_report(output, build_report(args, variants, [row], "reference_partial"))

    signature = experiment_config(args, variants)
    assert load_checkpoint_rows(output, signature) == [row]
    assert trial_key(row) == (0, 0, 16, 0.0625)
    with pytest.raises(ValueError, match="does not match"):
        load_checkpoint_rows(output, {**signature, "top_p": 0.8})


def test_checkpoint_rejects_duplicate_trials(tmp_path) -> None:
    args = SimpleNamespace(
        run_label="R031",
        model="models/gpt2",
        device="cuda",
        reference_dtype="float32",
        replay_dtype="float16",
        top_p=0.95,
        window_tokens=8,
    )
    variants = [(16, 0.0625)]
    row = {
        "prompt_index": 0,
        "message_index": 0,
        "parity_bytes": 16,
        "logit_quantum": 0.0625,
    }
    output = tmp_path / "duplicates.json"
    write_report(output, build_report(args, variants, [row, dict(row)], "reference_partial"))

    with pytest.raises(ValueError, match="duplicate"):
        load_checkpoint_rows(output, experiment_config(args, variants))
