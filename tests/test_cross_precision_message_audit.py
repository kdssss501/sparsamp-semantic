from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

from scripts.audit_cross_precision_messages import (
    bit_error_count,
    load_experiment_key,
    summarize_rows,
)


def test_bit_error_count_includes_mismatches_and_missing_bits() -> None:
    assert bit_error_count("1010", "1110") == 1
    assert bit_error_count("1010", "10") == 2
    assert bit_error_count("1010", "10101111") == 0


def test_summary_counts_failed_trials_in_message_rate_and_ber() -> None:
    rows = [
        {
            "variant": "adaptive",
            "payload_bit_length": 8,
            "encode_success": True,
            "same_precision_success": True,
            "cross_precision_success": True,
            "bit_errors": 0,
            "token_count": 4,
            "bits_per_token": 2.0,
            "forward_quantization_kl_nats": 0.01,
            "quantization_tv_step_sum": 0.02,
        },
        {
            "variant": "adaptive",
            "payload_bit_length": 8,
            "encode_success": False,
            "same_precision_success": False,
            "cross_precision_success": False,
            "bit_errors": 8,
        },
    ]

    summary = summarize_rows(rows)["adaptive"]

    assert summary["trials"] == 2
    assert summary["cross_precision_message_success_rate"] == 0.5
    assert summary["aggregate_ber"] == 0.5


def test_experiment_key_file_is_generated_once_and_reused(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.delenv("SPARSAMP_SECRET_KEY", raising=False)
    path = tmp_path / "experiment.key"

    first, first_source = load_experiment_key(path)
    second, second_source = load_experiment_key(path)

    assert len(first) == 32
    assert first == second
    assert first_source == "generated_key_file"
    assert second_source == "key_file"
