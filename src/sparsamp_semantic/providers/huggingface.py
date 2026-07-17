"""Local Hugging Face provider for semantic instruction models."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Hashable

from ..types import DistributionSnapshot, TokenCandidate
from .base import Provider, ProviderSession


@dataclass(frozen=True)
class HuggingFaceConfig:
    """Configuration shared by encoder and decoder model sessions."""

    model_name: str = "Qwen/Qwen2.5-1.5B-Instruct"
    revision: str | None = None
    top_p: float = 0.95
    top_k: int | None = None
    temperature: float = 1.0
    device: str = "auto"
    dtype: str = "float16"
    load_in_4bit: bool = False
    system_prompt: str = (
        "你是一个表达自然、内容准确的助手。直接回答用户问题，保持上下文连贯，"
        "不要提及采样、编码或隐藏消息。"
    )
    allow_eos: bool = False
    seed: int = 42
    adaptive_temperature: bool = False
    entropy_floor_bits: float = 0.75
    rescue_temperature: float = 1.1
    rescue_patience: int = 8

    def __post_init__(self) -> None:
        if not 0.0 < self.top_p <= 1.0:
            raise ValueError("top_p must be in (0, 1]")
        if self.top_k is not None and self.top_k < 1:
            raise ValueError("top_k must be positive")
        if self.temperature <= 0:
            raise ValueError("temperature must be positive")
        if self.entropy_floor_bits < 0:
            raise ValueError("entropy_floor_bits must be non-negative")
        if self.adaptive_temperature and self.rescue_temperature < self.temperature:
            raise ValueError("rescue_temperature must be at least the base temperature")
        if self.rescue_patience < 1:
            raise ValueError("rescue_patience must be positive")


def select_effective_temperature(
    entropy_bits: float,
    low_entropy_streak: int,
    config: HuggingFaceConfig,
) -> tuple[float, int, bool]:
    """Update the public low-entropy controller and return this step's temperature."""

    if not config.adaptive_temperature:
        return config.temperature, 0, False
    if entropy_bits < config.entropy_floor_bits:
        low_entropy_streak += 1
    else:
        low_entropy_streak = 0
    rescue_active = low_entropy_streak >= config.rescue_patience
    temperature = config.rescue_temperature if rescue_active else config.temperature
    return temperature, low_entropy_streak, rescue_active


class HuggingFaceSession(ProviderSession):
    """Cached autoregressive session backed by a local Transformers model."""

    def __init__(self, model: Any, tokenizer: Any, prompt: str, config: HuggingFaceConfig) -> None:
        import torch

        self._torch = torch
        self._model = model
        self._tokenizer = tokenizer
        self._prompt = prompt
        self._config = config
        self._device = next(model.parameters()).device
        messages = [
            {"role": "system", "content": config.system_prompt},
            {"role": "user", "content": prompt},
        ]
        if getattr(tokenizer, "chat_template", None):
            prompt_ids = tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt",
            )
        else:
            plain_prompt = f"{config.system_prompt}\n\n用户：{prompt}\n助手："
            prompt_ids = tokenizer(plain_prompt, return_tensors="pt").input_ids
        self._prompt_ids = prompt_ids.to(self._device)
        self._generated: list[int] = []
        self._past_key_values: Any = None
        self._pending_token: int | None = None
        self._last_candidates: set[int] = set()
        self._generator = torch.Generator(device=self._device)
        self._generator.manual_seed(config.seed)
        self._low_entropy_streak = 0

    @property
    def context_id(self) -> bytes:
        material = "\0".join(
            [
                "hf-v1",
                self._config.model_name,
                self._config.revision or "default",
                str(self._config.top_p),
                str(self._config.top_k),
                str(self._config.temperature),
                str(self._config.adaptive_temperature),
                str(self._config.entropy_floor_bits),
                str(self._config.rescue_temperature),
                str(self._config.rescue_patience),
                self._config.dtype,
                str(self._config.load_in_4bit),
                self._config.system_prompt,
                self._prompt,
            ]
        )
        return hashlib.sha256(material.encode("utf-8")).digest()

    @property
    def generated_token_ids(self) -> tuple[Hashable, ...]:
        return tuple(self._generated)

    def _forward(self) -> tuple[Any, float]:
        torch = self._torch
        started = perf_counter()
        with torch.inference_mode():
            if self._past_key_values is None:
                output = self._model(input_ids=self._prompt_ids, use_cache=True)
            else:
                if self._pending_token is None:
                    raise RuntimeError(
                        "a token must be appended before requesting the next distribution"
                    )
                input_ids = torch.tensor([[self._pending_token]], device=self._device)
                output = self._model(
                    input_ids=input_ids,
                    past_key_values=self._past_key_values,
                    use_cache=True,
                )
        self._past_key_values = output.past_key_values
        self._pending_token = None
        return output.logits[0, -1].float(), (perf_counter() - started) * 1000

    def next_distribution(self) -> DistributionSnapshot:
        torch = self._torch
        logits, latency_ms = self._forward()

        if not self._config.allow_eos:
            blocked = {
                token_id
                for token_id in (
                    self._tokenizer.eos_token_id,
                    self._tokenizer.pad_token_id,
                )
                if token_id is not None
            }
            for token_id in blocked:
                logits[token_id] = -torch.inf

        base_probabilities = torch.softmax(logits / self._config.temperature, dim=-1)
        positive = base_probabilities > 0
        base_entropy_bits = float(
            -(
                base_probabilities[positive]
                * torch.log2(base_probabilities[positive])
            ).sum().item()
        )
        effective_temperature, self._low_entropy_streak, rescue_active = (
            select_effective_temperature(
                base_entropy_bits, self._low_entropy_streak, self._config
            )
        )
        probabilities = (
            torch.softmax(logits / effective_temperature, dim=-1)
            if rescue_active
            else base_probabilities
        )
        sorted_probabilities, sorted_indices = torch.sort(probabilities, descending=True)

        if self._config.top_k is not None:
            sorted_probabilities = sorted_probabilities[: self._config.top_k]
            sorted_indices = sorted_indices[: self._config.top_k]

        cumulative = torch.cumsum(sorted_probabilities, dim=0)
        keep = cumulative - sorted_probabilities < self._config.top_p
        keep[0] = True
        retained_probabilities = sorted_probabilities[keep]
        retained_indices = sorted_indices[keep]
        source_mass = float(retained_probabilities.sum().item())
        retained_probabilities = retained_probabilities / retained_probabilities.sum()

        native_position = int(
            torch.multinomial(retained_probabilities, 1, generator=self._generator).item()
        )
        native_token_id = int(retained_indices[native_position].item())
        candidates: list[TokenCandidate] = []
        for rank, (token_tensor, probability_tensor) in enumerate(
            zip(retained_indices, retained_probabilities, strict=True)
        ):
            token_id = int(token_tensor.item())
            probability = float(probability_tensor.item())
            text = self._tokenizer.decode(
                [token_id], skip_special_tokens=False, clean_up_tokenization_spaces=False
            )
            candidates.append(
                TokenCandidate(
                    token_id=token_id,
                    text=text,
                    raw_bytes=text.encode("utf-8", errors="replace"),
                    probability=probability,
                    logprob=float(torch.log(probability_tensor).item()),
                    rank=rank,
                )
            )
        total = sum(candidate.probability for candidate in candidates)
        if total != 1.0:
            last = candidates[-1]
            candidates[-1] = TokenCandidate(
                token_id=last.token_id,
                text=last.text,
                raw_bytes=last.raw_bytes,
                probability=last.probability + (1.0 - total),
                logprob=last.logprob,
                rank=last.rank,
            )
        self._last_candidates = {int(candidate.token_id) for candidate in candidates}
        return DistributionSnapshot(
            candidates=tuple(candidates),
            source_mass=source_mass,
            native_token_id=native_token_id,
            model_name=self._config.model_name,
            model_fingerprint=self._config.revision,
            latency_ms=latency_ms,
            metadata={
                "top_p": self._config.top_p,
                "top_k": self._config.top_k,
                "temperature": self._config.temperature,
                "effective_temperature": effective_temperature,
                "base_entropy_bits": base_entropy_bits,
                "adaptive_temperature": self._config.adaptive_temperature,
                "entropy_floor_bits": self._config.entropy_floor_bits,
                "rescue_temperature": self._config.rescue_temperature,
                "rescue_patience": self._config.rescue_patience,
                "low_entropy_streak": self._low_entropy_streak,
                "rescue_active": rescue_active,
                "dtype": self._config.dtype,
                "load_in_4bit": self._config.load_in_4bit,
            },
        )

    def append(self, token_id: Hashable) -> None:
        if not isinstance(token_id, int):
            raise TypeError("Hugging Face token IDs must be integers")
        if token_id not in self._last_candidates:
            raise ValueError(f"token {token_id} is not in the current retained distribution")
        self._generated.append(token_id)
        self._pending_token = token_id

    def render(self) -> str:
        return self._tokenizer.decode(
            self._generated,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )

    def retokenize(self, text: str) -> tuple[Hashable, ...]:
        return tuple(self._tokenizer.encode(text, add_special_tokens=False))


class HuggingFaceProvider(Provider):
    """Load one local model and create independent cached sessions."""

    def __init__(self, config: HuggingFaceConfig | None = None) -> None:
        self.config = config or HuggingFaceConfig()
        self._model: Any = None
        self._tokenizer: Any = None

    def _load(self) -> None:
        if self._model is not None:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        device = self.config.device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = getattr(torch, self.config.dtype) if device == "cuda" else torch.float32
        model_kwargs: dict[str, Any] = {
            "revision": self.config.revision,
            "dtype": dtype,
            "low_cpu_mem_usage": True,
        }
        if self.config.load_in_4bit:
            from transformers import BitsAndBytesConfig

            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=dtype,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )
            model_kwargs["device_map"] = "auto"
        self._tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_name,
            revision=self.config.revision,
            use_fast=True,
        )
        self._model = AutoModelForCausalLM.from_pretrained(
            self.config.model_name,
            **model_kwargs,
        )
        if not self.config.load_in_4bit:
            self._model.to(device)
        self._model.eval()

    def start(self, prompt: str) -> ProviderSession:
        return self.start_with_config(prompt, self.config)

    def start_with_config(self, prompt: str, session_config: HuggingFaceConfig) -> ProviderSession:
        """Create a session with sampling overrides while reusing loaded model weights."""

        immutable_fields = ("model_name", "revision", "device", "dtype", "load_in_4bit")
        for field_name in immutable_fields:
            if getattr(session_config, field_name) != getattr(self.config, field_name):
                raise ValueError(f"cannot change loaded-model field: {field_name}")
        self._load()
        return HuggingFaceSession(self._model, self._tokenizer, prompt, session_config)
