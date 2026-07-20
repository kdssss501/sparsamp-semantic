from __future__ import annotations

from reedsolo import RSCodec

from sparsamp_semantic.list_recovery import (
    ListRecoveryConfig,
    candidate_cost_map,
    decode_rs_lists,
    score_codeword,
)


def test_rs_list_recovery_selects_unique_payload_without_expected_oracle() -> None:
    payload = b"A"
    codeword = bytes(RSCodec(1).encode(payload))
    windows = [([symbol], [0]) for symbol in codeword]
    result = decode_rs_lists(
        windows,
        ListRecoveryConfig(payload_bytes=1, parity_bytes=1, enumeration_limit=256),
    )
    assert result.unique
    assert result.payload == payload
    assert result.best_score == (0, 0)
    assert result.enumerated_payloads == 256


def test_empty_lists_produce_an_explicit_full_codebook_tie() -> None:
    result = decode_rs_lists(
        [([], []), ([], [])],
        ListRecoveryConfig(payload_bytes=1, parity_bytes=1, enumeration_limit=256),
    )
    assert not result.unique
    assert result.payload is None
    assert result.best_tie_count == 256
    assert result.best_score == (2, 0)


def test_cost_threshold_turns_high_cost_symbol_into_a_miss() -> None:
    costs = [candidate_cost_map([65], [2]), candidate_cost_map([1], [0])]
    assert score_codeword(b"A\x01", costs, 1) == (1, 0)
    assert score_codeword(b"A\x01", costs, 2) == (0, 2)


def test_list_recovery_rejects_unbounded_payload_codebook() -> None:
    try:
        ListRecoveryConfig(payload_bytes=2, parity_bytes=1, enumeration_limit=255)
    except ValueError as error:
        assert "enumeration limit" in str(error)
    else:
        raise AssertionError("expected oversized codebook to fail")
