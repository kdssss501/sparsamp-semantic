"""REST contract tests without loading a real language model."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import pytest
from fastapi.testclient import TestClient

from sparsamp_semantic.api.app import create_app
from sparsamp_semantic.api.repository import ExperimentRepository
from sparsamp_semantic.api.schemas import CodecSettings, DecodeOperationRequest, SamplingConfig
from sparsamp_semantic.api.service import ResearchService
from sparsamp_semantic.core import DecodeResult


class StubResearchService:
    def encode(
        self, operation_id: str, request: Any, progress: Callable[[int, str], None]
    ) -> dict[str, Any]:
        progress(80, "stub")
        return {"artifact_id": f"web/{operation_id}.json", "cover_text": "cover"}

    def decode(
        self, operation_id: str, request: Any, progress: Callable[[int, str], None]
    ) -> dict[str, Any]:
        del operation_id, request
        progress(90, "stub")
        return {"message": "A-17"}

    def native(
        self, operation_id: str, request: Any, progress: Callable[[int, str], None]
    ) -> dict[str, Any]:
        del operation_id, request
        progress(90, "stub")
        return {"text": "baseline"}


def test_operation_contract_and_secret_redaction(tmp_path: Path) -> None:
    app = create_app(
        output_root=tmp_path, web_dist=tmp_path / "missing", service=StubResearchService()
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/operations",
            json={
                "kind": "encode",
                "prompt": "Research prompt",
                "message": "A-17",
                "secret_key": "this-is-a-test-secret",
            },
        )
        assert response.status_code == 202
        operation_id = response.json()["data"]["id"]
        operation = client.get(f"/api/v1/operations/{operation_id}").json()["data"]
        for _ in range(100):
            if operation["status"] in {"succeeded", "failed"}:
                break
            operation = client.get(f"/api/v1/operations/{operation_id}").json()["data"]
        assert operation["status"] == "succeeded"
        assert "secret" not in str(operation).lower()
        assert "test-secret" not in str(operation)


def test_validation_and_not_found_errors_include_request_id(tmp_path: Path) -> None:
    app = create_app(
        output_root=tmp_path, web_dist=tmp_path / "missing", service=StubResearchService()
    )
    with TestClient(app) as client:
        invalid = client.post("/api/v1/operations", json={"kind": "encode"})
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
        assert invalid.json()["error"]["request_id"]

        missing = client.get("/api/v1/operations/not-found")
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "OPERATION_NOT_FOUND"


def test_repository_rejects_path_escape_and_paginates(tmp_path: Path) -> None:
    repository = ExperimentRepository(tmp_path)
    repository.write("first", {"prompt": "p1", "metrics": {"bits_per_token": 1.0}})
    repository.write("second", {"prompt": "p2", "metrics": {"bits_per_token": 2.0}})
    page = repository.list_artifacts(limit=1)
    assert len(page["data"]) == 1
    assert page["page"]["next_cursor"] == "1"
    try:
        repository.read("../outside.json")
    except ValueError:
        pass
    else:
        raise AssertionError("path traversal must be rejected")


def test_sampling_model_maps_to_huggingface_model_name(tmp_path: Path) -> None:
    service = ResearchService(ExperimentRepository(tmp_path))
    provider, config = service._provider(
        SamplingConfig(model="models/local-qwen", candidate_order="token_id")
    )
    assert config.model_name == "models/local-qwen"
    assert config.candidate_order == "token_id"
    assert provider.config.model_name == "models/local-qwen"


def test_decode_result_exposes_completed_block_count() -> None:
    result = DecodeResult(bits="1010", completed_blocks=2, consumed_tokens=7)
    assert result.completed_blocks == 2


def test_artifact_decode_request_only_requires_secret_and_artifact() -> None:
    request = DecodeOperationRequest.model_validate(
        {
            "kind": "decode",
            "artifact_id": "web/example.json",
            "secret_key": "this-is-a-test-secret",
        }
    )
    assert request.artifact_id == "web/example.json"


def test_codec_settings_default_to_bounded_punctuation_finishing() -> None:
    settings = CodecSettings()
    codec, payload, finishing = ResearchService._codecs(settings)

    assert codec.config.block_size == 32
    assert payload.repetitions == 1
    assert finishing.mode == "punctuation"
    assert finishing.max_tokens == 32


def test_codec_settings_reject_invalid_finishing_budget() -> None:
    try:
        CodecSettings(finish_min_tokens=9, finish_max_tokens=8)
    except ValueError as error:
        assert "finish_min_tokens" in str(error)
    else:
        raise AssertionError("invalid finishing budget must be rejected")


def test_codec_settings_accept_integer_mass_or_decimal_quantum_but_not_both() -> None:
    settings = CodecSettings(probability_quantum=None, probability_mass_bits=32)
    codec, _, _ = ResearchService._codecs(settings)

    assert codec.config.probability_mass_bits == 32
    assert codec.config.probability_quantum is None

    with pytest.raises(ValueError, match="mutually exclusive"):
        CodecSettings(probability_quantum="1e-15", probability_mass_bits=32)
