"""Finite-horizon adaptive block scheduling for SparSamp."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from time import perf_counter
from typing import Hashable

from .core import (
    DecodeResult,
    EncodeResult,
    IncompleteEncodeError,
    StepRecord,
    _bounds,
    _ceil_fraction,
    _probabilities,
    _select,
)
from .prf import HmacRandomStream
from .providers.base import ProviderSession


@dataclass(frozen=True)
class FhCodecConfig:
    """Public configuration for finite-horizon block selection."""

    total_bits: int
    block_sizes: tuple[int, ...] = (8, 16, 32)
    block_schedule: tuple[int, ...] | None = None
    max_tokens: int = 192
    entropy_ema_alpha: float = 0.2
    min_entropy_bits: float = 0.25
    tight_capacity_ratio: float = 1.0
    loose_capacity_ratio: float = 1.5
    min_source_mass: float = 0.0
    probability_quantum: str | None = "1e-15"

    def __post_init__(self) -> None:
        if self.total_bits < 1:
            raise ValueError("total_bits must be positive")
        if not self.block_sizes:
            raise ValueError("block_sizes must not be empty")
        if tuple(sorted(set(self.block_sizes))) != self.block_sizes:
            raise ValueError("block_sizes must be unique and sorted")
        if self.block_sizes[0] < 1:
            raise ValueError("block sizes must be positive")
        if self.block_schedule is not None:
            if not self.block_schedule or any(size < 1 for size in self.block_schedule):
                raise ValueError("block_schedule must contain positive sizes")
            if sum(self.block_schedule) != self.total_bits:
                raise ValueError("block_schedule must sum to total_bits")
        if self.max_tokens < 1:
            raise ValueError("max_tokens must be positive")
        if not 0.0 < self.entropy_ema_alpha <= 1.0:
            raise ValueError("entropy_ema_alpha must be in (0, 1]")
        if self.min_entropy_bits <= 0:
            raise ValueError("min_entropy_bits must be positive")
        if self.tight_capacity_ratio < 0:
            raise ValueError("tight_capacity_ratio must be non-negative")
        if self.loose_capacity_ratio <= self.tight_capacity_ratio:
            raise ValueError("loose_capacity_ratio must exceed tight_capacity_ratio")
        if not 0.0 <= self.min_source_mass <= 1.0:
            raise ValueError("min_source_mass must be in [0, 1]")


def select_block_size(
    config: FhCodecConfig,
    *,
    remaining_bits: int,
    remaining_tokens: int,
    entropy_bits: float,
) -> int:
    """Select a replayable block size from the estimated remaining capacity."""

    if remaining_bits < 1:
        raise ValueError("remaining_bits must be positive")
    if remaining_tokens < 1:
        raise ValueError("remaining_tokens must be positive")
    candidates = tuple(size for size in config.block_sizes if size <= remaining_bits)
    if not candidates:
        return remaining_bits
    effective_entropy = max(entropy_bits, config.min_entropy_bits)
    capacity_ratio = effective_entropy * remaining_tokens / remaining_bits
    if capacity_ratio <= config.tight_capacity_ratio:
        return candidates[0]
    if capacity_ratio >= config.loose_capacity_ratio:
        return candidates[-1]
    position = (capacity_ratio - config.tight_capacity_ratio) / (
        config.loose_capacity_ratio - config.tight_capacity_ratio
    )
    index = min(int(position * len(candidates)), len(candidates) - 1)
    return candidates[index]


def _update_entropy_ema(previous: float | None, current: float, alpha: float) -> float:
    return current if previous is None else alpha * current + (1.0 - alpha) * previous


def _next_block_size(
    config: FhCodecConfig,
    *,
    completed_blocks: int,
    remaining_bits: int,
    remaining_tokens: int,
    entropy_bits: float,
) -> int:
    if config.block_schedule is not None:
        return config.block_schedule[completed_blocks]
    return select_block_size(
        config,
        remaining_bits=remaining_bits,
        remaining_tokens=remaining_tokens,
        entropy_bits=entropy_bits,
    )


class FhSparSampCodec:
    """SparSamp with a deterministic finite-horizon block controller."""

    def __init__(self, config: FhCodecConfig) -> None:
        self.config = config

    def encode(self, session: ProviderSession, bits: str, key: bytes) -> EncodeResult:
        """Embed a fixed public-length payload using adaptive block sizes."""

        if len(bits) != self.config.total_bits:
            raise ValueError(
                f"payload must contain exactly {self.config.total_bits} bits, got {len(bits)}"
            )
        if set(bits) - {"0", "1"}:
            raise ValueError("message must be a binary string")

        random_stream = HmacRandomStream(key, session.context_id)
        bit_offset = 0
        completed_blocks = 0
        active_size: int | None = None
        n_m = 0
        k_m = 0
        entropy_ema: float | None = None
        records: list[StepRecord] = []
        started = perf_counter()

        for step in range(self.config.max_tokens):
            snapshot = session.next_distribution()
            probabilities = _probabilities(snapshot, self.config.probability_quantum)
            entropy_ema = _update_entropy_ema(
                entropy_ema, snapshot.entropy_bits, self.config.entropy_ema_alpha
            )
            r = random_stream.fraction(step)
            embedded = snapshot.source_mass >= self.config.min_source_mass
            block_completed = False
            record_block_size = active_size

            if not embedded:
                if snapshot.native_token_id is not None:
                    token_id = snapshot.native_token_id
                else:
                    token_id = snapshot.candidates[_select(probabilities, r)].token_id
            else:
                if active_size is None:
                    active_size = _next_block_size(
                        self.config,
                        completed_blocks=completed_blocks,
                        remaining_bits=self.config.total_bits - bit_offset,
                        remaining_tokens=self.config.max_tokens - step,
                        entropy_bits=entropy_ema,
                    )
                    record_block_size = active_size
                    n_m = 1 << active_size
                    k_m = int(bits[bit_offset : bit_offset + active_size], 2)

                sample = (Fraction(k_m, n_m) + r) % 1
                candidate_index = _select(probabilities, sample)
                token_id = snapshot.candidates[candidate_index].token_id
                lower, upper = _bounds(probabilities, candidate_index)
                temp0 = _ceil_fraction((lower - r) * n_m)
                temp1 = _ceil_fraction((upper - r) * n_m)
                if k_m + r * n_m >= n_m:
                    k_m = k_m - n_m - temp0
                else:
                    k_m = k_m - temp0
                n_m = temp1 - temp0
                if n_m < 1:
                    raise ArithmeticError("sparse interval collapsed to zero")
                if n_m == 1:
                    block_completed = True
                    bit_offset += active_size
                    completed_blocks += 1
                    active_size = None

            session.append(token_id)
            records.append(
                StepRecord(
                    step=step,
                    token_id=token_id,
                    embedded=embedded,
                    block_completed=block_completed,
                    entropy_bits=snapshot.entropy_bits,
                    source_mass=snapshot.source_mass,
                    truncation_kl_nats=snapshot.truncation_kl_nats,
                    candidate_count=len(snapshot.candidates),
                    latency_ms=snapshot.latency_ms,
                    block_size=record_block_size,
                    completed_bits=bit_offset,
                    base_entropy_bits=snapshot.metadata.get("base_entropy_bits"),
                    effective_temperature=snapshot.metadata.get("effective_temperature"),
                    rescue_active=bool(snapshot.metadata.get("rescue_active", False)),
                    low_entropy_streak=int(snapshot.metadata.get("low_entropy_streak", 0)),
                )
            )

            if bit_offset == self.config.total_bits:
                return EncodeResult(
                    token_ids=session.generated_token_ids,
                    text=session.render(),
                    embedded_bits=self.config.total_bits,
                    padded_bits=0,
                    elapsed_seconds=perf_counter() - started,
                    records=tuple(records),
                )

        raise IncompleteEncodeError(
            f"message incomplete after {self.config.max_tokens} tokens; "
            "finite-horizon controller exhausted its public budget",
            token_ids=session.generated_token_ids,
            text=session.render(),
            completed_blocks=completed_blocks,
            total_blocks=(
                len(self.config.block_schedule) if self.config.block_schedule is not None else None
            ),
            completed_bits=bit_offset,
            elapsed_seconds=perf_counter() - started,
            records=tuple(records),
        )

    def decode(
        self,
        session: ProviderSession,
        token_ids: tuple[Hashable, ...] | list[Hashable],
        key: bytes,
    ) -> DecodeResult:
        """Recover adaptive blocks by replaying the finite-horizon controller."""

        random_stream = HmacRandomStream(key, session.context_id)
        bit_offset = 0
        active_size: int | None = None
        n_m = 0
        entropy_ema: float | None = None
        temp0_values: list[int] = []
        n_values: list[int] = []
        recovered: list[str] = []

        for step, observed_token_id in enumerate(token_ids):
            snapshot = session.next_distribution()
            probabilities = _probabilities(snapshot, self.config.probability_quantum)
            entropy_ema = _update_entropy_ema(
                entropy_ema, snapshot.entropy_bits, self.config.entropy_ema_alpha
            )
            embedded = snapshot.source_mass >= self.config.min_source_mass

            if embedded:
                if active_size is None:
                    active_size = _next_block_size(
                        self.config,
                        completed_blocks=len(recovered),
                        remaining_bits=self.config.total_bits - bit_offset,
                        remaining_tokens=self.config.max_tokens - step,
                        entropy_bits=entropy_ema,
                    )
                    n_m = 1 << active_size
                try:
                    candidate_index = next(
                        index
                        for index, candidate in enumerate(snapshot.candidates)
                        if candidate.token_id == observed_token_id
                    )
                except StopIteration as error:
                    raise ValueError(
                        f"observed token {observed_token_id!r} is absent at step {step}; "
                        "the model distribution or controller configuration changed"
                    ) from error
                r = random_stream.fraction(step)
                lower, upper = _bounds(probabilities, candidate_index)
                temp0 = _ceil_fraction((lower - r) * n_m)
                temp1 = _ceil_fraction((upper - r) * n_m)
                n_m = temp1 - temp0
                if n_m < 1:
                    raise ArithmeticError("decoder sparse interval collapsed to zero")
                temp0_values.append(temp0)
                n_values.append(n_m)

                if n_m == 1:
                    count = len(temp0_values) - 2
                    k_m = temp0_values[count + 1]
                    while count >= 0:
                        previous_n = n_values[count]
                        k_m = temp0_values[count] + ((k_m + previous_n) % previous_n)
                        count -= 1
                    modulus = 1 << active_size
                    k_m = (k_m + modulus) % modulus
                    recovered.append(f"{k_m:0{active_size}b}")
                    bit_offset += active_size
                    active_size = None
                    n_m = 0
                    temp0_values.clear()
                    n_values.clear()

            session.append(observed_token_id)
            if bit_offset == self.config.total_bits:
                return DecodeResult(
                    bits="".join(recovered),
                    completed_blocks=len(recovered),
                    consumed_tokens=step + 1,
                )

        return DecodeResult(
            bits="".join(recovered),
            completed_blocks=len(recovered),
            consumed_tokens=len(token_ids),
        )
