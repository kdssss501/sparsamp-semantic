from scripts.analyze_replay_ablations import compare_variants, summarize_variant


def make_row(prompt_index: int, *, correction_count: int, source_mass: float) -> dict:
    token_count = 10 * (prompt_index + 1)
    return {
        "prompt_index": prompt_index,
        "seed": 0,
        "policy": "seeded",
        "token_count": token_count,
        "correction_count": correction_count,
        "mean_contract_source_mass": source_mass,
        "mean_contract_truncation_kl_nats": 1.0 - source_mass,
        "mean_reference_quantization_kl_nats": 0.01,
        "mean_reference_quantization_tv": 0.02,
        "shared_contract_exact_steps": token_count - correction_count,
        "sparse_payload_bytes": correction_count + 1,
        "full_trace_payload_bytes": token_count * 4,
        "sentence_complete": True,
        "corrected_exact": True,
        "uncorrected_exact": correction_count == 0,
        "reference_seconds": token_count / 2,
        "replay_seconds": token_count,
        "reference_tokens_in_top4": token_count,
        "reference_tokens_in_top8": token_count,
        "reference_token_sha256": f"trace-{prompt_index}",
    }


def make_report() -> dict:
    return {
        "run_label": "test",
        "result_signature": "signature",
        "experiment_config": {
            "reference_dtype": "float16",
            "replay_dtype": "bfloat16",
            "contract_top_k": 2,
        },
    }


def test_variant_summary_uses_token_weighted_rates() -> None:
    rows = [
        make_row(0, correction_count=1, source_mass=0.5),
        make_row(1, correction_count=3, source_mass=0.75),
    ]
    result = summarize_variant(make_report(), rows, repetitions=100, seed=7)
    assert result["metrics"]["correction_rate"]["value"] == 4 / 30
    assert result["metrics"]["contract_source_mass"]["value"] == 2 / 3
    assert result["reference_tokens_per_second"] == 2.0


def test_paired_comparison_reports_candidate_minus_baseline() -> None:
    baseline = [
        make_row(0, correction_count=1, source_mass=0.5),
        make_row(1, correction_count=3, source_mass=0.75),
    ]
    candidate = [
        make_row(0, correction_count=0, source_mass=0.75),
        make_row(1, correction_count=0, source_mass=0.875),
    ]
    result = compare_variants(baseline, candidate, repetitions=100, seed=11)
    assert result["matched_trials"] == 2
    assert result["matching_reference_trajectories"] == 2
    assert result["deltas"]["correction_rate"]["candidate_minus_baseline"] == -4 / 30
    assert result["deltas"]["contract_source_mass"]["candidate_minus_baseline"] > 0
