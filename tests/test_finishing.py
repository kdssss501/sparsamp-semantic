from __future__ import annotations

import pytest

from sparsamp_semantic.finishing import FinishingConfig, finish_session
from sparsamp_semantic.providers.mock import MockProvider


def test_none_mode_does_not_advance_session() -> None:
    session = MockProvider().start("prompt")

    result = finish_session(session, FinishingConfig(mode="none"))

    assert result.token_ids == ()
    assert result.tail_token_count == 0
    assert result.text == ""


def test_fixed_mode_appends_exact_native_token_budget() -> None:
    session = MockProvider().start("prompt")

    result = finish_session(session, FinishingConfig(mode="fixed", max_tokens=3))

    assert result.tail_token_count == 3
    assert len(result.records) == 3
    assert result.text == "This method produces"


def test_punctuation_mode_stops_at_sentence_boundary() -> None:
    session = MockProvider().start("prompt")

    result = finish_session(
        session, FinishingConfig(mode="punctuation", min_tokens=1, max_tokens=10)
    )

    assert result.tail_token_count == 6
    assert result.text.endswith(".")
    assert result.stopped_on_punctuation


def test_invalid_finishing_budget_is_rejected() -> None:
    with pytest.raises(ValueError, match="cannot exceed"):
        FinishingConfig(mode="punctuation", min_tokens=5, max_tokens=4)
