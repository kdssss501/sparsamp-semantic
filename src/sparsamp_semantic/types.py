"""Shared model-provider data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import exp, log
from typing import Any, Hashable


@dataclass(frozen=True)
class TokenCandidate:
    """One token and its probability within the provider distribution."""

    token_id: Hashable
    text: str
    probability: float
    logprob: float | None = None
    raw_bytes: bytes | None = None
    rank: int = 0

    def __post_init__(self) -> None:
        if not 0.0 < self.probability <= 1.0:
            raise ValueError(f"invalid token probability: {self.probability}")


@dataclass(frozen=True)
class DistributionSnapshot:
    """A reproducible next-token distribution and provider metadata."""

    candidates: tuple[TokenCandidate, ...]
    source_mass: float = 1.0
    native_token_id: Hashable | None = None
    model_name: str = "unknown"
    model_fingerprint: str | None = None
    latency_ms: float = 0.0
    usage: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.candidates:
            raise ValueError("a distribution must contain at least one candidate")
        total = sum(item.probability for item in self.candidates)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"candidate probabilities must sum to 1, got {total}")
        if not 0.0 < self.source_mass <= 1.000001:
            raise ValueError(f"invalid source mass: {self.source_mass}")

    @property
    def entropy_bits(self) -> float:
        """Shannon entropy of the normalized candidate distribution."""

        return -sum(item.probability * log(item.probability, 2) for item in self.candidates)

    @property
    def truncation_kl_nats(self) -> float:
        """KL(Q||P) when candidates are P conditioned on retained support."""

        return -log(min(self.source_mass, 1.0))

    @classmethod
    def from_logprobs(
        cls,
        candidates: list[tuple[Hashable, str, float, bytes | None]],
        **kwargs: Any,
    ) -> "DistributionSnapshot":
        """Build a normalized snapshot from raw log probabilities."""

        raw = [exp(logprob) for _, _, logprob, _ in candidates]
        source_mass = sum(raw)
        if source_mass <= 0:
            raise ValueError("log probabilities have zero total mass")
        normalized = tuple(
            TokenCandidate(
                token_id=token_id,
                text=text,
                probability=probability / source_mass,
                logprob=logprob,
                raw_bytes=raw_bytes,
                rank=rank,
            )
            for rank, ((token_id, text, logprob, raw_bytes), probability) in enumerate(
                zip(candidates, raw, strict=True)
            )
        )
        return cls(candidates=normalized, source_mass=min(source_mass, 1.0), **kwargs)

