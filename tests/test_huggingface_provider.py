from __future__ import annotations

from typing import Any

import pytest

from sparsamp_semantic.providers.huggingface import (
    HuggingFaceConfig,
    HuggingFaceSession,
    _mutable_float_logits,
    order_token_candidates,
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
