from __future__ import annotations

from scripts.audit_byte_sliced_messages import bit_errors, payload_for_seed, summarize


def test_seeded_payload_is_deterministic_and_domain_separated() -> None:
    assert payload_for_seed(0, 4) == payload_for_seed(0, 4)
    assert payload_for_seed(0, 4) != payload_for_seed(1, 4)


def test_byte_bit_errors_counts_mismatch_and_missing_bytes() -> None:
    assert bit_errors(b"\x00\xff", b"\x01\xff") == 1
    assert bit_errors(b"\x00\xff", b"\x00") == 8
    assert bit_errors(b"\x00\xff", None) == 16


def test_summary_keeps_failed_trials_in_rate_and_ber() -> None:
    rows = [
        {
            "parity_bytes": 2,
            "payload_bits": 16,
            "encode_success": True,
            "same_precision_success": True,
            "cross_precision_success": True,
            "bit_errors": 0,
            "payload_bits_per_token": 0.5,
            "erasure_count": 0,
            "raw_symbol_errors": 0,
        },
        {
            "parity_bytes": 2,
            "payload_bits": 16,
            "encode_success": True,
            "same_precision_success": True,
            "cross_precision_success": False,
            "bit_errors": 16,
            "payload_bits_per_token": 0.5,
            "erasure_count": 2,
            "raw_symbol_errors": 3,
        },
    ]

    result = summarize(rows)["2"]

    assert result["cross_precision_rate"] == 0.5
    assert result["aggregate_ber"] == 0.5
    assert result["mean_erasures"] == 1
