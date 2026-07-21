import pytest

from scripts.analyze_official_reproduction import (
    aggregate_metric,
    analyze_report,
    bootstrap_metric,
    relative_error,
)


def row(context_index: int, encoded_bits: int = 300, entropy_bits: float = 400.0) -> dict:
    return {
        "block_size": 64,
        "top_p": 1.0,
        "context_index": context_index,
        "status": "completed",
        "token_ambiguity": False,
        "decode_success": True,
        "token_count": 50,
        "encoded_bits": encoded_bits,
        "entropy_bits": entropy_bits,
        "generation_seconds": 2.0,
        "sampling_seconds": 0.1,
        "model_seconds": 1.9,
        "decode_seconds": 1.0,
    }


def test_aggregate_metrics_use_ratio_of_sums() -> None:
    rows = [row(0, 100, 200.0), row(1, 300, 400.0)]
    assert aggregate_metric(rows, "embedding_rate") == 4.0
    assert aggregate_metric(rows, "utilization") == pytest.approx(2 / 3)


def test_bootstrap_is_deterministic_and_bounded() -> None:
    rows = [row(0, 100), row(1, 300), row(2, 500)]
    first = bootstrap_metric(rows, "embedding_rate", 1000, 7)
    second = bootstrap_metric(rows, "embedding_rate", 1000, 7)
    assert first == second
    assert first[0] <= aggregate_metric(rows, "embedding_rate") <= first[1]


def test_analysis_rejects_partial_report() -> None:
    with pytest.raises(ValueError, match="incomplete"):
        analyze_report(
            {"phase": "partial", "progress": {"expected_trials": 2}, "rows": [row(0)]},
            repetitions=10,
            seed=1,
            capacity_tolerance=0.05,
        )


def test_relative_error() -> None:
    assert relative_error(0.95, 1.0) == pytest.approx(0.05)
