"""Semantic SparSamp package."""

from .core import CodecConfig, DecodeResult, EncodeResult, IncompleteEncodeError, SparSampCodec
from .fh import FhCodecConfig, FhSparSampCodec
from .finishing import FinishingConfig, FinishingResult, finish_session, is_sentence_complete
from .fixed_length_rrc import (
    FixedLengthCoverSampler,
    FixedLengthDecodeError,
    FixedLengthDecodeResult,
    FixedLengthEncodeResult,
    FixedLengthRotationRangeCodec,
    FixedLengthRrcConfig,
)
from .payload import PayloadCodec
from .microframe import (
    MicroframeCodec,
    MicroframeConfig,
    MicroframeDecodeResult,
    MicroframeEncodeResult,
    MicroframeRecord,
)
from .probability_contract import IntegerMassAllocation, allocate_integer_mass
from .rrc import RrcConfig, RotationRangeCodec

__all__ = [
    "CodecConfig",
    "DecodeResult",
    "EncodeResult",
    "FhCodecConfig",
    "FhSparSampCodec",
    "FinishingConfig",
    "FinishingResult",
    "FixedLengthCoverSampler",
    "FixedLengthDecodeError",
    "FixedLengthDecodeResult",
    "FixedLengthEncodeResult",
    "FixedLengthRotationRangeCodec",
    "FixedLengthRrcConfig",
    "IncompleteEncodeError",
    "IntegerMassAllocation",
    "PayloadCodec",
    "MicroframeCodec",
    "MicroframeConfig",
    "MicroframeDecodeResult",
    "MicroframeEncodeResult",
    "MicroframeRecord",
    "RrcConfig",
    "RotationRangeCodec",
    "SparSampCodec",
    "allocate_integer_mass",
    "finish_session",
    "is_sentence_complete",
]
