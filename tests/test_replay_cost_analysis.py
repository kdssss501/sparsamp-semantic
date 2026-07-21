from scripts.analyze_replay_cost import analyze
from sparsamp_semantic.replay_package import canonical_signature


def bundle() -> dict:
    value = {
        "schema": "precision-replay-reference-bundle-v1",
        "experiment_config": {"contract_top_k": 2},
        "model_fingerprint": {"signature": "ab" * 32},
        "source": {},
        "rows": [{"prompt_index": 0, "seed": 0, "policy": "seeded"}],
    }
    value["bundle_signature"] = canonical_signature(value)
    return value


def target(reference: dict) -> dict:
    return {
        "phase": "completed",
        "experiment_config": {"bundle_signature": reference["bundle_signature"]},
        "environment": {"signature": "cd" * 32},
        "rows": [
            {
                "prompt_index": 0,
                "seed": 0,
                "policy": "seeded",
                "token_count": 4,
                "reference_token_ids": [1, 2, 3, 4],
                "reference_token_sha256": "ef" * 32,
                "corrections": [{"step": 1, "token_id": 2}],
                "correction_count": 1,
                "correction_rate": 0.25,
                "corrected_exact": True,
                "uncorrected_exact": False,
                "manifest_construction_seconds": 2.0,
                "corrected_replay_seconds": 1.0,
                "uncorrected_replay_seconds": 1.0,
            }
        ],
    }


def test_complete_cost_includes_headers_and_separated_timing() -> None:
    reference = bundle()
    result = analyze(reference, target(reference))
    assert result["corrected_exact"] == 1
    assert result["serialization"]["certificate_package_bytes"] > result["serialization"][
        "manifest_payload_bytes"
    ]
    assert result["serialization"]["complete_package_ratio"] > result["serialization"][
        "payload_ratio"
    ]
    assert result["serialization"]["referenced_package_ratio"] < result["serialization"][
        "complete_package_ratio"
    ]
    assert result["timing"]["manifest_tokens_per_second"] == 2.0
    assert result["timing"]["corrected_replay_tokens_per_second"] == 4.0
