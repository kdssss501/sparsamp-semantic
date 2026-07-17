"""Mathematical audit helpers for rotation range-coding proofs."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import log


def positive_mod(value: Fraction, modulus: Fraction) -> Fraction:
    """Return the representative of value modulo modulus in [0, modulus)."""

    if modulus <= 0:
        raise ValueError("modulus must be positive")
    return value - (value // modulus) * modulus


def rotate(
    value: Fraction,
    left: Fraction,
    right: Fraction,
    offset: Fraction,
) -> Fraction:
    """Apply one RRC rotation with an offset expressed as a fraction of interval width."""

    if not left <= value < right:
        raise ValueError("value must lie in the rotation interval")
    if not 0 <= offset < 1:
        raise ValueError("offset must lie in [0, 1)")
    width = right - left
    return left + positive_mod(value - left + offset * width, width)


def inverse_rotate(
    value: Fraction,
    left: Fraction,
    right: Fraction,
    offset: Fraction,
) -> Fraction:
    """Invert one RRC rotation exactly over rational numbers."""

    if not left <= value < right:
        raise ValueError("value must lie in the rotation interval")
    if not 0 <= offset < 1:
        raise ValueError("offset must lie in [0, 1)")
    width = right - left
    return left + positive_mod(value - left - offset * width, width)


def round_half_down(value: Fraction) -> int:
    """Round a non-negative rational to nearest integer, resolving ties downward."""

    if value < 0:
        raise ValueError("RRC message coordinates must be non-negative")
    lower = value.numerator // value.denominator
    remainder = value - lower
    return lower + int(remainder > Fraction(1, 2))


def reverse_midpoint(
    midpoint: Fraction,
    previous_intervals: tuple[tuple[Fraction, Fraction], ...],
    offsets: tuple[Fraction, ...],
) -> Fraction:
    """Replay Algorithm 4's reverse rotations exactly."""

    if len(previous_intervals) != len(offsets):
        raise ValueError("one interval and offset are required for every generated token")
    for (left, right), offset in reversed(tuple(zip(previous_intervals, offsets, strict=True))):
        midpoint = inverse_rotate(midpoint, left, right, offset)
    return midpoint


def verified_stop(
    message: int,
    midpoint: Fraction,
    previous_intervals: tuple[tuple[Fraction, Fraction], ...],
    offsets: tuple[Fraction, ...],
) -> bool:
    """Return whether the public decoder applied now would recover message exactly."""

    return round_half_down(reverse_midpoint(midpoint, previous_intervals, offsets)) == message


def same_inverse_branch(
    first: Fraction,
    second: Fraction,
    left: Fraction,
    right: Fraction,
    offset: Fraction,
) -> bool:
    """Return whether two points avoid the linear cut of one inverse rotation."""

    if not left <= first < right or not left <= second < right:
        return False
    if not 0 <= offset < 1:
        raise ValueError("offset must lie in [0, 1)")
    if offset == 0:
        return True
    cut = left + offset * (right - left)
    return (first < cut) == (second < cut)


def no_wrap_recovery_certificate(
    message: int,
    secret_path: tuple[Fraction, ...],
    midpoint: Fraction,
    previous_intervals: tuple[tuple[Fraction, Fraction], ...],
    offsets: tuple[Fraction, ...],
) -> bool:
    """Check a sufficient certificate for preserving linear midpoint error."""

    if len(secret_path) != len(previous_intervals) or len(secret_path) != len(offsets):
        raise ValueError("secret path, interval history, and offsets must have equal length")
    if not secret_path:
        raise ValueError("the certificate requires at least one rotation")

    previous_secret = Fraction(message)
    for secret, (left, right), offset in zip(
        secret_path, previous_intervals, offsets, strict=True
    ):
        if rotate(previous_secret, left, right, offset) != secret:
            return False
        previous_secret = secret

    error = midpoint - secret_path[-1]
    if round_half_down(Fraction(message) + error) != message:
        return False
    for secret, (left, right), offset in reversed(
        tuple(zip(secret_path, previous_intervals, offsets, strict=True))
    ):
        displaced = secret + error
        if not same_inverse_branch(secret, displaced, left, right, offset):
            return False
    return True


@dataclass(frozen=True)
class KLDecomposition:
    """KL terms induced by support truncation and probability quantization."""

    source_mass: Fraction
    truncation_kl_nats: float
    quantization_kl_nats: float
    total_kl_nats: float


def kl_divergence_nats(
    distribution: tuple[Fraction, ...], reference: tuple[Fraction, ...]
) -> float:
    """Return KL(distribution||reference), including infinite support mismatch."""

    _validate_distribution(distribution, "distribution")
    _validate_distribution(reference, "reference distribution")
    if len(distribution) != len(reference):
        raise ValueError("KL distributions must have equal length")
    result = 0.0
    for probability, reference_probability in zip(distribution, reference, strict=True):
        if probability == 0:
            continue
        if reference_probability == 0:
            return float("inf")
        probability_float = float(probability)
        result += probability_float * log(probability_float / float(reference_probability))
    return result


def _validate_distribution(probabilities: tuple[Fraction, ...], name: str) -> None:
    if not probabilities:
        raise ValueError(f"{name} must not be empty")
    if any(probability < 0 for probability in probabilities):
        raise ValueError(f"{name} must be non-negative")
    if sum(probabilities, start=Fraction(0)) != 1:
        raise ValueError(f"{name} must sum to one exactly")


def kl_truncation_quantization_decomposition(
    source: tuple[Fraction, ...],
    retained_indices: tuple[int, ...],
    implemented: tuple[Fraction, ...],
) -> KLDecomposition:
    """Compute KL(R||P) = -log(Z) + KL(R||Q) on retained support."""

    _validate_distribution(source, "source distribution")
    _validate_distribution(implemented, "implemented distribution")
    if len(retained_indices) != len(implemented):
        raise ValueError("one implemented probability is required per retained index")
    if len(set(retained_indices)) != len(retained_indices):
        raise ValueError("retained indices must be unique")
    if any(index < 0 or index >= len(source) for index in retained_indices):
        raise ValueError("retained index is outside the source distribution")

    retained_source = tuple(source[index] for index in retained_indices)
    source_mass = sum(retained_source, start=Fraction(0))
    if source_mass <= 0:
        raise ValueError("retained support must have positive source mass")
    conditioned = tuple(probability / source_mass for probability in retained_source)

    quantization_kl = 0.0
    total_kl = 0.0
    for implemented_probability, conditioned_probability, source_probability in zip(
        implemented, conditioned, retained_source, strict=True
    ):
        if implemented_probability == 0:
            continue
        if conditioned_probability <= 0 or source_probability <= 0:
            raise ValueError("implemented support must be absolutely continuous under source")
        implemented_float = float(implemented_probability)
        quantization_kl += implemented_float * log(
            implemented_float / float(conditioned_probability)
        )
        total_kl += implemented_float * log(implemented_float / float(source_probability))

    return KLDecomposition(
        source_mass=source_mass,
        truncation_kl_nats=-log(float(source_mass)),
        quantization_kl_nats=quantization_kl,
        total_kl_nats=total_kl,
    )


@dataclass(frozen=True)
class StoppingLeakCounterexample:
    """A stopped fair-coin process whose distribution differs from length-matched cover."""

    stego_distribution: tuple[tuple[tuple[int, ...], Fraction], ...]
    cover_distribution: tuple[tuple[tuple[int, ...], Fraction], ...]
    stego_length_distribution: tuple[tuple[int, Fraction], ...]
    cover_length_distribution: tuple[tuple[int, Fraction], ...]
    witness_event_stego_probability: Fraction
    witness_event_cover_probability: Fraction
    witness_advantage: Fraction
    total_variation: Fraction


def stopped_process_counterexample() -> StoppingLeakCounterexample:
    """Show that matching active-step conditionals and length marginals is insufficient."""

    stego = (
        ((0,), Fraction(1, 2)),
        ((1, 0), Fraction(1, 4)),
        ((1, 1), Fraction(1, 4)),
    )
    cover = (
        ((0,), Fraction(1, 4)),
        ((1,), Fraction(1, 4)),
        ((0, 0), Fraction(1, 8)),
        ((0, 1), Fraction(1, 8)),
        ((1, 0), Fraction(1, 8)),
        ((1, 1), Fraction(1, 8)),
    )
    support = {sequence for sequence, _ in stego} | {sequence for sequence, _ in cover}
    stego_map = dict(stego)
    cover_map = dict(cover)
    total_variation = sum(
        abs(stego_map.get(sequence, Fraction(0)) - cover_map.get(sequence, Fraction(0)))
        for sequence in support
    ) / 2
    stego_witness = stego_map[(0,)]
    cover_witness = cover_map[(0,)]
    return StoppingLeakCounterexample(
        stego_distribution=stego,
        cover_distribution=cover,
        stego_length_distribution=((1, Fraction(1, 2)), (2, Fraction(1, 2))),
        cover_length_distribution=((1, Fraction(1, 2)), (2, Fraction(1, 2))),
        witness_event_stego_probability=stego_witness,
        witness_event_cover_probability=cover_witness,
        witness_advantage=abs(stego_witness - cover_witness),
        total_variation=total_variation,
    )


def authentication_false_acceptance_bound(candidate_checks: int, tag_bits: int) -> Fraction:
    """Return the union bound for ideal independent tag checks."""

    if candidate_checks < 0:
        raise ValueError("candidate_checks must be non-negative")
    if tag_bits < 1:
        raise ValueError("tag_bits must be positive")
    return min(Fraction(1), Fraction(candidate_checks, 1 << tag_bits))


@dataclass(frozen=True)
class PaperStopCounterexample:
    """A two-step exact counterexample to the paper's local stopping implication."""

    message: int
    initial_interval: tuple[Fraction, Fraction]
    first_token_interval: tuple[Fraction, Fraction]
    final_token_interval: tuple[Fraction, Fraction]
    offsets: tuple[Fraction, Fraction]
    rotated_secrets: tuple[Fraction, Fraction]
    final_midpoint: Fraction
    paper_midpoint_error: Fraction
    decoded_midpoint: Fraction
    decoded_message: int


@dataclass(frozen=True)
class PaperFailureRegion:
    """A positive-measure rectangle of offsets producing the same decoding failure."""

    first_offset_range: tuple[Fraction, Fraction]
    second_offset_range: tuple[Fraction, Fraction]
    first_secret_range: tuple[Fraction, Fraction]
    second_secret_range: tuple[Fraction, Fraction]
    midpoint_error_range: tuple[Fraction, Fraction]
    first_reverse_range: tuple[Fraction, Fraction]
    decoded_midpoint_range: tuple[Fraction, Fraction]
    decoded_message: int
    probability_lower_bound: Fraction


def paper_stop_counterexample() -> PaperStopCounterexample:
    """Construct an exact l=3 example where Algorithm 3 stops but Algorithm 4 fails."""

    initial = (Fraction(0), Fraction(8))
    first = (Fraction(3), Fraction(5))
    final = (Fraction(3), Fraction(9, 2))
    offsets = (Fraction(0), Fraction(1, 2))
    message = 3
    first_secret = rotate(Fraction(message), *initial, offsets[0])
    second_secret = rotate(first_secret, *first, offsets[1])
    midpoint = sum(final, start=Fraction(0)) / 2
    decoded_midpoint = reverse_midpoint(midpoint, (initial, first), offsets)
    return PaperStopCounterexample(
        message=message,
        initial_interval=initial,
        first_token_interval=first,
        final_token_interval=final,
        offsets=offsets,
        rotated_secrets=(first_secret, second_secret),
        final_midpoint=midpoint,
        paper_midpoint_error=midpoint - second_secret,
        decoded_midpoint=decoded_midpoint,
        decoded_message=round_half_down(decoded_midpoint),
    )


def paper_failure_region() -> PaperFailureRegion:
    """Return a positive-measure offset region around the exact counterexample."""

    first = (Fraction(0), Fraction(1, 64))
    second = (Fraction(15, 32), Fraction(17, 32))
    return PaperFailureRegion(
        first_offset_range=first,
        second_offset_range=second,
        first_secret_range=(Fraction(3), Fraction(25, 8)),
        second_secret_range=(Fraction(63, 16), Fraction(67, 16)),
        midpoint_error_range=(Fraction(-7, 16), Fraction(-3, 16)),
        first_reverse_range=(Fraction(75, 16), Fraction(77, 16)),
        decoded_midpoint_range=(Fraction(73, 16), Fraction(77, 16)),
        decoded_message=5,
        probability_lower_bound=(first[1] - first[0]) * (second[1] - second[0]),
    )
