"""Fixed-window, authenticated SparSamp microframes (R026).

The codec deliberately treats a window that does not reach a singleton sparse
interval as an erasure.  This prevents one precision-drift event from
contaminating the interval state of later windows.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from fractions import Fraction
from time import perf_counter
from typing import Hashable

from .core import _bounds, _ceil_fraction, _probabilities, _select
from .prf import HmacRandomStream
from .providers.base import ProviderSession
from .probability_contract import SupportStrategy


def _keystream(key: bytes, context: bytes, domain: bytes, size: int) -> bytes:
    """Expand a domain-separated HMAC stream for frame masking."""

    if size < 0:
        raise ValueError("keystream size must be non-negative")
    digest_key = hashlib.sha256(key).digest()
    context_digest = hashlib.sha256(context).digest()
    output = bytearray()
    counter = 0
    while len(output) < size:
        output.extend(
            hmac.new(
                digest_key,
                b"sparsamp-r026-mask\0" + domain + context_digest + counter.to_bytes(4, "big"),
                hashlib.sha256,
            ).digest()
        )
        counter += 1
    return bytes(output[:size])


def _tag(key: bytes, context: bytes, window_index: int, symbol: bytes, bits: int) -> int:
    """Return a truncated authentication tag for one unmasked symbol."""

    if bits < 1 or bits > 256:
        raise ValueError("auth_tag_bits must be in [1, 256]")
    material = (
        b"sparsamp-r026-auth\0"
        + hashlib.sha256(context).digest()
        + window_index.to_bytes(8, "big")
        + symbol
    )
    value = int.from_bytes(hmac.new(hashlib.sha256(key).digest(), material, hashlib.sha256).digest(), "big")
    return value >> (256 - bits)


def _xor_bytes(left: bytes, right: bytes) -> bytes:
    if len(left) != len(right):
        raise ValueError("mask and frame lengths must match")
    return bytes(a ^ b for a, b in zip(left, right, strict=True))


@dataclass(frozen=True)
class MicroframeConfig:
    """Parameters for independent authenticated token windows."""

    window_tokens: int = 8
    symbol_bytes: int = 2
    auth_tag_bits: int = 16
    parity_bytes: int = 0
    probability_quantum: str | None = "1e-15"
    probability_mass_bits: int | None = None
    probability_mass_headroom_bits: int | None = None
    probability_support_strategy: SupportStrategy = "base"
    preserve_probability_support: bool = True

    def __post_init__(self) -> None:
        if self.window_tokens < 1:
            raise ValueError("window_tokens must be positive")
        if self.symbol_bytes < 1:
            raise ValueError("symbol_bytes must be positive")
        if not 1 <= self.auth_tag_bits <= 256:
            raise ValueError("auth_tag_bits must be in [1, 256]")
        if self.parity_bytes < 0:
            raise ValueError("parity_bytes must be non-negative")
        if self.parity_bytes > 255:
            raise ValueError("parity_bytes must be at most 255 for Reed-Solomon")
        from .probability_contract import validate_probability_contract

        validate_probability_contract(
            self.probability_quantum,
            self.probability_mass_bits,
            self.probability_mass_headroom_bits,
            self.probability_support_strategy,
        )

    @property
    def block_size(self) -> int:
        return self.symbol_bytes * 8 + self.auth_tag_bits


@dataclass(frozen=True)
class MicroframeRecord:
    window_index: int
    token_start: int
    token_end: int
    completed: bool
    authenticated: bool | None
    erasure_reason: str | None
    singleton_step: int | None
    forward_quantization_kl_nats: float
    quantization_total_variation: float


@dataclass(frozen=True)
class MicroframeEncodeResult:
    token_ids: tuple[Hashable, ...]
    text: str
    payload_bit_length: int
    codeword_bytes: bytes
    frame_count: int
    elapsed_seconds: float
    records: tuple[MicroframeRecord, ...] = field(default_factory=tuple)

    @property
    def bits_per_token(self) -> float:
        """Net secret payload bits per visible token."""

        return self.payload_bit_length / len(self.token_ids) if self.token_ids else 0.0

    @property
    def codeword_bits_per_token(self) -> float:
        """Embedded RS codeword bits per token, including parity overhead."""

        return len(self.codeword_bytes) * 8 / len(self.token_ids) if self.token_ids else 0.0


@dataclass(frozen=True)
class MicroframeDecodeResult:
    payload_bytes: bytes | None
    recovered_codeword: bytes | None
    records: tuple[MicroframeRecord, ...]
    consumed_tokens: int
    erasure_count: int
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.payload_bytes is not None and self.error is None


class MicroframeCodec:
    """Encode a byte payload as independently reset authenticated windows.

    A window carries ``symbol_bytes`` plus a truncated HMAC tag.  Both are
    masked with a domain-separated PRF before sparse sampling.  Therefore the
    transmitted block is computationally pseudorandom under the PRF assumption;
    this is not an information-theoretic zero-KL claim for a fixed key.
    """

    def __init__(self, config: MicroframeConfig | None = None) -> None:
        self.config = config or MicroframeConfig()

    def _codeword(self, payload: bytes) -> bytes:
        if not payload:
            raise ValueError("payload must not be empty")
        if len(payload) % self.config.symbol_bytes:
            raise ValueError("payload length must be a multiple of symbol_bytes")
        if self.config.parity_bytes == 0:
            return payload
        try:
            from reedsolo import RSCodec
        except ImportError as error:
            raise RuntimeError(
                "parity_bytes requires the optional 'reedsolo' package"
            ) from error
        return bytes(RSCodec(self.config.parity_bytes).encode(payload))

    def _frame_bits(self, key: bytes, context: bytes, window_index: int, symbol: bytes) -> int:
        tag = _tag(key, context, window_index, symbol, self.config.auth_tag_bits)
        frame = int.from_bytes(symbol, "big") << self.config.auth_tag_bits | tag
        mask = _keystream(
            key,
            context,
            b"frame\0" + window_index.to_bytes(8, "big"),
            (self.config.block_size + 7) // 8,
        )
        mask_value = int.from_bytes(mask, "big") & ((1 << self.config.block_size) - 1)
        return frame ^ mask_value

    def _open_frame(
        self, key: bytes, context: bytes, window_index: int, masked_value: int
    ) -> tuple[bytes | None, str | None]:
        mask = _keystream(
            key,
            context,
            b"frame\0" + window_index.to_bytes(8, "big"),
            (self.config.block_size + 7) // 8,
        )
        mask_value = int.from_bytes(mask, "big") & ((1 << self.config.block_size) - 1)
        frame = masked_value ^ mask_value
        tag_mask = (1 << self.config.auth_tag_bits) - 1
        received_tag = frame & tag_mask
        symbol = (frame >> self.config.auth_tag_bits).to_bytes(self.config.symbol_bytes, "big")
        if received_tag != _tag(key, context, window_index, symbol, self.config.auth_tag_bits):
            return None, "authentication_failed"
        return symbol, None

    def _window_domain(self, window_index: int) -> bytes:
        return b"sparsamp-r026-window\0" + window_index.to_bytes(8, "big")

    def encode(self, session: ProviderSession, payload: bytes, key: bytes) -> MicroframeEncodeResult:
        codeword = self._codeword(payload)
        if len(codeword) % self.config.symbol_bytes:
            raise ValueError("codeword length must be a multiple of symbol_bytes")
        frame_count = len(codeword) // self.config.symbol_bytes
        stream = HmacRandomStream(key, session.context_id)
        records: list[MicroframeRecord] = []
        started = perf_counter()
        for window_index in range(frame_count):
            symbol_start = window_index * self.config.symbol_bytes
            symbol = codeword[symbol_start : symbol_start + self.config.symbol_bytes]
            target = self._frame_bits(key, session.context_id, window_index, symbol)
            modulus = 1 << self.config.block_size
            n_m, k_m = modulus, target
            temp0_values: list[int] = []
            n_values: list[int] = []
            singleton_step: int | None = None
            window_start = len(session.generated_token_ids)
            embedded = True
            kl_sum = 0.0
            tv_sum = 0.0
            reason: str | None = None
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
                r = stream.fraction(local_step, domain=self._window_domain(window_index))
                if embedded and snapshot.source_mass >= 0.0:
                    kl_sum += snapshot.forward_kl_to_nats(probabilities)
                    tv_sum += snapshot.total_variation_to(probabilities)
                if not embedded:
                    token_id = snapshot.native_token_id
                    if token_id is None:
                        token_id = snapshot.candidates[
                            _select(probabilities, stream.fraction(local_step, domain=b"r026-filler"))
                        ].token_id
                else:
                    try:
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
                        temp0_values.append(temp0)
                        n_values.append(n_m)
                        if n_m == 1:
                            embedded = False
                            singleton_step = local_step
                    except (ArithmeticError, IndexError, ValueError) as error:
                        embedded = False
                        reason = type(error).__name__
                        token_id = snapshot.native_token_id or snapshot.candidates[_select(probabilities, r)].token_id
                session.append(token_id)
            records.append(
                MicroframeRecord(
                    window_index=window_index,
                    token_start=window_start,
                    token_end=len(session.generated_token_ids),
                    completed=singleton_step is not None,
                    authenticated=None,
                    erasure_reason=reason if singleton_step is None else None,
                    singleton_step=singleton_step,
                    forward_quantization_kl_nats=kl_sum,
                    quantization_total_variation=tv_sum,
                )
            )
        return MicroframeEncodeResult(
            token_ids=session.generated_token_ids,
            text=session.render(),
            payload_bit_length=len(payload) * 8,
            codeword_bytes=codeword,
            frame_count=frame_count,
            elapsed_seconds=perf_counter() - started,
            records=tuple(records),
        )

    def decode(
        self, session: ProviderSession, token_ids: tuple[Hashable, ...] | list[Hashable], key: bytes
    ) -> MicroframeDecodeResult:
        records: list[MicroframeRecord] = []
        symbols: list[bytes] = []
        erasures: list[int] = []
        consumed = 0
        stream = HmacRandomStream(key, session.context_id)
        # The caller supplies exactly the fixed-window token stream produced by encode.
        window_count = (len(token_ids) + self.config.window_tokens - 1) // self.config.window_tokens
        for window_index in range(window_count):
            if consumed >= len(token_ids):
                break
            window_start = consumed
            n_m = 1 << self.config.block_size
            temp0_values: list[int] = []
            n_values: list[int] = []
            masked_value: int | None = None
            singleton_step: int | None = None
            reason: str | None = None
            kl_sum = 0.0
            tv_sum = 0.0
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
                if reason is None and singleton_step is None:
                    kl_sum += snapshot.forward_kl_to_nats(probabilities)
                    tv_sum += snapshot.total_variation_to(probabilities)
                    try:
                        candidate_index = next(
                            i for i, candidate in enumerate(snapshot.candidates)
                            if candidate.token_id == observed
                        )
                        r = stream.fraction(
                            local_step, domain=self._window_domain(window_index)
                        )
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
                            masked_value = value % (1 << self.config.block_size)
                            singleton_step = local_step
                    except (StopIteration, ArithmeticError, IndexError, ValueError) as error:
                        reason = type(error).__name__
                try:
                    session.append(observed)
                except ValueError as error:
                    reason = reason or f"provider_append_failed:{error}"
                    return MicroframeDecodeResult(
                        None, None, tuple(records), consumed, len(erasures) + 1, str(error)
                    )
                consumed += 1
            completed = singleton_step is not None and masked_value is not None and reason is None
            authenticated: bool | None = None
            symbol: bytes | None = None
            if completed:
                symbol, auth_error = self._open_frame(
                    key, session.context_id, window_index, masked_value
                )
                authenticated = auth_error is None
                reason = auth_error
            if not completed or symbol is None:
                erasures.extend(range(window_index * self.config.symbol_bytes, (window_index + 1) * self.config.symbol_bytes))
                symbols.append(bytes(self.config.symbol_bytes))
            else:
                symbols.append(symbol)
            records.append(
                MicroframeRecord(
                    window_index=window_index,
                    token_start=window_start,
                    token_end=consumed,
                    completed=completed,
                    authenticated=authenticated,
                    erasure_reason=reason,
                    singleton_step=singleton_step,
                    forward_quantization_kl_nats=kl_sum,
                    quantization_total_variation=tv_sum,
                )
            )
        if not symbols:
            return MicroframeDecodeResult(None, None, tuple(records), consumed, 0, "empty_token_stream")
        codeword = b"".join(symbols)
        if self.config.parity_bytes == 0:
            if erasures:
                return MicroframeDecodeResult(None, None, tuple(records), consumed, len(erasures), "uncorrectable_erasures")
            return MicroframeDecodeResult(codeword, codeword, tuple(records), consumed, 0)
        try:
            from reedsolo import RSCodec
        except ImportError:
            return MicroframeDecodeResult(None, None, tuple(records), consumed, len(erasures), "reedsolo_missing")
        try:
            result = RSCodec(self.config.parity_bytes).decode(bytearray(codeword), erase_pos=erasures)
            recovered = bytes(result[0] if isinstance(result, tuple) else result)
            corrected = bytes(result[1]) if isinstance(result, tuple) and len(result) > 1 else codeword
            return MicroframeDecodeResult(
                recovered,
                corrected,
                tuple(records),
                consumed,
                len(erasures),
            )
        except Exception as error:  # library-specific exception types vary by version
            return MicroframeDecodeResult(None, codeword, tuple(records), consumed, len(erasures), str(error))
