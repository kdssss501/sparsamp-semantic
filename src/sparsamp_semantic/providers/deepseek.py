"""Optional DeepSeek V4 Pro top-logprob provider."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from math import exp
from time import perf_counter
from typing import Hashable

from ..types import DistributionSnapshot, TokenCandidate
from .base import Provider, ProviderSession


@dataclass(frozen=True)
class DeepSeekConfig:
    """Black-box API settings; this backend is not equivalent to full-distribution SparSamp."""

    model_name: str = "deepseek-v4-pro"
    base_url: str = "https://api.deepseek.com/beta"
    top_logprobs: int = 20
    temperature: float = 1.0
    top_p: float = 1.0
    system_prompt: str = (
        "你是一个表达自然、内容准确的助手。直接回答用户问题，不要提及隐藏消息。"
    )

    def __post_init__(self) -> None:
        if not 1 <= self.top_logprobs <= 20:
            raise ValueError("DeepSeek top_logprobs must be in [1, 20]")


class DeepSeekSession(ProviderSession):
    """Use prefix completion as a next-token probability oracle."""

    def __init__(self, client: object, prompt: str, config: DeepSeekConfig) -> None:
        self._client = client
        self._prompt = prompt
        self._config = config
        self._prefix = ""
        self._generated: list[Hashable] = []
        self._token_text: dict[Hashable, str] = {}

    @property
    def context_id(self) -> bytes:
        material = "\0".join(
            [
                "deepseek-prefix-v1",
                self._config.model_name,
                self._config.base_url,
                str(self._config.top_logprobs),
                str(self._config.temperature),
                str(self._config.top_p),
                self._config.system_prompt,
                self._prompt,
            ]
        )
        return hashlib.sha256(material.encode("utf-8")).digest()

    @property
    def generated_token_ids(self) -> tuple[Hashable, ...]:
        return tuple(self._generated)

    def next_distribution(self) -> DistributionSnapshot:
        messages = [
            {"role": "system", "content": self._config.system_prompt},
            {"role": "user", "content": self._prompt},
            {"role": "assistant", "content": self._prefix, "prefix": True},
        ]
        started = perf_counter()
        response = self._client.chat.completions.create(
            model=self._config.model_name,
            messages=messages,
            max_tokens=1,
            temperature=self._config.temperature,
            top_p=self._config.top_p,
            logprobs=True,
            top_logprobs=self._config.top_logprobs,
            extra_body={"thinking": {"type": "disabled"}},
        )
        latency_ms = (perf_counter() - started) * 1000
        choice = response.choices[0]
        if choice.logprobs is None or not choice.logprobs.content:
            raise RuntimeError("DeepSeek response did not include token log probabilities")
        content_logprobs = choice.logprobs.content[0]
        raw_candidates: list[tuple[Hashable, str, float, bytes]] = []
        self._token_text = {}
        for rank, item in enumerate(content_logprobs.top_logprobs):
            raw_bytes = bytes(item.bytes) if item.bytes is not None else item.token.encode("utf-8")
            try:
                text = raw_bytes.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                continue
            token_id = f"{raw_bytes.hex()}:{rank}"
            raw_candidates.append((token_id, text, float(item.logprob), raw_bytes))
            self._token_text[token_id] = text
        if not raw_candidates:
            raise RuntimeError("DeepSeek returned no standalone UTF-8 candidate tokens")

        masses = [exp(item[2]) for item in raw_candidates]
        source_mass = sum(masses)
        candidates = tuple(
            TokenCandidate(
                token_id=token_id,
                text=text,
                probability=mass / source_mass,
                logprob=logprob,
                raw_bytes=raw_bytes,
                rank=rank,
            )
            for rank, ((token_id, text, logprob, raw_bytes), mass) in enumerate(
                zip(raw_candidates, masses, strict=True)
            )
        )
        native_text = choice.message.content or content_logprobs.token
        native_bytes = native_text.encode("utf-8")
        native_token_id = f"native:{native_bytes.hex()}"
        self._token_text[native_token_id] = native_text
        usage = {}
        if response.usage is not None:
            for name in ("prompt_tokens", "completion_tokens", "total_tokens"):
                value = getattr(response.usage, name, None)
                if value is not None:
                    usage[name] = int(value)
        return DistributionSnapshot(
            candidates=candidates,
            source_mass=min(source_mass, 1.0),
            native_token_id=native_token_id,
            model_name=self._config.model_name,
            model_fingerprint=getattr(response, "system_fingerprint", None),
            latency_ms=latency_ms,
            usage=usage,
            metadata={"observable_top_logprobs": len(candidates)},
        )

    def append(self, token_id: Hashable) -> None:
        try:
            text = self._token_text[token_id]
        except KeyError as error:
            raise ValueError(f"unknown DeepSeek token ID: {token_id!r}") from error
        self._generated.append(token_id)
        self._prefix += text

    def render(self) -> str:
        return self._prefix.strip()


class DeepSeekProvider(Provider):
    """Create API prefix-completion sessions from an environment-provided key."""

    def __init__(self, api_key: str, config: DeepSeekConfig | None = None) -> None:
        if not api_key:
            raise ValueError("DeepSeek API key is required")
        from openai import OpenAI

        self.config = config or DeepSeekConfig()
        self._client = OpenAI(api_key=api_key, base_url=self.config.base_url)

    def start(self, prompt: str) -> ProviderSession:
        return DeepSeekSession(self._client, prompt, self.config)

