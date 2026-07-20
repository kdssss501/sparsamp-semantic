from scripts.analyze_replay_scale import cluster_bootstrap_mean, percentile, wilson_interval


def test_wilson_interval_is_bounded_for_perfect_sample() -> None:
    low, high = wilson_interval(60, 60)
    assert 0.93 < low < 0.95
    assert high == 1.0


def test_percentile_interpolates_sorted_values() -> None:
    assert percentile([0.0, 1.0], 0.25) == 0.25


def test_cluster_bootstrap_keeps_seed_rows_with_their_prompt() -> None:
    rows = [
        {"prompt_index": 0, "value": 0.0},
        {"prompt_index": 0, "value": 0.0},
        {"prompt_index": 1, "value": 1.0},
        {"prompt_index": 1, "value": 1.0},
    ]
    low, high = cluster_bootstrap_mean(
        rows, lambda row: row["value"], repetitions=1000, seed=7
    )
    assert low == 0.0
    assert high == 1.0
