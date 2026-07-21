from scripts.generate_manuscript_figures import cluster_interval, percentile, summarize_variant


def test_percentile_interpolates() -> None:
    assert percentile([0.0, 1.0], 0.25) == 0.25


def test_cluster_interval_keeps_prompt_rows_together() -> None:
    rows = [
        {"prompt_index": 0, "value": 0.0},
        {"prompt_index": 0, "value": 0.0},
        {"prompt_index": 1, "value": 1.0},
        {"prompt_index": 1, "value": 1.0},
    ]
    low, high = cluster_interval(
        rows, lambda row: row["value"], repetitions=1000, seed=7
    )
    assert low == 0.0
    assert high == 1.0


def test_variant_summary_uses_equal_trial_means() -> None:
    rows = []
    for prompt_index, rate in ((0, 0.0), (1, 0.04)):
        rows.append(
            {
                "prompt_index": prompt_index,
                "correction_rate": rate,
                "mean_contract_source_mass": 0.75,
                "mean_contract_truncation_kl_nats": 0.3,
                "shared_contract_exact_rate": 0.8,
                "sentence_complete": True,
                "corrected_exact": True,
                "uncorrected_exact": False,
            }
        )
    summary = summarize_variant(rows, repetitions=100, seed=1)
    assert summary["correction_rate"]["mean"] == 0.02
    assert summary["corrected_exact_rate"]["mean"] == 1.0
