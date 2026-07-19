"""Byte-sliced SparSamp with outer Reed-Solomon correction (R029)."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from time import perf_counter
from typing import Hashable

from .core import _bounds, _ceil_fraction, _probabilities, _select
from .microframe import _distance_to_integer
from .prf import HmacRandomStream
from .probability_contract import SupportStrategy
from .providers.base import ProviderSession


@dataclass(frozen=True)
class ByteSlicedConfig:
    """Fixed-window configuration for one 8-bit codeword symbol per window."""

    window_tokens: int = 8
    parity_bytes: int = 2
    probability_quantum: str | None = "1e-15"
    probability_mass_bits: int | None = None
    probability_mass_headroom_bits: int | None = None
    probability_support_strategy: SupportStrategy = "base"
    preserve_probability_support: bool = True
    cdf_uncertainty_bound: float = 0.0

    def __post_init__(self) -> None:
        if self.window_tokens < 1:
            raise ValueError("window_tokens must be positive")
        if not 0 <= self.parity_bytes <= 255:
            raise ValueError("parity_bytes must be in [0, 255]")
        if not 0.0 <= self.cdf_uncertainty_bound <= 1.0:
            raise ValueError("cdf_uncertainty_bound must be in [0, 1]")
        from .probability_contract import validate_probability_contract

        validate_probability_contract(
            self.probability_quantum,
            self.probability_mass_bits,
            self.probability_mass_headroom_bits,
            self.probability_support_strategy,
        )


@dataclass(frozen=True)
class ByteFrameRecord:
    window_index: int
    token_start: int
    token_end: int
    completed: bool
    recovered_symbol: int | None
    erasure_reason: str | None
    singleton_step: int | None
    guard_aborted: bool = False
    minimum_interval_margin_units: float | None = None
    required_interval_margin_units: float | None = None


@dataclass(frozen=True)
class ByteSlicedEncodeResult:
    token_ids: tuple[Hashable, ...]
    text: str
    payload_bytes: bytes
    codeword_bytes: bytes
    elapsed_seconds: float
    records: tuple[ByteFrameRecord, ...] = field(default_factory=tuple)

    @property
    def payload_bits_per_token(self) -> float:
        return len(self.payload_bytes) * 8 / len(self.token_ids) if self.token_ids else 0.0

    @property
    def codeword_bits_per_token(self) -> float:
        return len(self.codeword_bytes) * 8 / len(self.token_ids) if self.token_ids else 0.0


@dataclass(frozen=True)
class ByteSlicedDecodeResult:
    payload_bytes: bytes | None
    corrected_codeword: bytes | None
    records: tuple[ByteFrameRecord, ...]
    consumed_tokens: int
    erasure_count: int
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.payload_bytes is not None and self.error is None


class ByteSlicedCodec:
    """Embed one byte per independent window and correct symbols with RS.

    The codec intentionally has no per-window authentication bits.  Callers
    should authenticate the recovered payload with ``PayloadCodec`` or an
    equivalent AEAD/MAC after RS decoding.
    """

    def __init__(self, config: ByteSlicedConfig | None = None) -> None:
        self.config = config or ByteSlicedConfig()

    def _codeword(self, payload: bytes) -> bytes:
        if not payload:
            raise ValueError("payload must not be empty")
        if len(payload) + self.config.parity_bytes > 255:
            raise ValueError("RS codeword must contain at most 255 bytes")
        if self.config.parity_bytes == 0:
            return payload
        try:
            from reedsolo import RSCodec
        except ImportError as error:
            raise RuntimeError("parity_bytes requires the optional 'reedsolo' package") from error
        return bytes(RSCodec(self.config.parity_bytes).encode(payload))

    @staticmethod
    def _domain(window_index: int) -> bytes:
        return b"sparsamp-r029-byte-window\0" + window_index.to_bytes(8, "big")

    @staticmethod
    def _native_or_sample(snapshot, probabilities, sample: Fraction):
        if snapshot.native_token_id is not None:
            return snapshot.native_token_id
        return snapshot.candidates[_select(probabilities, sample)].token_id

    def encode(
        self, session: ProviderSession, payload: bytes, key: bytes
    ) -> ByteSlicedEncodeResult:
        codeword = self._codeword(payload)
        stream = HmacRandomStream(key, session.context_id)
        records: list[ByteFrameRecord] = []
        started = perf_counter()
        for window_index, symbol in enumerate(codeword):
            n_m = 1 << 8
            k_m = symbol
            singleton_step: int | None = None
            reason: str | None = None
            guard_aborted = False
            minimum_margin: Fraction | None = None
            maximum_required: Fraction | None = None
            window_start = len(session.generated_token_ids)
            for local_step in range(self.config.window_tokens):
                snapshot = session.next_distribution()
                probabilities = _probabilities(
                    snapshot,
                    self.config.probability_quantum,
                    self.config.probability_mass_bits,
                    self.config.preserve_probability_support,
                    self.config.probability_mass_headroom_bits,
                    self.config.probability_support_strategy,
                )
                r = stream.fraction(local_step, domain=self._domain(window_index))
                if singleton_step is not None or reason is not None:
                    session.append(self._native_or_sample(snapshot, probabilities, r))
                    continue
                try:
                    sample = (Fraction(k_m, n_m) + r) % 1
                    candidate_index = _select(probabilities, sample)
                    token_id = snapshot.candidates[candidate_index].token_id
                    lower, upper = _bounds(probabilities, candidate_index)
                    lower_lattice = (lower - r) * n_m
                    upper_lattice = (upper - r) * n_m
                    margin = min(
                        _distance_to_integer(lower_lattice),
                        _distance_to_integer(upper_lattice),
                    )
                    required = Fraction(str(self.config.cdf_uncertainty_bound)) * n_m
                    minimum_margin = margin if minimum_margin is None else min(minimum_margin, margin)
                    maximum_required = (
                        required if maximum_required is None else max(maximum_required, required)
                    )
                    if self.config.cdf_uncertainty_bound > 0 and margin <= required:
                        reason = "interval_guard_aborted"
                        guard_aborted = True
                        session.append(self._native_or_sample(snapshot, probabilities, r))
                        continue
                    temp0 = _ceil_fraction((lower - r) * n_m)
                    temp1 = _ceil_fraction((upper - r) * n_m)
                    k_m = k_m - n_m - temp0 if k_m + r * n_m >= n_m else k_m - temp0
                    n_m = temp1 - temp0
                    if n_m < 1:
                        raise ArithmeticError("sparse interval collapsed to zero")
                    session.append(token_id)
                    if n_m == 1:
                        singleton_step = local_step
                except (ArithmeticError, IndexError, ValueError) as error:
                    reason = type(error).__name__
                    session.append(self._native_or_sample(snapshot, probabilities, r))
            records.append(
                ByteFrameRecord(
                    window_index=window_index,
                    token_start=window_start,
                    token_end=len(session.generated_token_ids),
                    completed=singleton_step is not None,
                    recovered_symbol=symbol if singleton_step is not None else None,
                    erasure_reason=reason if singleton_step is None else None,
                    singleton_step=singleton_step,
                    guard_aborted=guard_aborted,
                    minimum_interval_margin_units=(
                        float(minimum_margin) if minimum_margin is not None else None
                    ),
                    required_interval_margin_units=(
                        float(maximum_required) if maximum_required is not None else None
                    ),
                )
            )
        return ByteSlicedEncodeResult(
            token_ids=session.generated_token_ids,
            text=session.render(),
            payload_bytes=payload,
            codeword_bytes=codeword,
            elapsed_seconds=perf_counter() - started,
            records=tuple(records),
        )

    def decode(
        self, session: ProviderSession, token_ids: tuple[Hashable, ...] | list[Hashable], key: bytes
    ) -> ByteSlicedDecodeResult:
        window_count = (len(token_ids) + self.config.window_tokens - 1) // self.config.window_tokens
        stream = HmacRandomStream(key, session.context_id)
        records: list[ByteFrameRecord] = []
        symbols: list[int] = []
        erasures: list[int] = []
        consumed = 0
        for window_index in range(window_count):
            n_m = 1 << 8
            temp0_values: list[int] = []
            n_values: list[int] = []
            recovered: int | None = None
            singleton_step: int | None = None
            reason: str | None = None
            window_start = consumed
            for local_step in range(self.config.window_tokens):
                if consumed >= len(token_ids):
                    reason = reason or "short_window"
                    break
                observed = token_ids[consumed]
                snapshot = session.next_distribution()
                probabilities = _probabilities(
                    snapshot,
                    self.config.probability_quantum,
                    self.config.probability_mass_bits,
                    self.config.preserve_probability_support,
                    self.config.probability_mass_headroom_bits,
                    self.config.probability_support_strategy,
                )
                if singleton_step is None and reason is None:
                    try:
                        candidate_index = next(
                            index
                            for index, candidate in enumerate(snapshot.candidates)
                            if candidate.token_id == observed
                        )
                        r = stream.fraction(local_step, domain=self._domain(window_index))
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
                            value = temp0_values[count + 1]
                            while count >= 0:
                                previous_n = n_values[count]
                                value = temp0_values[count] + ((value + previous_n) % previous_n)
                                count -= 1
                            recovered = value % 256
                            singleton_step = local_step
                    except (StopIteration, ArithmeticError, IndexError, ValueError) as error:
                        reason = type(error).__name__
                try:
                    session.append(observed)
                except ValueError as error:
                    return ByteSlicedDecodeResult(
                        None, None, tuple(records), consumed, len(erasures) + 1, str(error)
                    )
                consumed += 1
            if recovered is None or reason is not None:
                erasures.append(window_index)
                symbols.append(0)
            else:
                symbols.append(recovered)
            records.append(
                ByteFrameRecord(
                    window_index=window_index,
                    token_start=window_start,
                    token_end=consumed,
                    completed=singleton_step is not None and reason is None,
                    recovered_symbol=recovered,
                    erasure_reason=reason,
                    singleton_step=singleton_step,
                )
            )
        if not symbols:
            return ByteSlicedDecodeResult(None, None, tuple(records), consumed, 0, "empty_token_stream")
        codeword = bytes(symbols)
        if self.config.parity_bytes == 0:
            if erasures:
                return ByteSlicedDecodeResult(None, codeword, tuple(records), consumed, len(erasures), "uncorrectable_erasures")
            return ByteSlicedDecodeResult(codeword, codeword, tuple(records), consumed, 0)
        try:
            from reedsolo import RSCodec

            result = RSCodec(self.config.parity_bytes).decode(bytearray(codeword), erase_pos=erasures)
            payload = bytes(result[0] if isinstance(result, tuple) else result)
            corrected = bytes(result[1]) if isinstance(result, tuple) and len(result) > 1 else codeword
            return ByteSlicedDecodeResult(payload, corrected, tuple(records), consumed, len(erasures))
        except ImportError:
            return ByteSlicedDecodeResult(None, codeword, tuple(records), consumed, len(erasures), "reedsolo_missing")
        except Exception as error:  # library-specific exception types vary by version
            return ByteSlicedDecodeResult(None, codeword, tuple(records), consumed, len(erasures), str(error))
