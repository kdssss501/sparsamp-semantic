from __future__ import annotations

from typing import Any

import pytest

from sparsamp_semantic.providers.huggingface import (
    HuggingFaceConfig,
    HuggingFaceSession,
    select_effective_temperature,
)


class _WhitespaceTokenizer:
    def decode(self, *_args: Any, **_kwargs: Any) -> str:
        return " leading and trailing "


def test_render_preserves_tokenizer_whitespace() -> None:
    session = object.__new__(HuggingFaceSession)
    session._tokenizer = _WhitespaceTokenizer()
    session._generated = [1, 2, 3]

    assert session.render() == " leading and trailing "


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
