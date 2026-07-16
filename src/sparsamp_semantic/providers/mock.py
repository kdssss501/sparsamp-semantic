"""Dependency-free deterministic provider for algorithm and CLI tests."""

from __future__ import annotations

import hashlib
from typing import Hashable

from ..types import DistributionSnapshot, TokenCandidate
from .base import Provider, ProviderSession


_VOCABULARY = (
    (" This", " The", " A", " One"),
    (" method", " system", " study", " approach"),
    (" produces", " preserves", " improves", " supports"),
    (" coherent", " reliable", " practical", " secure"),
    (" language", " communication", " decoding", " sampling"),
    (".", ", while", " with", " for"),
)
_PROBABILITIES = (0.4, 0.3, 0.2, 0.1)


class MockSession(ProviderSession):
    """A readable cyclic language model with a fixed four-way distribution."""

    def __init__(self, prompt: str, source_mass: float = 1.0) -> None:
        self._prompt = prompt
        self._source_mass = source_mass
        self._generated: list[Hashable] = []
        self._texts: list[str] = []
        self._last_candidates: dict[Hashable, str] = {}

    @property
    def context_id(self) -> bytes:
        return hashlib.sha256(("mock-v1\0" + self._prompt).encode("utf-8")).digest()

    @property
    def generated_token_ids(self) -> tuple[Hashable, ...]:
        return tuple(self._generated)

    def next_distribution(self) -> DistributionSnapshot:
        step = len(self._generated)
        words = _VOCABULARY[step % len(_VOCABULARY)]
        candidates = tuple(
            TokenCandidate(
                token_id=f"{step}:{rank}",
                text=word,
                raw_bytes=word.encode("utf-8"),
                probability=probability,
                rank=rank,
            )
            for rank, (word, probability) in enumerate(zip(words, _PROBABILITIES, strict=True))
        )
        self._last_candidates = {candidate.token_id: candidate.text for candidate in candidates}
        return DistributionSnapshot(
            candidates=candidates,
            source_mass=self._source_mass,
            native_token_id=candidates[0].token_id,
            model_name="mock-semantic-v1",
            model_fingerprint="mock-v1",
        )

    def append(self, token_id: Hashable) -> None:
        if token_id not in self._last_candidates:
            raise ValueError(f"token {token_id!r} is not in the current mock distribution")
        self._generated.append(token_id)
        self._texts.append(self._last_candidates[token_id])

    def render(self) -> str:
        return "".join(self._texts).strip()


class MockProvider(Provider):
    """Create deterministic mock sessions."""

    def __init__(self, source_mass: float = 1.0) -> None:
        self._source_mass = source_mass

    def start(self, prompt: str) -> ProviderSession:
        return MockSession(prompt, source_mass=self._source_mass)

