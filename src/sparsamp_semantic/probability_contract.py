"""Deterministic probability contracts for finite-precision replay."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal, localcontext
from fractions import Fraction
from math import inf, log
from typing import Any, Literal, Sequence


SupportStrategy = Literal["base", "waterfill"]


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


def support_feasible_mass_bits(candidate_count: int, headroom_bits: int = 0) -> int:
    """Return the smallest power-of-two mass width with public headroom."""

    if candidate_count < 1:
        raise ValueError("candidate_count must be positive")
    if headroom_bits < 0:
        raise ValueError("headroom_bits must be non-negative")
    mass_bits = max(1, (candidate_count - 1).bit_length()) + headroom_bits
    if mass_bits > 52:
        raise ValueError("support-feasible probability mass exceeds 52 bits")
    return mass_bits


def _waterfilled_support_target(
    normalized: tuple[Fraction, ...], total_mass: int
) -> tuple[Fraction, ...]:
    """Project Q onto r_i >= 1/M by minimizing KL(Q||R)."""

    positive = sorted(
        (index for index, value in enumerate(normalized) if value > 0),
        key=lambda index: (normalized[index], index),
    )
    if len(positive) > total_mass:
        raise ValueError("total integer mass is too small to preserve candidate support")
    epsilon = Fraction(1, total_mass)
    fixed_count = 0
    remaining_probability = sum(
        (normalized[index] for index in positive), start=Fraction(0)
    )
    while fixed_count < len(positive):
        remaining_mass = Fraction(total_mass - fixed_count, total_mass)
        scale = remaining_mass / remaining_probability
        smallest = positive[fixed_count]
        if scale * normalized[smallest] >= epsilon:
            break
        remaining_probability -= normalized[smallest]
        fixed_count += 1

    projected = [Fraction(0) for _ in normalized]
    for index in positive[:fixed_count]:
        projected[index] = epsilon
    if fixed_count < len(positive):
        remaining_mass = Fraction(total_mass - fixed_count, total_mass)
        scale = remaining_mass / remaining_probability
        for index in positive[fixed_count:]:
            projected[index] = scale * normalized[index]
    return tuple(projected)


def waterfilled_support_target(
    probabilities: Sequence[Any], *, mass_bits: int
) -> tuple[Fraction, ...]:
    """Return the exact continuous KL projection used before integer apportionment."""

    if not 1 <= mass_bits <= 52:
        raise ValueError("probability mass bits must lie in [1, 52]")
    return _waterfilled_support_target(_normalized(probabilities), 1 << mass_bits)


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


@dataclass(frozen=True)
class IntegerMassAudit:
    """Exact distance and floating-point KL summaries for one allocation."""

    total_variation: Fraction
    max_absolute_error: Fraction
    target_to_implemented_kl_nats: float
    implemented_to_target_kl_nats: float


def _kl_nats(source: Sequence[Fraction], target: Sequence[Fraction]) -> float:
    total = 0.0
    for source_value, target_value in zip(source, target, strict=True):
        if source_value == 0:
            continue
        if target_value == 0:
            return inf
        source_float = float(source_value)
        total += source_float * log(source_float / float(target_value))
    return total


def audit_integer_mass(
    probabilities: Sequence[Any], allocation: IntegerMassAllocation
) -> IntegerMassAudit:
    """Compare a normalized target with the allocation's implemented law."""

    target = _normalized(probabilities)
    implemented = allocation.probabilities
    if len(target) != len(implemented):
        raise ValueError("target and allocation must have equal length")
    errors = tuple(
        abs(target_value - implemented_value)
        for target_value, implemented_value in zip(target, implemented, strict=True)
    )
    return IntegerMassAudit(
        total_variation=sum(errors, start=Fraction(0)) / 2,
        max_absolute_error=max(errors, default=Fraction(0)),
        target_to_implemented_kl_nats=_kl_nats(target, implemented),
        implemented_to_target_kl_nats=_kl_nats(implemented, target),
    )


def support_preserving_tv_upper_bound(
    candidate_count: int, *, mass_bits: int
) -> Fraction:
    """Return a distribution-free TV bound for the legacy base allocation.

    For k positive candidates and M=2**mass_bits, the implementation reserves
    one count per candidate and apportions the remaining M-k counts by largest
    remainder. Each positive coordinate error is strictly below 2/M. Because
    at most k-1 coordinates can be positive when errors sum to zero, TV is
    strictly below 2(k-1)/M. The returned rational is a conservative upper
    bound; k=1 is exact.

    No analogous distribution-free KL bound is finite without a public lower
    bound on every target probability.
    """

    if candidate_count < 1:
        raise ValueError("candidate_count must be positive")
    if not 1 <= mass_bits <= 52:
        raise ValueError("probability mass bits must lie in [1, 52]")
    total_mass = 1 << mass_bits
    if candidate_count > total_mass:
        raise ValueError("total integer mass is too small to preserve candidate support")
    if candidate_count == 1:
        return Fraction(0)
    return Fraction(2 * (candidate_count - 1), total_mass)


def allocate_integer_mass(
    probabilities: Sequence[Any],
    *,
    mass_bits: int,
    preserve_support: bool = True,
    support_strategy: SupportStrategy = "base",
) -> IntegerMassAllocation:
    """Allocate 2**mass_bits counts with deterministic largest remainders.

    The legacy base strategy reserves one count per positive candidate before
    apportionment. The waterfill strategy first computes the continuous
    KL-minimizing lower-bounded target. Remainder ties follow candidate order.
    """

    if not 1 <= mass_bits <= 52:
        raise ValueError("probability mass bits must lie in [1, 52]")
    if support_strategy not in {"base", "waterfill"}:
        raise ValueError("support_strategy must be 'base' or 'waterfill'")
    normalized = _normalized(probabilities)
    total_mass = 1 << mass_bits
    positive = tuple(index for index, value in enumerate(normalized) if value > 0)
    if preserve_support and support_strategy == "waterfill":
        target = _waterfilled_support_target(normalized, total_mass)
        quotas = [value * total_mass for value in target]
        floors = [quota.numerator // quota.denominator for quota in quotas]
        counts = list(floors)
        residual = total_mass - sum(counts)
        remainders = [quota - floor for quota, floor in zip(quotas, floors, strict=True)]
        order = sorted(
            range(len(normalized)), key=lambda index: (-remainders[index], index)
        )
        for index in order[:residual]:
            counts[index] += 1
        return IntegerMassAllocation(
            counts=tuple(counts),
            total_mass=total_mass,
            preserve_support=True,
        )

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
    support_strategy: SupportStrategy = "base",
) -> tuple[Fraction, ...]:
    """Return exact probabilities induced by an integer mass allocation."""

    return allocate_integer_mass(
        probabilities,
        mass_bits=mass_bits,
        preserve_support=preserve_support,
        support_strategy=support_strategy,
    ).probabilities


def allocate_logit_bin_mass(
    token_ids: Sequence[int],
    logit_bins: Sequence[int],
    *,
    quantum: float,
    temperature: float,
    mass_bits: int,
) -> IntegerMassAllocation:
    """Map shared integer logit bins to deterministic power-of-two counts.

    Decimal exponentiation removes endpoint floating-point softmax from the
    probability contract. One count is reserved for every retained token; the
    remaining mass follows deterministic largest-remainder apportionment with
    token ID as the public tie breaker.
    """

    if not token_ids or len(token_ids) != len(logit_bins):
        raise ValueError("token IDs and logit bins must have equal positive length")
    if len(set(token_ids)) != len(token_ids):
        raise ValueError("token IDs must be unique")
    if quantum <= 0:
        raise ValueError("logit quantum must be positive")
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    if not 1 <= mass_bits <= 52:
        raise ValueError("probability mass bits must lie in [1, 52]")
    total_mass = 1 << mass_bits
    if len(token_ids) > total_mass:
        raise ValueError("total integer mass is too small to preserve candidate support")

    with localcontext() as context:
        context.prec = 80
        decimal_quantum = Decimal(str(quantum))
        decimal_temperature = Decimal(str(temperature))
        maximum_bin = max(logit_bins)
        weights = [
            ((Decimal(value - maximum_bin) * decimal_quantum) / decimal_temperature).exp()
            for value in logit_bins
        ]
        weight_sum = sum(weights, start=Decimal(0))
        remaining = total_mass - len(token_ids)
        quotas = [weight * remaining / weight_sum for weight in weights]
        floors = [
            int(quota.to_integral_value(rounding=ROUND_FLOOR)) for quota in quotas
        ]
        counts = [1 + value for value in floors]
        residual = total_mass - sum(counts)
        remainders = [quota - floor for quota, floor in zip(quotas, floors, strict=True)]
        order = sorted(
            range(len(token_ids)),
            key=lambda index: (-remainders[index], int(token_ids[index])),
        )
        for index in order[:residual]:
            counts[index] += 1

    return IntegerMassAllocation(
        counts=tuple(counts),
        total_mass=total_mass,
        preserve_support=True,
    )


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
    probability_mass_headroom_bits: int | None = None,
    probability_support_strategy: SupportStrategy = "base",
) -> None:
    """Validate mutually exclusive Decimal and integer probability contracts."""

    if probability_quantum is not None and Decimal(probability_quantum) <= 0:
        raise ValueError("probability quantum must be positive")
    if probability_mass_bits is not None and not 16 <= probability_mass_bits <= 52:
        raise ValueError("probability mass bits must lie in [16, 52]")
    if probability_mass_headroom_bits is not None and not 0 <= probability_mass_headroom_bits <= 51:
        raise ValueError("probability mass headroom bits must lie in [0, 51]")
    if probability_support_strategy not in {"base", "waterfill"}:
        raise ValueError("probability support strategy must be 'base' or 'waterfill'")
    enabled = sum(
        value is not None
        for value in (
            probability_quantum,
            probability_mass_bits,
            probability_mass_headroom_bits,
        )
    )
    if enabled > 1:
        raise ValueError(
            "probability quantum, integer mass bits, and adaptive headroom are mutually exclusive"
        )
