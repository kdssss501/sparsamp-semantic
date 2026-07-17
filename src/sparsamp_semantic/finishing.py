"""Native-sampling tails that finish visible text after payload embedding."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from time import perf_counter
from typing import Hashable, Literal

from .providers.base import ProviderSession


_SENTENCE_END = re.compile(r"[.!?。！？](?:[\"'”’）)\]】》」』*_\s]*)$")
_ORDERED_LIST_MARKER = re.compile(r"(?:^|\n)\s*\d{1,3}\.\s*$")


def is_sentence_complete(text: str) -> bool:
    """Return true for a visible sentence end, excluding standalone list markers."""

    if _ORDERED_LIST_MARKER.search(text) is not None:
        return False
    return _SENTENCE_END.search(text) is not None


@dataclass(frozen=True)
class FinishingConfig:
    """Control a non-embedding tail generated from the provider's native sampler."""

    mode: Literal["none", "punctuation", "fixed"] = "none"
    max_tokens: int = 32
    min_tokens: int = 4

    def __post_init__(self) -> None:
        if self.mode not in {"none", "punctuation", "fixed"}:
            raise ValueError("finishing mode must be 'none', 'punctuation', or 'fixed'")
        if self.max_tokens < 0:
            raise ValueError("finishing max_tokens must be non-negative")
        if self.min_tokens < 0:
            raise ValueError("finishing min_tokens must be non-negative")
        if self.mode == "punctuation" and self.min_tokens > self.max_tokens:
            raise ValueError("finishing min_tokens cannot exceed max_tokens")


@dataclass(frozen=True)
class FinishingStep:
    """Audit information for one native tail token."""

    step: int
    token_id: Hashable
    text: str
    latency_ms: float
    entropy_bits: float
    source_mass: float


@dataclass(frozen=True)
class FinishingResult:
    """Visible text and token sequence after an optional native tail."""

    token_ids: tuple[Hashable, ...]
    text: str
    tail_token_ids: tuple[Hashable, ...]
    elapsed_seconds: float
    stopped_on_punctuation: bool
    records: tuple[FinishingStep, ...] = field(default_factory=tuple)

    @property
    def tail_token_count(self) -> int:
        return len(self.tail_token_ids)


def finish_session(
    session: ProviderSession, config: FinishingConfig | None = None
) -> FinishingResult:
    """Append native tokens without embedding until the configured public stop rule fires."""

    config = config or FinishingConfig()
    started = perf_counter()
    initial_count = len(session.generated_token_ids)
    records: list[FinishingStep] = []
    stopped_on_punctuation = False

    if config.mode != "none":
        for step in range(config.max_tokens):
            snapshot = session.next_distribution()
            if snapshot.native_token_id is None:
                raise RuntimeError("provider does not expose a native sampled token")
            token_id = snapshot.native_token_id
            try:
                token_text = next(
                    candidate.text
                    for candidate in snapshot.candidates
                    if candidate.token_id == token_id
                )
            except StopIteration as error:
                raise RuntimeError("native token is absent from the retained distribution") from error
            session.append(token_id)
            records.append(
                FinishingStep(
                    step=step,
                    token_id=token_id,
                    text=token_text,
                    latency_ms=snapshot.latency_ms,
                    entropy_bits=snapshot.entropy_bits,
                    source_mass=snapshot.source_mass,
                )
            )
            generated = step + 1
            if (
                config.mode == "punctuation"
                and generated >= config.min_tokens
                and is_sentence_complete(session.render())
            ):
                stopped_on_punctuation = True
                break

    token_ids = session.generated_token_ids
    return FinishingResult(
        token_ids=token_ids,
        text=session.render(),
        tail_token_ids=token_ids[initial_count:],
        elapsed_seconds=perf_counter() - started,
        stopped_on_punctuation=stopped_on_punctuation,
        records=tuple(records),
    )
