from __future__ import annotations

from types import SimpleNamespace

from sparsamp_semantic.providers.deepseek import DeepSeekConfig, DeepSeekSession


class FakeCompletions:
    def create(self, **_: object) -> SimpleNamespace:
        top = [
            SimpleNamespace(token=" answer", logprob=-0.5, bytes=list(b" answer")),
            SimpleNamespace(token=" result", logprob=-2.0, bytes=list(b" result")),
            SimpleNamespace(token=" method", logprob=-3.0, bytes=list(b" method")),
        ]
        content = SimpleNamespace(
            token=" answer",
            logprob=-0.5,
            bytes=list(b" answer"),
            top_logprobs=top,
        )
        choice = SimpleNamespace(
            message=SimpleNamespace(content=" answer"),
            logprobs=SimpleNamespace(content=[content]),
        )
        return SimpleNamespace(
            choices=[choice],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=1, total_tokens=11),
            system_fingerprint="fixture-v1",
        )


class FakeClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions())


def test_deepseek_fixture_parsing_and_prefix_append() -> None:
    session = DeepSeekSession(FakeClient(), "Explain the result.", DeepSeekConfig())
    snapshot = session.next_distribution()

    assert len(snapshot.candidates) == 3
    assert 0 < snapshot.source_mass < 1
    assert snapshot.model_fingerprint == "fixture-v1"
    assert snapshot.usage["total_tokens"] == 11

    session.append(snapshot.candidates[0].token_id)
    assert session.render() == "answer"
