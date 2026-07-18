"""Deterministic probability contracts for finite-precision replay."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Any, Sequence


def _as_fraction(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, Decimal):
        return Fraction(value)
    return Fraction(Decimal(str(value)))


def _normalized(values: Sequence[Any]) -> tuple[Fraction, ...]:
    if not values:
        raise ValueError("probability distribution must not be empty")
    probabilities = tuple(_as_fraction(value) for value in values)
    if any(value < 0 for value in probabilities):
        raise ValueError("probabilities must be non-negative")
    total = sum(probabilities, start=Fraction(0))
    if total <= 0:
        raise ValueError("probability distribution must have positive mass")
    return tuple(value / total for value in probabilities)


@dataclass(frozen=True)
class IntegerMassAllocation:
    """Exact integer counts whose total is a public power-of-two mass."""

    counts: tuple[int, ...]
    total_mass: int
    preserve_support: bool

    def __post_init__(self) -> None:
        if not self.counts:
            raise ValueError("integer mass allocation must not be empty")
        if self.total_mass < 1:
            raise ValueError("total_mass must be positive")
        if any(count < 0 for count in self.counts):
            raise ValueError("integer counts must be non-negative")
        if sum(self.counts) != self.total_mass:
            raise ValueError("integer counts must sum to total_mass")

    @property
    def probabilities(self) -> tuple[Fraction, ...]:
        return tuple(Fraction(count, self.total_mass) for count in self.counts)


def allocate_integer_mass(
    probabilities: Sequence[Any],
    *,
    mass_bits: int,
    preserve_support: bool = True,
) -> IntegerMassAllocation:
    """Allocate 2**mass_bits counts with deterministic largest remainders.

    Positive candidates receive one base count when preserve_support is enabled.
    Remaining counts are apportioned by normalized probability, with ties broken
    by the original candidate order.
    """

    if not 16 <= mass_bits <= 52:
        raise ValueError("probability mass bits must lie in [16, 52]")
    normalized = _normalized(probabilities)
    total_mass = 1 << mass_bits
    positive = tuple(index for index, value in enumerate(normalized) if value > 0)
    base_count = 1 if preserve_support else 0
    required = base_count * len(positive)
    if required > total_mass:
        raise ValueError("total integer mass is too small to preserve candidate support")

    counts = [base_count if value > 0 else 0 for value in normalized]
    remaining = total_mass - required
    quotas = [value * remaining for value in normalized]
    floors = [quota.numerator // quota.denominator for quota in quotas]
    for index, floor in enumerate(floors):
        counts[index] += floor

    residual = total_mass - sum(counts)
    remainders = [quota - floor for quota, floor in zip(quotas, floors, strict=True)]
    order = sorted(range(len(normalized)), key=lambda index: (-remainders[index], index))
    for index in order[:residual]:
        counts[index] += 1

    return IntegerMassAllocation(
        counts=tuple(counts),
        total_mass=total_mass,
        preserve_support=preserve_support,
    )


def integer_mass_probabilities(
    probabilities: Sequence[Any],
    *,
    mass_bits: int,
    preserve_support: bool = True,
) -> tuple[Fraction, ...]:
    """Return exact probabilities induced by an integer mass allocation."""

    return allocate_integer_mass(
        probabilities,
        mass_bits=mass_bits,
        preserve_support=preserve_support,
    ).probabilities


def decimal_quantized_probabilities(
    probabilities: Sequence[Any], quantum: str | None
) -> tuple[Fraction, ...]:
    """Match the legacy Fraction-based Decimal quantum contract."""

    normalized = _normalized(probabilities)
    if quantum is not None:
        step = Fraction(Decimal(quantum))
        if step <= 0:
            raise ValueError("probability quantum must be positive")
        quantized = []
        for probability in normalized:
            units = int(probability / step + Fraction(1, 2))
            quantized.append(max(step, units * step))
        normalized = _normalized(quantized)
    return normalized


def validate_probability_contract(
    probability_quantum: str | None,
    probability_mass_bits: int | None,
) -> None:
    """Validate mutually exclusive Decimal and integer probability contracts."""

    if probability_quantum is not None and Decimal(probability_quantum) <= 0:
        raise ValueError("probability quantum must be positive")
    if probability_mass_bits is not None and not 16 <= probability_mass_bits <= 52:
        raise ValueError("probability mass bits must lie in [16, 52]")
    if probability_quantum is not None and probability_mass_bits is not None:
        raise ValueError("probability quantum and integer mass bits are mutually exclusive")
