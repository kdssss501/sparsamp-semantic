from scripts.analyze_replay_baselines import analyze, block_repair_payload
from sparsamp_semantic.replay_package import canonical_signature


def _bundle() -> dict:
    value = {
        "schema": "precision-replay-reference-bundle-v1",
        "experiment_config": {"contract_top_k": 2},
        "model_fingerprint": {"signature": "ab" * 32},
        "source": {},
        "rows": [{"prompt_index": 0, "seed": 0, "policy": "seeded"}],
    }
    value["bundle_signature"] = canonical_signature(value)
    return value


def _target(bundle: dict) -> dict:
    return {
        "phase": "completed",
        "experiment_config": {"bundle_signature": bundle["bundle_signature"]},
        "environment": {"signature": "cd" * 32},
        "rows": [
            {
                "prompt_index": 0,
                "seed": 0,
                "policy": "seeded",
                "token_count": 6,
                "reference_token_ids": [10, 11, 12, 13, 14, 15],
                "reference_token_sha256": "ef" * 32,
                "corrections": [
                    {"step": 1, "token_id": 11},
                    {"step": 4, "token_id": 14},
                ],
                "corrected_exact": True,
                "uncorrected_exact": False,
            }
        ],
    }


def test_block_repair_serializes_only_dirty_blocks() -> None:
    row = _target(_bundle())["rows"][0]

    payload = block_repair_payload(row, 2)

    assert payload.startswith(b"SPRB\x01")
    assert len(payload) < len(block_repair_payload(row, 4))


def test_baselines_share_boundary_and_expose_missing_native_delta() -> None:
    bundle = _bundle()
    result = analyze(bundle, _target(bundle), block_sizes=(2, 4))
    methods = {item["name"]: item for item in result["baselines"]}

    assert methods["seed_only"]["exact_successes"] == 0
    assert methods["sparse_precision_replay_certificate"]["exact_successes"] == 1
    assert methods["full_token_trace"]["exact_successes"] == 1
    assert methods["sparse_precision_replay_certificate"]["referenced_package_bytes"] < methods[
        "full_token_trace"
    ]["referenced_package_bytes"]
    assert result["missing_baselines"][0]["name"] == "native_softmax_target_conditioned_delta"
