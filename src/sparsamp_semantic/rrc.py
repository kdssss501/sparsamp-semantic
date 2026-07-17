"""Clean-room implementation of rotation range-coding steganography."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_DOWN, localcontext
from math import ceil, log10
from time import perf_counter
from typing import Hashable

from .core import DecodeResult, EncodeResult, IncompleteEncodeError, StepRecord
from .prf import HmacRandomStream
from .providers.base import ProviderSession
from .types import DistributionSnapshot


def _positive_mod(value: Decimal, modulus: Decimal) -> Decimal:
    remainder = value % modulus
    return remainder + modulus if remainder < 0 else remainder


def _decimal_probabilities(
    snapshot: DistributionSnapshot, quantum: str | None
) -> tuple[Decimal, ...]:
    probabilities = [Decimal(str(item.probability)) for item in snapshot.candidates]
    if quantum is not None:
        step = Decimal(quantum)
        if step <= 0:
            raise ValueError("probability quantum must be positive")
        probabilities = [max(step, value.quantize(step)) for value in probabilities]
    total = sum(probabilities, start=Decimal(0))
    if total <= 0:
        raise ValueError("distribution has no probability mass")
    return tuple(value / total for value in probabilities)


def _select_interval(
    probabilities: tuple[Decimal, ...], position: Decimal
) -> tuple[int, Decimal, Decimal]:
    lower = Decimal(0)
    for index, probability in enumerate(probabilities):
        upper = Decimal(1) if index == len(probabilities) - 1 else lower + probability
        if position < upper or index == len(probabilities) - 1:
            return index, lower, upper
        lower = upper
    raise AssertionError("unreachable range-coding selection state")


def _observed_interval(
    snapshot: DistributionSnapshot,
    probabilities: tuple[Decimal, ...],
    observed_token_id: Hashable,
    step: int,
) -> tuple[Decimal, Decimal]:
    lower = Decimal(0)
    for index, (candidate, probability) in enumerate(
        zip(snapshot.candidates, probabilities, strict=True)
    ):
        upper = Decimal(1) if index == len(probabilities) - 1 else lower + probability
        if candidate.token_id == observed_token_id:
            return lower, upper
        lower = upper
    raise ValueError(
        f"observed token {observed_token_id!r} is absent at step {step}; "
        "the model distribution or tokenizer changed"
    )


@dataclass(frozen=True)
class RrcConfig:
    """Numerical and stopping configuration for rotation range coding."""

    message_bits: int
    max_tokens: int = 2048
    probability_quantum: str | None = "1e-15"
    guard_digits: int = 24
    min_precision: int = 48

    def __post_init__(self) -> None:
        if self.message_bits < 1:
            raise ValueError("message_bits must be positive")
        if self.max_tokens < 1:
            raise ValueError("max_tokens must be positive")
        if self.guard_digits < 8:
            raise ValueError("guard_digits must be at least 8")
        if self.min_precision < 16:
            raise ValueError("min_precision must be at least 16")
        if self.probability_quantum is not None and Decimal(self.probability_quantum) <= 0:
            raise ValueError("probability quantum must be positive")

    @property
    def decimal_precision(self) -> int:
        integer_digits = ceil(self.message_bits * log10(2)) + 1
        return max(self.min_precision, integer_digits + self.guard_digits)


class RotationRangeCodec:
    """Embed one fixed-length payload with per-step keyed interval rotation."""

    def __init__(self, config: RrcConfig) -> None:
        self.config = config

    def _validate_bits(self, bits: str) -> None:
        if len(bits) != self.config.message_bits:
            raise ValueError(f"message must contain exactly {self.config.message_bits} bits")
        if set(bits) - {"0", "1"}:
            raise ValueError("message must be a binary string")

    def encode(self, session: ProviderSession, bits: str, key: bytes) -> EncodeResult:
        """Embed a fixed-length bit string using Algorithm 3 from Yan and Murawaki."""

        self._validate_bits(bits)
        random_stream = HmacRandomStream(key, session.context_id)
        records: list[StepRecord] = []
        started = perf_counter()

        with localcontext() as context:
            context.prec = self.config.decimal_precision
            left = Decimal(0)
            right = Decimal(1 << self.config.message_bits)
            secret = Decimal(int(bits, 2))
            half = Decimal("0.5")

            for step in range(self.config.max_tokens):
                snapshot = session.next_distribution()
                probabilities = _decimal_probabilities(
                    snapshot, self.config.probability_quantum
                )
                width = right - left
                if width <= 0:
                    raise ArithmeticError("range-coding interval collapsed to zero")
                offset_fraction = random_stream.fraction(step, domain=b"rrc")
                offset = Decimal(offset_fraction.numerator) / Decimal(offset_fraction.denominator)
                secret = left + _positive_mod(secret - left + offset * width, width)
                position = (secret - left) / width
                candidate_index, lower_probability, upper_probability = _select_interval(
                    probabilities, position
                )
                old_left = left
                left = old_left + width * lower_probability
                right = old_left + width * upper_probability
                token_id = snapshot.candidates[candidate_index].token_id
                midpoint_delta = (left + right) / 2 - secret
                completed = -half < midpoint_delta <= half
                session.append(token_id)
                records.append(
                    StepRecord(
                        step=step,
                        token_id=token_id,
                        embedded=True,
                        block_completed=completed,
                        entropy_bits=snapshot.entropy_bits,
                        source_mass=snapshot.source_mass,
                        truncation_kl_nats=snapshot.truncation_kl_nats,
                        candidate_count=len(snapshot.candidates),
                        latency_ms=snapshot.latency_ms,
                        block_size=self.config.message_bits,
                        completed_bits=self.config.message_bits if completed else 0,
                    )
                )
                if completed:
                    return EncodeResult(
                        token_ids=session.generated_token_ids,
                        text=session.render(),
                        embedded_bits=self.config.message_bits,
                        padded_bits=0,
                        elapsed_seconds=perf_counter() - started,
                        records=tuple(records),
                    )

        raise IncompleteEncodeError(
            f"RRC message incomplete after {self.config.max_tokens} tokens; "
            "increase max_tokens or reduce the payload",
            token_ids=session.generated_token_ids,
            text=session.render(),
            completed_blocks=0,
            total_blocks=1,
            completed_bits=0,
            elapsed_seconds=perf_counter() - started,
            records=tuple(records),
        )

    def decode(
        self,
        session: ProviderSession,
        token_ids: tuple[Hashable, ...] | list[Hashable],
        key: bytes,
    ) -> DecodeResult:
        """Recover a fixed-length bit string using reverse interval rotations."""

        if not token_ids:
            raise ValueError("RRC decoding requires at least one token")
        random_stream = HmacRandomStream(key, session.context_id)

        with localcontext() as context:
            context.prec = self.config.decimal_precision
            left = Decimal(0)
            right = Decimal(1 << self.config.message_bits)
            history: list[tuple[Decimal, Decimal]] = []

            for step, observed_token_id in enumerate(token_ids):
                snapshot = session.next_distribution()
                probabilities = _decimal_probabilities(
                    snapshot, self.config.probability_quantum
                )
                width = right - left
                if width <= 0:
                    raise ArithmeticError("decoder range-coding interval collapsed to zero")
                history.append((left, right))
                lower_probability, upper_probability = _observed_interval(
                    snapshot, probabilities, observed_token_id, step
                )
                old_left = left
                left = old_left + width * lower_probability
                right = old_left + width * upper_probability
                session.append(observed_token_id)

            midpoint = (left + right) / 2
            for step in range(len(history) - 1, -1, -1):
                previous_left, previous_right = history[step]
                width = previous_right - previous_left
                offset_fraction = random_stream.fraction(step, domain=b"rrc")
                offset = Decimal(offset_fraction.numerator) / Decimal(offset_fraction.denominator)
                midpoint = previous_left + _positive_mod(
                    midpoint - previous_left - offset * width, width
                )

            secret = int(midpoint.to_integral_value(rounding=ROUND_HALF_DOWN))
            if not 0 <= secret < 1 << self.config.message_bits:
                raise ArithmeticError("decoded RRC value falls outside the message interval")
            return DecodeResult(
                bits=f"{secret:0{self.config.message_bits}b}",
                completed_blocks=1,
                consumed_tokens=len(token_ids),
            )
