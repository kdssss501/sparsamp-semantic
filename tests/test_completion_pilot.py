from __future__ import annotations

from scripts.run_completion_pilot import (
    _build_codec,
    _finishing_config,
    _iter_specs,
    _payload_for_seed,
    _record_metrics,
    _sequence_difference,
    _trajectory_key,
)
from sparsamp_semantic.core import StepRecord
from sparsamp_semantic.fh import FhSparSampCodec
from sparsamp_semantic.fixed_length_rrc import (
    FixedLengthCoverSampler,
    FixedLengthRotationRangeCodec,
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


def test_record_metrics_separates_embedded_and_visible_entropy() -> None:
    records = (
        StepRecord(
            step=0,
            token_id=1,
            embedded=True,
            block_completed=False,
            entropy_bits=1.0,
            source_mass=1.0,
            truncation_kl_nats=0.0,
            candidate_count=2,
            latency_ms=1.0,
        ),
        StepRecord(
            step=1,
            token_id=2,
            embedded=False,
            block_completed=False,
            entropy_bits=3.0,
            source_mass=1.0,
            truncation_kl_nats=0.0,
            candidate_count=4,
            latency_ms=1.0,
        ),
    )

    metrics = _record_metrics(records)

    assert metrics["mean_entropy_bits"] == 1.0
    assert metrics["mean_visible_entropy_bits"] == 2.0


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


def test_fixed_rrc_trajectory_key_keeps_public_length() -> None:
    variant = {"name": "fixed-rrc", "kind": "fixed_rrc", "tag_bits": 64}
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


def test_fixed_length_rrc_codec_building() -> None:
    settings = {
        "experiment_id": "fixed-rrc-test",
        "prompts": ["prompt"],
        "payload_seeds": [0],
        "token_budgets": [192],
        "variants": [
            {
                "name": "fixed-rrc-64",
                "kind": "fixed_rrc",
                "tag_bits": 64,
                "failure_mode": "cover",
            }
        ],
    }

    spec = _iter_specs(settings)[0]
    codec = _build_codec(spec, settings, total_bits=128)

    assert isinstance(codec, FixedLengthRotationRangeCodec)
    assert codec.config.payload_bits == 128
    assert codec.config.total_tokens == 192
    assert codec.config.tag_bits == 64
    assert codec.config.failure_mode == "cover"


def test_fixed_length_cover_codec_building() -> None:
    settings = {
        "experiment_id": "fixed-cover-test",
        "prompts": ["prompt"],
        "payload_seeds": [0],
        "token_budgets": [224],
        "variants": [
            {
                "name": "fixed-cover",
                "kind": "fixed_rrc_cover",
                "tag_bits": 64,
            }
        ],
    }

    spec = _iter_specs(settings)[0]
    codec = _build_codec(spec, settings, total_bits=128)

    assert isinstance(codec, FixedLengthCoverSampler)
    assert codec.config.total_tokens == 224


def test_variant_can_enable_punctuation_finishing() -> None:
    spec = {
        "codec_variant": {
            "name": "fixed-16-tail",
            "kind": "fixed",
            "block_size": 16,
            "finish_mode": "punctuation",
            "finish_max_tokens": 24,
        }
    }

    config = _finishing_config(spec, {})

    assert config.mode == "punctuation"
    assert config.max_tokens == 24
