"""Model-independent SparSamp encoder and decoder."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
from time import perf_counter
from typing import Hashable

from .prf import HmacRandomStream
from .providers.base import ProviderSession
from .types import DistributionSnapshot


def _fraction_from_probability(probability: float) -> Fraction:
    return Fraction(Decimal(str(probability)))


def _ceil_fraction(value: Fraction) -> int:
    return -((-value.numerator) // value.denominator)


def _probabilities(snapshot: DistributionSnapshot, quantum: str | None) -> tuple[Fraction, ...]:
    probabilities = [_fraction_from_probability(item.probability) for item in snapshot.candidates]
    if quantum is not None:
        step = Fraction(Decimal(quantum))
        if step <= 0:
            raise ValueError("probability quantum must be positive")
        quantized: list[Fraction] = []
        for probability in probabilities:
            units = int(probability / step + Fraction(1, 2))
            quantized.append(max(step, units * step))
        probabilities = quantized
    total = sum(probabilities, start=Fraction(0))
    if total <= 0:
        raise ValueError("distribution has no probability mass")
    return tuple(probability / total for probability in probabilities)


def _bounds(probabilities: tuple[Fraction, ...], index: int) -> tuple[Fraction, Fraction]:
    lower = sum(probabilities[:index], start=Fraction(0))
    return lower, lower + probabilities[index]


def _select(probabilities: tuple[Fraction, ...], sample: Fraction) -> int:
    cumulative = Fraction(0)
    for index, probability in enumerate(probabilities):
        cumulative += probability
        if sample < cumulative or index == len(probabilities) - 1:
            return index
    raise AssertionError("unreachable inverse-CDF state")


@dataclass(frozen=True)
class CodecConfig:
    """SparSamp numerical and stopping configuration."""

    block_size: int = 32
    max_tokens: int = 2048
    min_source_mass: float = 0.0
    probability_quantum: str | None = "1e-15"

    def __post_init__(self) -> None:
        if self.block_size < 1:
            raise ValueError("block_size must be positive")
        if self.max_tokens < 1:
            raise ValueError("max_tokens must be positive")
        if not 0.0 <= self.min_source_mass <= 1.0:
            raise ValueError("min_source_mass must be in [0, 1]")


@dataclass(frozen=True)
class StepRecord:
    """Audit information for one generated token."""

    step: int
    token_id: Hashable
    embedded: bool
    block_completed: bool
    entropy_bits: float
    source_mass: float
    truncation_kl_nats: float
    candidate_count: int
    latency_ms: float


@dataclass(frozen=True)
class EncodeResult:
    """Encoded cover text, token sequence, and reproducibility metrics."""

    token_ids: tuple[Hashable, ...]
    text: str
    embedded_bits: int
    padded_bits: int
    elapsed_seconds: float
    records: tuple[StepRecord, ...] = field(default_factory=tuple)

    @property
    def bits_per_token(self) -> float:
        return self.embedded_bits / len(self.token_ids) if self.token_ids else 0.0

    @property
    def bits_per_second(self) -> float:
        return self.embedded_bits / self.elapsed_seconds if self.elapsed_seconds else 0.0

    @property
    def entropy_utilization(self) -> float:
        total_entropy = sum(record.entropy_bits for record in self.records if record.embedded)
        return self.embedded_bits / total_entropy if total_entropy else 0.0

    @property
    def truncation_kl_nats(self) -> float:
        return sum(record.truncation_kl_nats for record in self.records)


@dataclass(frozen=True)
class DecodeResult:
    """Recovered padded bit stream and block count."""

    bits: str
    completed_blocks: int
    consumed_tokens: int


class IncompleteEncodeError(RuntimeError):
    """Raised with partial progress when a payload misses the token budget."""

    def __init__(
        self,
        message: str,
        *,
        token_ids: tuple[Hashable, ...],
        text: str,
        completed_blocks: int,
        total_blocks: int,
        completed_bits: int,
        elapsed_seconds: float,
        records: tuple[StepRecord, ...],
    ) -> None:
        super().__init__(message)
        self.token_ids = token_ids
        self.text = text
        self.completed_blocks = completed_blocks
        self.total_blocks = total_blocks
        self.completed_bits = completed_bits
        self.elapsed_seconds = elapsed_seconds
        self.records = records


class SparSampCodec:
    """Encode and decode binary payloads against any deterministic provider session."""

    def __init__(self, config: CodecConfig | None = None) -> None:
        self.config = config or CodecConfig()

    def _pad(self, bits: str) -> tuple[str, int]:
        if set(bits) - {"0", "1"}:
            raise ValueError("message must be a binary string")
        padding = (-len(bits)) % self.config.block_size
        return bits + "0" * padding, padding

    def encode(self, session: ProviderSession, bits: str, key: bytes) -> EncodeResult:
        """Embed all bits into tokens generated from a fresh provider session."""

        padded, padding = self._pad(bits)
        if not padded:
            raise ValueError("cannot encode an empty message")
        blocks = [
            padded[index : index + self.config.block_size]
            for index in range(0, len(padded), self.config.block_size)
        ]
        random_stream = HmacRandomStream(key, session.context_id)
        block_index = 0
        n_m = 1 << self.config.block_size
        k_m = int(blocks[block_index], 2)
        records: list[StepRecord] = []
        started = perf_counter()

        for step in range(self.config.max_tokens):
            snapshot = session.next_distribution()
            probabilities = _probabilities(snapshot, self.config.probability_quantum)
            r = random_stream.fraction(step)
            embedded = snapshot.source_mass >= self.config.min_source_mass
            block_completed = False

            if not embedded:
                if snapshot.native_token_id is not None:
                    token_id = snapshot.native_token_id
                else:
                    token_id = snapshot.candidates[_select(probabilities, r)].token_id
            else:
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
                    block_index += 1

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
                )
            )

            if block_completed:
                if block_index == len(blocks):
                    elapsed = perf_counter() - started
                    return EncodeResult(
                        token_ids=session.generated_token_ids,
                        text=session.render(),
                        embedded_bits=len(bits),
                        padded_bits=padding,
                        elapsed_seconds=elapsed,
                        records=tuple(records),
                    )
                n_m = 1 << self.config.block_size
                k_m = int(blocks[block_index], 2)

        raise IncompleteEncodeError(
            f"message incomplete after {self.config.max_tokens} tokens; "
            "increase max_tokens or reduce the payload",
            token_ids=session.generated_token_ids,
            text=session.render(),
            completed_blocks=block_index,
            total_blocks=len(blocks),
            completed_bits=min(block_index * self.config.block_size, len(bits)),
            elapsed_seconds=perf_counter() - started,
            records=tuple(records),
        )

    def decode(
        self,
        session: ProviderSession,
        token_ids: tuple[Hashable, ...] | list[Hashable],
        key: bytes,
    ) -> DecodeResult:
        """Recover every complete message block from observed token IDs."""

        random_stream = HmacRandomStream(key, session.context_id)
        n_m = 1 << self.config.block_size
        temp0_values: list[int] = []
        n_values: list[int] = []
        recovered: list[str] = []

        for step, observed_token_id in enumerate(token_ids):
            snapshot = session.next_distribution()
            probabilities = _probabilities(snapshot, self.config.probability_quantum)
            embedded = snapshot.source_mass >= self.config.min_source_mass

            if embedded:
                try:
                    candidate_index = next(
                        index
                        for index, candidate in enumerate(snapshot.candidates)
                        if candidate.token_id == observed_token_id
                    )
                except StopIteration as error:
                    raise ValueError(
                        f"observed token {observed_token_id!r} is absent at step {step}; "
                        "the model distribution or tokenizer changed"
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
                    modulus = 1 << self.config.block_size
                    k_m = (k_m + modulus) % modulus
                    recovered.append(f"{k_m:0{self.config.block_size}b}")
                    n_m = modulus
                    temp0_values.clear()
                    n_values.clear()

            session.append(observed_token_id)

        return DecodeResult(
            bits="".join(recovered),
            completed_blocks=len(recovered),
            consumed_tokens=len(token_ids),
        )
