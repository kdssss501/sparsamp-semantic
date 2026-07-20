from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts.audit_byte_sliced_messages import (
    KEY,
    acceptance_summary,
    archive_existing_report,
    bit_errors,
    build_report,
    config_signature,
    experiment_config,
    load_checkpoint_rows,
    payload_for_seed,
    summarize,
    trial_key,
    write_report,
)
from sparsamp_semantic.byte_sliced import ByteSlicedCodec, ByteSlicedConfig
from sparsamp_semantic.providers.mock import MockProvider


def audit_args(**overrides: object) -> SimpleNamespace:
    values = {
        "run_label": "R036-test",
        "model": "models/gpt2",
        "device": "cuda",
        "reference_dtype": "float32",
        "replay_dtype": "float16",
        "top_p": 1.0,
        "top_k": 2,
        "logit_quantum": 0.5,
        "bin_mass_bits": 16,
        "temperature": 1.2,
        "payload_bytes": 2,
        "payload_seeds": [0, 1],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def audit_row(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "prompt_index": 0,
        "payload_seed": 0,
        "window_tokens": 16,
        "parity_bytes": 2,
        "variant": "window=16,parity=2",
        "payload_bits": 16,
        "encode_success": True,
        "same_precision_success": True,
        "cross_precision_success": True,
        "same_precision_bit_errors": 0,
        "cross_precision_bit_errors": 0,
        "token_count": 64,
        "codeword_bits_per_token": 0.5,
        "same_precision_erasure_count": 0,
        "cross_precision_erasure_count": 0,
        "same_precision_raw_symbol_errors": 0,
        "cross_precision_raw_symbol_errors": 0,
        "encode_seconds": 1.0,
        "same_precision_decode_seconds": 0.5,
        "cross_precision_decode_seconds": 0.25,
    }
    values.update(overrides)
    return values


def test_seeded_payload_is_deterministic_and_domain_separated() -> None:
    assert payload_for_seed(0, 4) == payload_for_seed(0, 4)
    assert payload_for_seed(0, 4) != payload_for_seed(1, 4)


def test_byte_bit_errors_counts_mismatch_and_missing_bytes() -> None:
    assert bit_errors(b"\x00\xff", b"\x01\xff") == 1
    assert bit_errors(b"\x00\xff", b"\x00") == 8
    assert bit_errors(b"\x00\xff", None) == 16


def test_mock_raw_byte_roundtrip_with_r036_window() -> None:
    payload = payload_for_seed(0, 2)
    codec = ByteSlicedCodec(ByteSlicedConfig(window_tokens=16, parity_bytes=2))
    provider = MockProvider()

    encoded = codec.encode(provider.start("R036 mock"), payload, KEY)
    decoded = codec.decode(provider.start("R036 mock"), encoded.token_ids, KEY)

    assert decoded.payload_bytes == payload
    assert decoded.erasure_count == 0


def test_summary_keeps_failed_trials_in_rate_ber_and_effective_capacity() -> None:
    rows = [
        audit_row(),
        audit_row(
            payload_seed=1,
            cross_precision_success=False,
            cross_precision_bit_errors=16,
            cross_precision_erasure_count=2,
            cross_precision_raw_symbol_errors=3,
        ),
    ]

    result = summarize(rows)["window=16,parity=2"]

    assert result["cross_precision_rate"] == 0.5
    assert result["cross_precision_aggregate_ber"] == 0.5
    assert result["aggregate_net_payload_bits_per_token"] == 0.25
    assert result["cross_precision_effective_bits_per_token"] == 0.125
    assert result["mean_cross_precision_erasures"] == 1


def test_checkpoint_resume_requires_exact_signed_experiment_config(tmp_path) -> None:
    args = audit_args()
    variants = [(16, 0), (16, 2), (32, 0), (32, 2)]
    row = audit_row()
    output = tmp_path / "checkpoint.json"
    write_report(output, build_report(args, variants, [row], "reference_partial"))

    signature = experiment_config(args, variants)
    assert load_checkpoint_rows(output, signature) == [row]
    assert trial_key(row) == (0, 0, 16, 2)
    assert config_signature(signature) == build_report(
        args, variants, [row], "reference_partial"
    )["experiment_signature"]
    with pytest.raises(ValueError, match="does not match"):
        load_checkpoint_rows(output, {**signature, "temperature": 1.0})


def test_checkpoint_rejects_duplicate_trials(tmp_path) -> None:
    args = audit_args()
    variants = [(16, 2)]
    row = audit_row()
    output = tmp_path / "duplicates.json"
    write_report(output, build_report(args, variants, [row, dict(row)], "reference_partial"))

    with pytest.raises(ValueError, match="duplicate"):
        load_checkpoint_rows(output, experiment_config(args, variants))


def test_checkpoint_rejects_tampered_signature(tmp_path) -> None:
    args = audit_args()
    variants = [(16, 2)]
    output = tmp_path / "tampered.json"
    report = build_report(args, variants, [audit_row()], "reference_partial")
    report["experiment_signature"] = "0" * 64
    write_report(output, report)

    with pytest.raises(ValueError, match="signature"):
        load_checkpoint_rows(output, experiment_config(args, variants))


def test_checkpoint_rejects_trial_outside_configured_matrix(tmp_path) -> None:
    args = audit_args()
    variants = [(16, 2)]
    output = tmp_path / "outside.json"
    row = audit_row(window_tokens=32, variant="window=32,parity=2")
    write_report(output, build_report(args, variants, [row], "reference_partial"))

    with pytest.raises(ValueError, match="outside"):
        load_checkpoint_rows(output, experiment_config(args, variants))


def test_fresh_archive_preserves_existing_report(tmp_path) -> None:
    output = tmp_path / "report.json"
    output.write_text("previous progress", encoding="utf-8")

    archived = archive_existing_report(output)

    assert archived is not None
    assert archived.read_text(encoding="utf-8") == "previous progress"
    assert not output.exists()


def test_acceptance_selects_success_then_capacity_then_runtime() -> None:
    high_capacity = summarize(
        [audit_row(payload_seed=index, token_count=32) for index in range(6)]
    )["window=16,parity=2"]
    low_capacity = summarize(
        [
            audit_row(
                payload_seed=index,
                window_tokens=32,
                variant="window=32,parity=2",
                token_count=64,
            )
            for index in range(6)
        ]
    )["window=32,parity=2"]

    result = acceptance_summary(
        {
            "window=16,parity=2": high_capacity,
            "window=32,parity=2": low_capacity,
        },
        expected_trials=6,
    )

    assert result["overall_go"]
    assert result["required_cross_precision_successes"] == 5
    assert result["selected_variant"] == "window=16,parity=2"
