from scripts.audit_replay_certificate import common_prefix_length, result_signature, summarize


def test_common_prefix_length_stops_at_first_difference() -> None:
    assert common_prefix_length([1, 2, 3], [1, 2, 4]) == 2
    assert common_prefix_length([1, 2], [9, 2]) == 0


def test_replay_summary_keeps_corrected_and_uncorrected_results_separate() -> None:
    rows = [
        {
            "policy": "seeded",
            "replay_completed": True,
            "corrected_exact": True,
            "uncorrected_exact": False,
            "correction_rate": 0.1,
            "reference_tokens_in_envelope": 10,
            "token_count": 10,
            "sparse_to_full_payload_ratio": 0.15,
            "uncorrected_common_prefix_tokens": 4,
            "shared_contract_exact_rate": 0.9,
            "mean_contract_source_mass": 0.5,
            "mean_contract_truncation_kl_nats": 0.7,
            "sentence_complete": True,
        }
    ]
    result = summarize(rows)["seeded"]
    assert result["corrected_exact_successes"] == 1
    assert result["uncorrected_exact_successes"] == 0
    assert result["mean_correction_rate"] == 0.1
    assert result["mean_contract_source_mass"] == 0.5
    assert result["sentence_complete_successes"] == 1
    assert result["mean_token_count"] == 10


def test_result_signature_excludes_runtime_only_fields() -> None:
    base = {
        "prompt_index": 0,
        "seed": 0,
        "policy": "seeded",
        "reference_token_sha256": "abc",
        "corrections": [{"step": 1, "token_id": 2}],
        "corrected_exact": True,
        "uncorrected_exact": False,
    }
    assert result_signature([{**base, "replay_seconds": 1.0}]) == result_signature(
        [{**base, "replay_seconds": 9.0}]
    )
