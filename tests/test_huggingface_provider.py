from __future__ import annotations

from typing import Any

from sparsamp_semantic.providers.huggingface import HuggingFaceSession


class _WhitespaceTokenizer:
    def decode(self, *_args: Any, **_kwargs: Any) -> str:
        return " leading and trailing "


def test_render_preserves_tokenizer_whitespace() -> None:
    session = object.__new__(HuggingFaceSession)
    session._tokenizer = _WhitespaceTokenizer()
    session._generated = [1, 2, 3]

    assert session.render() == " leading and trailing "
