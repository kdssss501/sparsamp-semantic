"""Versioned request and response schemas for the local REST API."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class SamplingConfig(BaseModel):
    """Sampling and codec values shared by encode and decode operations."""

    model: str = "models/qwen2.5-1.5b-instruct"
    revision: str | None = None
    device: Literal["auto", "cuda", "cpu"] = "cuda"
    dtype: Literal["float16", "bfloat16", "float32"] = "float16"
    load_in_4bit: bool = False
    top_p: float = Field(default=0.95, gt=0.0, le=1.0)
    top_k: int | None = Field(default=None, ge=1)
    temperature: float = Field(default=0.8, gt=0.0, le=5.0)
    seed: int = 42


class CodecSettings(BaseModel):
    """SparSamp interval and payload framing settings."""

    block_size: int = Field(default=32, ge=1, le=1023)
    max_tokens: int = Field(default=2048, ge=1, le=8192)
    min_source_mass: float = Field(default=0.0, ge=0.0, le=1.0)
    probability_quantum: str = "1e-15"
    repetitions: int = Field(default=1, ge=1, le=9)
    finish_mode: Literal["none", "punctuation", "fixed"] = "punctuation"
    finish_max_tokens: int = Field(default=32, ge=0, le=256)
    finish_min_tokens: int = Field(default=4, ge=0, le=256)

    @field_validator("repetitions")
    @classmethod
    def repetitions_must_be_odd(cls, value: int) -> int:
        if value % 2 == 0:
            raise ValueError("repetitions must be odd")
        return value

    @model_validator(mode="after")
    def finishing_budget_is_valid(self) -> CodecSettings:
        if (
            self.finish_mode == "punctuation"
            and self.finish_min_tokens > self.finish_max_tokens
        ):
            raise ValueError("finish_min_tokens cannot exceed finish_max_tokens")
        return self


class EncodeOperationRequest(BaseModel):
    kind: Literal["encode"]
    prompt: str = Field(min_length=1, max_length=8000)
    message: str = Field(min_length=1, max_length=4096)
    secret_key: str = Field(min_length=16, max_length=4096)
    sampling: SamplingConfig = Field(default_factory=SamplingConfig)
    codec: CodecSettings = Field(default_factory=CodecSettings)


class DecodeOperationRequest(BaseModel):
    kind: Literal["decode"]
    prompt: str | None = Field(default=None, max_length=8000)
    cover_text: str | None = Field(default=None, max_length=100_000)
    artifact_id: str | None = Field(default=None, max_length=500)
    secret_key: str = Field(min_length=16, max_length=4096)
    sampling: SamplingConfig | None = None
    codec: CodecSettings | None = None

    @model_validator(mode="after")
    def validate_decode_source(self) -> DecodeOperationRequest:
        if self.artifact_id:
            return self
        if not self.prompt or not self.cover_text:
            raise ValueError("text decoding requires prompt and cover_text")
        if self.sampling is None or self.codec is None:
            raise ValueError("text decoding requires sampling and codec settings")
        return self


class NativeOperationRequest(BaseModel):
    kind: Literal["native"]
    prompt: str = Field(min_length=1, max_length=8000)
    tokens: int = Field(default=256, ge=1, le=4096)
    sampling: SamplingConfig = Field(default_factory=SamplingConfig)


OperationCreateRequest = Annotated[
    EncodeOperationRequest | DecodeOperationRequest | NativeOperationRequest,
    Field(discriminator="kind"),
]
