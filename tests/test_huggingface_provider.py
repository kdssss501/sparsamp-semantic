from __future__ import annotations

from typing import Any

import pytest

from sparsamp_semantic.providers.huggingface import (
    HuggingFaceConfig,
    HuggingFaceSession,
    _mutable_float_logits,
    normalize_retained_probabilities,
    order_token_candidates,
    quantize_relative_logits,
    rank_probabilities,
    select_effective_temperature,
)
from sparsamp_semantic.types import TokenCandidate


class _WhitespaceTokenizer:
    def decode(self, *_args: Any, **_kwargs: Any) -> str:
        return " leading and trailing "


def _candidate(token_id: int, probability: float, rank: int) -> TokenCandidate:
    return TokenCandidate(
        token_id=token_id,
        text=str(token_id),
        raw_bytes=str(token_id).encode(),
        probability=probability,
        logprob=0.0,
        rank=rank,
    )


def test_render_preserves_tokenizer_whitespace() -> None:
    session = object.__new__(HuggingFaceSession)
    session._tokenizer = _WhitespaceTokenizer()
    session._generated = [1, 2, 3]

    assert session.render() == " leading and trailing "


def test_fp32_inference_logits_are_cloned_before_inplace_filtering() -> None:
    torch = pytest.importorskip("torch")
    with torch.inference_mode():
        inference_logits = torch.tensor([1.0, 2.0], dtype=torch.float32)

    mutable = _mutable_float_logits(inference_logits)
    mutable[0] = -torch.inf

    assert torch.isneginf(mutable[0])
    assert inference_logits[0].item() == 1.0


def test_entropy_rescue_activates_after_public_patience() -> None:
    config = HuggingFaceConfig(
        temperature=0.8,
        adaptive_temperature=True,
        entropy_floor_bits=0.75,
        rescue_temperature=1.1,
        rescue_patience=3,
    )
    streak = 0

    temperature, streak, active = select_effective_temperature(0.6, streak, config)
    assert (temperature, streak, active) == (0.8, 1, False)
    temperature, streak, active = select_effective_temperature(0.5, streak, config)
    assert (temperature, streak, active) == (0.8, 2, False)
    temperature, streak, active = select_effective_temperature(0.4, streak, config)
    assert (temperature, streak, active) == (1.1, 3, True)
    temperature, streak, active = select_effective_temperature(1.2, streak, config)
    assert (temperature, streak, active) == (0.8, 0, False)


def test_entropy_rescue_rejects_lower_temperature() -> None:
    with pytest.raises(ValueError, match="at least the base"):
        HuggingFaceConfig(
            temperature=1.0,
            adaptive_temperature=True,
            rescue_temperature=0.9,
        )


def test_entropy_controller_does_not_change_pre_intervention_prf_context() -> None:
    fixed = object.__new__(HuggingFaceSession)
    fixed._config = HuggingFaceConfig(temperature=0.8)
    fixed._prompt = "paired prompt"
    adaptive = object.__new__(HuggingFaceSession)
    adaptive._config = HuggingFaceConfig(
        temperature=0.8,
        adaptive_temperature=True,
        entropy_floor_bits=1.0,
        rescue_temperature=1.4,
        rescue_patience=8,
    )
    adaptive._prompt = "paired prompt"

    assert fixed.context_id == adaptive.context_id


def test_token_id_order_is_deterministic_and_preserves_token_masses() -> None:
    candidates = (
        _candidate(30, 0.5, 0),
        _candidate(10, 0.3, 1),
        _candidate(20, 0.2, 2),
    )

    ordered = order_token_candidates(candidates, "token_id")

    assert [candidate.token_id for candidate in ordered] == [10, 20, 30]
    assert {candidate.token_id: candidate.probability for candidate in ordered} == {
        10: 0.3,
        20: 0.2,
        30: 0.5,
    }
    assert {candidate.token_id: candidate.rank for candidate in ordered} == {
        10: 1,
        20: 2,
        30: 0,
    }


def test_probability_order_remains_the_default_contract() -> None:
    candidates = (_candidate(30, 0.6, 0), _candidate(10, 0.4, 1))

    assert HuggingFaceConfig().candidate_order == "probability"
    assert order_token_candidates(candidates, "probability") == candidates


def test_candidate_order_changes_prf_context_without_changing_default_context() -> None:
    legacy = object.__new__(HuggingFaceSession)
    legacy._config = HuggingFaceConfig()
    legacy._prompt = "paired prompt"
    canonical = object.__new__(HuggingFaceSession)
    canonical._config = HuggingFaceConfig(candidate_order="token_id")
    canonical._prompt = "paired prompt"

    assert legacy.context_id != canonical.context_id


def test_candidate_order_rejects_unknown_contract() -> None:
    with pytest.raises(ValueError, match="candidate_order"):
        HuggingFaceConfig(candidate_order="unknown")  # type: ignore[arg-type]


def test_portable_precision_context_matches_across_dtypes() -> None:
    fp32 = object.__new__(HuggingFaceSession)
    fp32._config = HuggingFaceConfig(dtype="float32", precision_context="portable")
    fp32._prompt = "portable prompt"
    fp16 = object.__new__(HuggingFaceSession)
    fp16._config = HuggingFaceConfig(dtype="float16", precision_context="portable")
    fp16._prompt = "portable prompt"

    assert fp32.context_id == fp16.context_id


def test_strict_precision_context_separates_dtypes() -> None:
    fp32 = object.__new__(HuggingFaceSession)
    fp32._config = HuggingFaceConfig(dtype="float32")
    fp32._prompt = "strict prompt"
    fp16 = object.__new__(HuggingFaceSession)
    fp16._config = HuggingFaceConfig(dtype="float16")
    fp16._prompt = "strict prompt"

    assert fp32.context_id != fp16.context_id


def test_relative_logit_quantization_is_shift_invariant_and_bounded() -> None:
    torch = pytest.importorskip("torch")
    logits = torch.tensor([3.0, 2.991, 2.97, -torch.inf])
    shifted = logits + 17.0

    quantized, bins, max_error = quantize_relative_logits(logits, 1 / 64)
    shifted_quantized, shifted_bins, shifted_error = quantize_relative_logits(
        shifted, 1 / 64
    )

    assert torch.equal(bins, shifted_bins)
    assert torch.equal(quantized, shifted_quantized)
    assert max_error <= 1 / 128 + 1e-7
    assert shifted_error <= 1 / 128 + 1e-7


def test_quantized_probability_ties_are_broken_by_token_id() -> None:
    torch = pytest.importorskip("torch")
    probabilities = torch.tensor([0.2, 0.4, 0.4, 0.0])

    ranked, token_ids = rank_probabilities(probabilities, stable_token_ties=True)

    assert token_ids.tolist()[:3] == [1, 2, 0]
    assert ranked.tolist()[:3] == pytest.approx([0.4, 0.4, 0.2])


def test_logit_quantum_changes_context_but_remains_portable_across_dtype() -> None:
    baseline = object.__new__(HuggingFaceSession)
    baseline._config = HuggingFaceConfig(precision_context="portable")
    baseline._prompt = "quantized prompt"
    fp32 = object.__new__(HuggingFaceSession)
    fp32._config = HuggingFaceConfig(
        dtype="float32", precision_context="portable", logit_quantum=1 / 64
    )
    fp32._prompt = "quantized prompt"
    fp16 = object.__new__(HuggingFaceSession)
    fp16._config = HuggingFaceConfig(
        dtype="float16", precision_context="portable", logit_quantum=1 / 64
    )
    fp16._prompt = "quantized prompt"

    assert baseline.context_id != fp32.context_id
    assert fp32.context_id == fp16.context_id


def test_logit_quantum_must_be_positive() -> None:
    with pytest.raises(ValueError, match="logit_quantum"):
        HuggingFaceConfig(logit_quantum=0.0)


def test_retained_probability_normalization_preserves_tiny_positive_mass() -> None:
    torch = pytest.importorskip("torch")
    probabilities = torch.tensor([1.0, 1e-9, 1e-12], dtype=torch.float32)

    normalized = normalize_retained_probabilities(probabilities)

    assert normalized.dtype == torch.float64
    assert all(value > 0 for value in normalized.tolist())
    assert sum(normalized.tolist()) == pytest.approx(1.0, abs=1e-15)
