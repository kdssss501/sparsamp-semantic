"""Fixed-length, authenticated-prefix wrapper for Verified-RRC."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_DOWN, localcontext
from time import perf_counter
from typing import Hashable, Literal

from .core import DecodeResult, EncodeResult, IncompleteEncodeError, StepRecord
from .prf import HmacRandomStream
from .providers.base import ProviderSession
from .types import DistributionSnapshot
from .rrc import (
    RrcConfig,
    RotationRangeCodec,
    _decimal_probabilities,
    _observed_interval,
    _select_interval,
)

_AUTH_KEY_DOMAIN = b"fixed-length-rrc-auth-key-v1"
_AUTH_TAG_DOMAIN = b"fixed-length-rrc-auth-tag-v1"
_PADDING_DOMAIN = b"fixed-length-rrc-padding-v1"
_COVER_DOMAIN = b"fixed-length-rrc-cover-v1"
_COVER_RUN_KEY_DOMAIN = b"fixed-length-rrc-cover-run-key-v1"


class FixedLengthDecodeError(ValueError):
    """Raised when no unique authenticated payload can be recovered."""


@dataclass(frozen=True)
class FixedLengthRrcConfig:
    """Configuration for fixed-public-length Verified-RRC."""

    payload_bits: int
    total_tokens: int
    tag_bits: int = 128
    probability_quantum: str | None = "1e-15"
    guard_digits: int = 24
    min_precision: int = 48
    failure_mode: Literal["raise", "cover"] = "raise"

    def __post_init__(self) -> None:
        if self.payload_bits < 1:
            raise ValueError("payload_bits must be positive")
        if self.total_tokens < 1:
            raise ValueError("total_tokens must be positive")
        if not 32 <= self.tag_bits <= 256:
            raise ValueError("tag_bits must lie in [32, 256]")
        if self.failure_mode not in {"raise", "cover"}:
            raise ValueError("failure_mode must be 'raise' or 'cover'")
        RrcConfig(
            message_bits=self.frame_bits,
            max_tokens=self.total_tokens,
            probability_quantum=self.probability_quantum,
            guard_digits=self.guard_digits,
            min_precision=self.min_precision,
        )

    @property
    def frame_bits(self) -> int:
        return self.payload_bits + self.tag_bits

    @property
    def rrc_config(self) -> RrcConfig:
        return RrcConfig(
            message_bits=self.frame_bits,
            max_tokens=self.total_tokens,
            probability_quantum=self.probability_quantum,
            guard_digits=self.guard_digits,
            min_precision=self.min_precision,
            termination_mode="verified",
        )


@dataclass(frozen=True)
class FixedLengthEncodeResult(EncodeResult):
    """Fixed-length text plus the hidden embedding/padding boundary for auditing."""

    embedded_token_count: int = 0
    authentication_bits: int = 0
    payload_embedded: bool = True

    @property
    def padding_token_count(self) -> int:
        return len(self.token_ids) - self.embedded_token_count


@dataclass(frozen=True)
class FixedLengthDecodeResult(DecodeResult):
    """Authenticated payload and the earliest validating prefix length."""

    authenticated_prefix_tokens: int = 0
    authenticated_candidates: int = 0


def _validate_key(key: bytes) -> None:
    if len(key) < 16:
        raise ValueError("fixed-length RRC key must contain at least 16 bytes")


def _validate_bits(bits: str, expected_length: int) -> None:
    if len(bits) != expected_length:
        raise ValueError(f"payload must contain exactly {expected_length} bits")
    if set(bits) - {"0", "1"}:
        raise ValueError("payload must be a binary string")


def _authentication_tag(payload: str, key: bytes, context_id: bytes, tag_bits: int) -> str:
    _validate_key(key)
    derived_key = hmac.new(hashlib.sha256(key).digest(), _AUTH_KEY_DOMAIN, hashlib.sha256).digest()
    material = (
        _AUTH_TAG_DOMAIN
        + len(payload).to_bytes(8, "big", signed=False)
        + context_id
        + payload.encode("ascii")
    )
    digest = hmac.new(derived_key, material, hashlib.sha256).digest()
    return "".join(f"{byte:08b}" for byte in digest)[:tag_bits]


def _seal_frame(payload: str, key: bytes, context_id: bytes, tag_bits: int) -> str:
    return payload + _authentication_tag(payload, key, context_id, tag_bits)


def _open_frame(
    frame: str,
    key: bytes,
    context_id: bytes,
    payload_bits: int,
    tag_bits: int,
) -> str | None:
    if len(frame) != payload_bits + tag_bits:
        return None
    payload = frame[:payload_bits]
    observed_tag = frame[payload_bits:]
    expected_tag = _authentication_tag(payload, key, context_id, tag_bits)
    return payload if hmac.compare_digest(observed_tag, expected_tag) else None


def _step_record(
    *,
    step: int,
    token_id: Hashable,
    snapshot: DistributionSnapshot,
    implemented_probabilities: tuple[Decimal, ...],
    embedded: bool,
) -> StepRecord:
    metadata = snapshot.metadata
    return StepRecord(
        step=step,
        token_id=token_id,
        embedded=embedded,
        block_completed=False,
        entropy_bits=snapshot.entropy_bits,
        source_mass=snapshot.source_mass,
        truncation_kl_nats=snapshot.truncation_kl_nats,
        candidate_count=len(snapshot.candidates),
        latency_ms=snapshot.latency_ms,
        block_size=None,
        completed_bits=0,
        base_entropy_bits=metadata.get("base_entropy_bits"),
        effective_temperature=metadata.get("effective_temperature"),
        rescue_active=bool(metadata.get("rescue_active", False)),
        low_entropy_streak=int(metadata.get("low_entropy_streak", 0)),
        forward_quantization_kl_nats=snapshot.forward_kl_to_nats(
            implemented_probabilities
        ),
        quantization_total_variation=snapshot.total_variation_to(
            implemented_probabilities
        ),
    )


class FixedLengthRotationRangeCodec:
    """Embed an authenticated payload prefix and pad to a public token length."""

    def __init__(self, config: FixedLengthRrcConfig) -> None:
        self.config = config

    def _sample_quantized_token(
        self,
        session: ProviderSession,
        random_stream: HmacRandomStream,
        step: int,
        domain: bytes,
    ) -> StepRecord:
        snapshot = session.next_distribution()
        probabilities = _decimal_probabilities(snapshot, self.config.probability_quantum)
        offset_fraction = random_stream.fraction(step, domain=domain)
        position = Decimal(offset_fraction.numerator) / Decimal(offset_fraction.denominator)
        candidate_index, _, _ = _select_interval(probabilities, position)
        token_id = snapshot.candidates[candidate_index].token_id
        session.append(token_id)
        return _step_record(
            step=step,
            token_id=token_id,
            snapshot=snapshot,
            implemented_probabilities=probabilities,
            embedded=False,
        )

    def encode(self, session: ProviderSession, bits: str, key: bytes) -> FixedLengthEncodeResult:
        """Embed bits, then sample from the same quantized target to total_tokens."""

        _validate_bits(bits, self.config.payload_bits)
        _validate_key(key)
        started = perf_counter()
        context_id = session.context_id
        frame = _seal_frame(bits, key, context_id, self.config.tag_bits)
        codec = RotationRangeCodec(self.config.rrc_config)

        try:
            embedded = codec.encode(session, frame, key)
        except IncompleteEncodeError as error:
            if self.config.failure_mode == "raise":
                raise
            return FixedLengthEncodeResult(
                token_ids=error.token_ids,
                text=error.text,
                embedded_bits=0,
                padded_bits=0,
                elapsed_seconds=perf_counter() - started,
                records=error.records,
                embedded_token_count=0,
                authentication_bits=self.config.tag_bits,
                payload_embedded=False,
            )

        embedded_token_count = len(embedded.token_ids)
        records = [
            replace(
                record,
                completed_bits=self.config.payload_bits if record.block_completed else 0,
            )
            for record in embedded.records
        ]
        random_stream = HmacRandomStream(key, context_id)
        with localcontext() as context:
            context.prec = self.config.rrc_config.decimal_precision
            for step in range(embedded_token_count, self.config.total_tokens):
                records.append(
                    self._sample_quantized_token(
                        session,
                        random_stream,
                        step,
                        _PADDING_DOMAIN,
                    )
                )

        return FixedLengthEncodeResult(
            token_ids=session.generated_token_ids,
            text=session.render(),
            embedded_bits=self.config.payload_bits,
            padded_bits=0,
            elapsed_seconds=perf_counter() - started,
            records=tuple(records),
            embedded_token_count=embedded_token_count,
            authentication_bits=self.config.tag_bits,
            payload_embedded=True,
        )

    def generate_cover(self, session: ProviderSession, key: bytes) -> FixedLengthEncodeResult:
        """Generate a fixed-length cover from the codec's same quantized target."""

        _validate_key(key)
        started = perf_counter()
        random_stream = HmacRandomStream(key, session.context_id)
        records: list[StepRecord] = []
        with localcontext() as context:
            context.prec = self.config.rrc_config.decimal_precision
            for step in range(self.config.total_tokens):
                records.append(
                    self._sample_quantized_token(session, random_stream, step, _COVER_DOMAIN)
                )
        return FixedLengthEncodeResult(
            token_ids=session.generated_token_ids,
            text=session.render(),
            embedded_bits=0,
            padded_bits=0,
            elapsed_seconds=perf_counter() - started,
            records=tuple(records),
            embedded_token_count=0,
            authentication_bits=self.config.tag_bits,
            payload_embedded=False,
        )

    def decode(
        self,
        session: ProviderSession,
        token_ids: tuple[Hashable, ...] | list[Hashable],
        key: bytes,
    ) -> FixedLengthDecodeResult:
        """Scan all prefixes and return the unique authenticated payload."""

        if len(token_ids) != self.config.total_tokens:
            raise ValueError(f"fixed-length RRC requires exactly {self.config.total_tokens} tokens")
        _validate_key(key)
        context_id = session.context_id
        random_stream = HmacRandomStream(key, context_id)
        with localcontext() as context:
            context.prec = self.config.rrc_config.decimal_precision
            left = Decimal(0)
            right = Decimal(1 << self.config.frame_bits)
            history: list[tuple[Decimal, Decimal]] = []

            for step, observed_token_id in enumerate(token_ids):
                snapshot = session.next_distribution()
                probabilities = _decimal_probabilities(snapshot, self.config.probability_quantum)
                width = right - left
                if width <= 0:
                    raise ArithmeticError("fixed-length RRC interval collapsed to zero")
                history.append((left, right))
                lower_probability, upper_probability = _observed_interval(
                    snapshot, probabilities, observed_token_id, step
                )
                old_left = left
                left = old_left + width * lower_probability
                right = old_left + width * upper_probability
                session.append(observed_token_id)

                midpoint = RotationRangeCodec._reverse_midpoint(
                    (left + right) / 2,
                    history,
                    random_stream,
                )
                recovered = int(midpoint.to_integral_value(rounding=ROUND_HALF_DOWN))
                if not 0 <= recovered < 1 << self.config.frame_bits:
                    continue
                frame = f"{recovered:0{self.config.frame_bits}b}"
                payload = _open_frame(
                    frame,
                    key,
                    context_id,
                    self.config.payload_bits,
                    self.config.tag_bits,
                )
                if payload is not None:
                    return FixedLengthDecodeResult(
                        bits=payload,
                        completed_blocks=1,
                        consumed_tokens=self.config.total_tokens,
                        authenticated_prefix_tokens=step + 1,
                        authenticated_candidates=1,
                    )

        raise FixedLengthDecodeError(
            "no authenticated payload prefix was found; key, prompt, or text is wrong"
        )


class FixedLengthCoverSampler:
    """Generate a matched fixed-length cover without embedding a payload."""

    def __init__(self, config: FixedLengthRrcConfig) -> None:
        self.config = config
        self._codec = FixedLengthRotationRangeCodec(config)

    def encode(self, session: ProviderSession, bits: str, key: bytes) -> FixedLengthEncodeResult:
        """Use payload bits only to domain-separate reproducible cover samples."""

        _validate_bits(bits, self.config.payload_bits)
        _validate_key(key)
        cover_key = hmac.new(
            hashlib.sha256(key).digest(),
            _COVER_RUN_KEY_DOMAIN + bits.encode("ascii"),
            hashlib.sha256,
        ).digest()
        return self._codec.generate_cover(session, cover_key)
