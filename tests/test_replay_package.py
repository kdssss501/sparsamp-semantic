import copy
import hashlib

import pytest

from sparsamp_semantic.replay_package import (
    export_reference_bundle,
    model_fingerprint,
    validate_reference_bundle,
)


def reference_row() -> dict:
    return {
        "prompt_index": 0,
        "prompt": "Explain reproducibility.",
        "seed": 0,
        "policy": "seeded",
        "reference_completed": True,
        "token_count": 2,
        "reference_token_ids": [1, 2],
        "reference_token_sha256": "abc",
        "reference_text": "text.",
        "sentence_complete": True,
        "stopped_on_sentence": True,
        "reference_contracts": [{}, {}],
        "reference_seconds": 1.0,
        "mean_reference_source_mass": 1.0,
        "mean_contract_source_mass": 0.8,
        "mean_contract_truncation_kl_nats": 0.2,
        "mean_reference_quantization_kl_nats": 0.01,
        "mean_reference_quantization_tv": 0.02,
        "replay_completed": True,
    }


def test_reference_bundle_filters_replay_fields_and_signs_content() -> None:
    report = {
        "phase": "completed",
        "run_label": "R044",
        "result_signature": "result",
        "environment": {"python": "3.11"},
        "experiment_config": {"model": "logical", "seeds": [0]},
        "rows": [reference_row()],
    }
    bundle = export_reference_bundle(
        report,
        seeds=[0],
        model={"signature": "model"},
        source_sha256="source",
    )
    validate_reference_bundle(bundle)
    assert "replay_completed" not in bundle["rows"][0]
    changed = copy.deepcopy(bundle)
    changed["rows"][0]["token_count"] = 3
    with pytest.raises(ValueError, match="signature mismatch"):
        validate_reference_bundle(changed)


def test_model_fingerprint_hashes_nested_files(tmp_path) -> None:
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    (tmp_path / "model.safetensors").write_bytes(b"weights")
    value = model_fingerprint(tmp_path)
    assert value["files"][0]["sha256"] == hashlib.sha256(b"{}").hexdigest()
    assert value["files"][1]["sha256"] == hashlib.sha256(b"weights").hexdigest()
