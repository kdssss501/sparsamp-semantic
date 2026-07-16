"""Provider contracts shared by local and API language models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Hashable

from ..types import DistributionSnapshot


class ProviderSession(ABC):
    """A deterministic autoregressive generation session."""

    @property
    @abstractmethod
    def context_id(self) -> bytes:
        """Return stable bytes identifying model configuration and prompt."""

    @property
    @abstractmethod
    def generated_token_ids(self) -> tuple[Hashable, ...]:
        """Return token IDs appended so far."""

    @abstractmethod
    def next_distribution(self) -> DistributionSnapshot:
        """Return the next-token distribution for the current prefix."""

    @abstractmethod
    def append(self, token_id: Hashable) -> None:
        """Append one selected or observed token to the session."""

    @abstractmethod
    def render(self) -> str:
        """Render generated tokens to user-visible text."""

    def retokenize(self, text: str) -> tuple[Hashable, ...]:
        """Tokenize rendered text for Token Ambiguity checks when supported."""

        raise NotImplementedError("this provider does not expose a tokenizer")


class Provider(ABC):
    """Factory for independent encoder and decoder sessions."""

    @abstractmethod
    def start(self, prompt: str) -> ProviderSession:
        """Create a fresh generation session for a prompt."""

    def replay(self, prompt: str, token_ids: Sequence[Hashable]) -> ProviderSession:
        """Create a session and append an existing prefix."""

        session = self.start(prompt)
        for token_id in token_ids:
            session.append(token_id)
        return session

