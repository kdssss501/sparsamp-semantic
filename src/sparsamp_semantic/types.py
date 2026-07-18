"""Shared model-provider data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, localcontext
from fractions import Fraction
from math import exp, log
from typing import Any, Hashable, Sequence


def _as_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, Fraction):
        return Decimal(value.numerator) / Decimal(value.denominator)
    return Decimal(str(value))


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
        """Reverse KL(Q||P) when candidates are P conditioned on retained support."""

        return -log(min(self.source_mass, 1.0))

    def forward_kl_to_nats(self, implemented: Sequence[Any]) -> float:
        """Return paper-direction KL(Q||R) for the actually sampled probabilities."""

        if len(implemented) != len(self.candidates):
            raise ValueError("implemented distribution must align with candidates")
        with localcontext() as context:
            context.prec = 60
            cover = [Decimal(str(item.probability)) for item in self.candidates]
            sampled = [_as_decimal(value) for value in implemented]
            if any(value < 0 for value in sampled):
                raise ValueError("implemented probabilities must be non-negative")
            cover_total = sum(cover, start=Decimal(0))
            sampled_total = sum(sampled, start=Decimal(0))
            if cover_total <= 0 or sampled_total <= 0:
                raise ValueError("probability distributions must have positive mass")
            cover = [value / cover_total for value in cover]
            sampled = [value / sampled_total for value in sampled]
            divergence = Decimal(0)
            for q_value, r_value in zip(cover, sampled, strict=True):
                if q_value == 0:
                    continue
                if r_value == 0:
                    return float("inf")
                divergence += q_value * (q_value / r_value).ln()
            return max(0.0, float(divergence))

    def total_variation_to(self, implemented: Sequence[Any]) -> float:
        """Return TV(Q,R) for the cover and actually sampled distributions."""

        if len(implemented) != len(self.candidates):
            raise ValueError("implemented distribution must align with candidates")
        with localcontext() as context:
            context.prec = 60
            cover = [Decimal(str(item.probability)) for item in self.candidates]
            sampled = [_as_decimal(value) for value in implemented]
            if any(value < 0 for value in sampled):
                raise ValueError("implemented probabilities must be non-negative")
            cover_total = sum(cover, start=Decimal(0))
            sampled_total = sum(sampled, start=Decimal(0))
            if cover_total <= 0 or sampled_total <= 0:
                raise ValueError("probability distributions must have positive mass")
            distance = sum(
                abs(q_value / cover_total - r_value / sampled_total)
                for q_value, r_value in zip(cover, sampled, strict=True)
            ) / 2
            return float(distance)

    def support_loss_to(self, implemented: Sequence[Any]) -> tuple[int, float]:
        """Return candidate count and Q-mass removed by an implemented distribution."""

        if len(implemented) != len(self.candidates):
            raise ValueError("implemented distribution must align with candidates")
        with localcontext() as context:
            context.prec = 60
            target = [Decimal(str(item.probability)) for item in self.candidates]
            sampled = [_as_decimal(value) for value in implemented]
            if any(value < 0 for value in sampled):
                raise ValueError("implemented probabilities must be non-negative")
            target_total = sum(target, start=Decimal(0))
            sampled_total = sum(sampled, start=Decimal(0))
            if target_total <= 0 or sampled_total <= 0:
                raise ValueError("probability distributions must have positive mass")
            lost = [
                target_value / target_total
                for target_value, sampled_value in zip(target, sampled, strict=True)
                if target_value > 0 and sampled_value == 0
            ]
            return len(lost), float(sum(lost, start=Decimal(0)))

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
