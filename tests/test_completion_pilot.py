from __future__ import annotations

from scripts.run_completion_pilot import (
    _payload_for_seed,
    _sequence_difference,
    _trajectory_key,
)


def test_raw_payload_is_deterministic_and_seeded() -> None:
    settings = {
        "experiment_id": "test",
        "payload": {"mode": "raw", "bit_length": 13},
    }
    first, mode = _payload_for_seed(settings, b"0123456789abcdef", 1)
    repeated, _ = _payload_for_seed(settings, b"0123456789abcdef", 1)
    changed, _ = _payload_for_seed(settings, b"0123456789abcdef", 2)

    assert mode == "raw"
    assert len(first) == 13
    assert first == repeated
    assert first != changed


def test_trajectory_key_ignores_only_token_budget() -> None:
    base = {"prompt": "p", "block_size": 8, "token_budget": 128}
    larger_budget = {**base, "token_budget": 512}
    different_block = {**base, "block_size": 16}

    assert _trajectory_key(base) == _trajectory_key(larger_budget)
    assert _trajectory_key(base) != _trajectory_key(different_block)


def test_sequence_difference_reports_first_mismatch() -> None:
    assert _sequence_difference((1, 2), (1, 2)) is None
    assert _sequence_difference((1, 2, 3), (1, 9))["first_index"] == 1
