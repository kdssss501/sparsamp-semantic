from __future__ import annotations

from scripts.run_completion_pilot import (
    _build_codec,
    _iter_specs,
    _payload_for_seed,
    _sequence_difference,
    _trajectory_key,
)
from sparsamp_semantic.fh import FhSparSampCodec


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


def test_fh_trajectory_key_keeps_token_budget() -> None:
    variant = {"name": "fh", "kind": "fh", "block_sizes": [8, 16, 32]}
    short = {"prompt": "p", "token_budget": 128, "codec_variant": variant}
    long = {**short, "token_budget": 192}

    assert _trajectory_key(short) != _trajectory_key(long)


def test_sequence_difference_reports_first_mismatch() -> None:
    assert _sequence_difference((1, 2), (1, 2)) is None
    assert _sequence_difference((1, 2, 3), (1, 9))["first_index"] == 1


def test_variant_specs_and_fh_codec_building() -> None:
    settings = {
        "experiment_id": "fh-test",
        "prompts": ["prompt"],
        "payload_seeds": [0],
        "token_budgets": [128],
        "variants": [
            {
                "name": "fh",
                "kind": "fh",
                "block_sizes": [8, 16, 32],
            }
        ],
    }

    spec = _iter_specs(settings)[0]
    codec = _build_codec(spec, settings, total_bits=128)

    assert spec["variant"] == "fh"
    assert isinstance(codec, FhSparSampCodec)
    assert codec.config.max_tokens == 128
