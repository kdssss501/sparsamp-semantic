"""Application service that composes providers, codecs, and persisted artifacts."""

from __future__ import annotations

import os
import random
import sys
from dataclasses import asdict
from pathlib import Path
from threading import Lock
from typing import Any, Callable

from ..core import CodecConfig, SparSampCodec
from ..payload import PayloadCodec
from ..providers.huggingface import HuggingFaceConfig, HuggingFaceProvider
from .repository import ExperimentRepository
from .schemas import (
    CodecSettings,
    DecodeOperationRequest,
    EncodeOperationRequest,
    NativeOperationRequest,
    SamplingConfig,
)


ProgressCallback = Callable[[int, str], None]


class ResearchService:
    """Run local research workflows while reusing model weights across requests."""

    def __init__(self, repository: ExperimentRepository) -> None:
        self.repository = repository
        self._providers: dict[tuple[Any, ...], HuggingFaceProvider] = {}
        self._provider_lock = Lock()

    def encode(
        self,
        operation_id: str,
        request: EncodeOperationRequest,
        progress: ProgressCallback,
    ) -> dict[str, Any]:
        key = request.secret_key.encode("utf-8")
        progress(10, "加载语言模型")
        provider, model_config = self._provider(request.sampling)
        codec, payload_codec = self._codecs(request.codec)
        payload_bits = payload_codec.seal(request.message, key)
        progress(25, "计算完整分布并嵌入")
        session = provider.start_with_config(request.prompt, model_config)
        encoded = codec.encode(session, payload_bits, key)
        progress(88, "检测 Token Ambiguity")
        retokenized = session.retokenize(encoded.text)
        token_ambiguity = retokenized != encoded.token_ids
        artifact = {
            "schema": "sparsamp-semantic-result-v1",
            "prompt": request.prompt,
            "provider": {"type": "huggingface", **asdict(model_config)},
            "codec": asdict(codec.config),
            "payload": {"repetitions": payload_codec.repetitions},
            "cover_text": encoded.text,
            "token_ids": list(encoded.token_ids),
            "token_ambiguity": token_ambiguity,
            "metrics": {
                "embedded_bits": encoded.embedded_bits,
                "padded_bits": encoded.padded_bits,
                "token_count": len(encoded.token_ids),
                "elapsed_seconds": encoded.elapsed_seconds,
                "bits_per_token": encoded.bits_per_token,
                "bits_per_second": encoded.bits_per_second,
                "entropy_utilization": encoded.entropy_utilization,
                "truncation_kl_nats": encoded.truncation_kl_nats,
            },
            "records": [asdict(record) for record in encoded.records],
        }
        artifact_path = self.repository.write(operation_id, artifact)
        progress(96, "保存脱敏实验记录")
        return {
            "artifact_id": artifact_path,
            "cover_text": encoded.text,
            "token_ambiguity": token_ambiguity,
            "metrics": artifact["metrics"],
        }

    def decode(
        self,
        operation_id: str,
        request: DecodeOperationRequest,
        progress: ProgressCallback,
    ) -> dict[str, Any]:
        del operation_id
        key = request.secret_key.encode("utf-8")
        if request.artifact_id:
            artifact = self.repository.read(request.artifact_id)
            provider_values = {
                name: value for name, value in artifact["provider"].items() if name != "type"
            }
            model_config = HuggingFaceConfig(**provider_values)
            provider = self._provider_for_config(model_config)
            codec = SparSampCodec(CodecConfig(**artifact["codec"]))
            payload_codec = PayloadCodec(**artifact["payload"])
            prompt = artifact["prompt"]
            token_ids = tuple(artifact["token_ids"])
            source = "artifact_token_ids"
            progress(25, "载入 artifact token IDs")
        else:
            if request.sampling is None or request.codec is None:
                raise ValueError("text decode settings are missing")
            provider, model_config = self._provider(request.sampling)
            codec, payload_codec = self._codecs(request.codec)
            prompt = request.prompt or ""
            progress(25, "重新分词 cover text")
            session_for_tokens = provider.start_with_config(prompt, model_config)
            token_ids = session_for_tokens.retokenize(request.cover_text or "")
            source = "cover_text"
        progress(45, "回放概率分布并解码")
        session = provider.start_with_config(prompt, model_config)
        decoded = codec.decode(session, list(token_ids), key)
        progress(92, "认证加密载荷")
        message = payload_codec.open(decoded.bits, key)
        return {
            "message": message,
            "source": source,
            "token_count": len(token_ids),
            "decoded_blocks": decoded.completed_blocks,
        }

    def native(
        self,
        operation_id: str,
        request: NativeOperationRequest,
        progress: ProgressCallback,
    ) -> dict[str, Any]:
        del operation_id
        provider, model_config = self._provider(request.sampling)
        session = provider.start_with_config(request.prompt, model_config)
        rng = random.Random(request.sampling.seed)
        latencies: list[float] = []
        for index in range(request.tokens):
            snapshot = session.next_distribution()
            if snapshot.latency_ms is not None:
                latencies.append(snapshot.latency_ms)
            target = rng.random()
            cumulative = 0.0
            selected = snapshot.candidates[-1]
            for candidate in snapshot.candidates:
                cumulative += candidate.probability
                if target < cumulative:
                    selected = candidate
                    break
            session.append(selected.token_id)
            if index % max(1, request.tokens // 20) == 0:
                progress(15 + int(80 * (index + 1) / request.tokens), "生成语义基线")
        return {
            "text": session.render(),
            "token_count": request.tokens,
            "mean_token_latency_ms": sum(latencies) / len(latencies) if latencies else None,
        }

    def _provider(self, sampling: SamplingConfig) -> tuple[HuggingFaceProvider, HuggingFaceConfig]:
        values = sampling.model_dump()
        values["model_name"] = values.pop("model")
        config = HuggingFaceConfig(**values)
        return self._provider_for_config(config), config

    def _provider_for_config(self, config: HuggingFaceConfig) -> HuggingFaceProvider:
        key = (
            config.model_name,
            config.revision,
            config.device,
            config.dtype,
            config.load_in_4bit,
        )
        with self._provider_lock:
            provider = self._providers.get(key)
            if provider is None:
                provider = HuggingFaceProvider(config)
                self._providers[key] = provider
        return provider

    @staticmethod
    def _codecs(settings: CodecSettings) -> tuple[SparSampCodec, PayloadCodec]:
        values = settings.model_dump()
        repetitions = values.pop("repetitions")
        return SparSampCodec(CodecConfig(**values)), PayloadCodec(repetitions=repetitions)


def project_root() -> Path:
    """Return the repository root for source and installed editable workflows."""

    configured = os.environ.get("SPARSAMP_WORKSPACE")
    if configured:
        root = Path(configured).expanduser().resolve()
        if not (root / "pyproject.toml").is_file():
            raise RuntimeError("SPARSAMP_WORKSPACE does not contain pyproject.toml")
        return root
    current = Path.cwd().resolve()
    environment_root = Path(sys.prefix).resolve().parent
    for candidate in (current, *current.parents, environment_root):
        if (candidate / "pyproject.toml").is_file() and (
            candidate / "src" / "sparsamp_semantic"
        ).is_dir():
            return candidate
    source_root = Path(__file__).resolve().parents[3]
    if (source_root / "pyproject.toml").is_file():
        return source_root
    raise RuntimeError("start sparsamp-web from the project root or set SPARSAMP_WORKSPACE")
