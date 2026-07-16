"""Deterministic cryptographic random stream for sampling."""

from __future__ import annotations

import hashlib
import hmac
from fractions import Fraction


class HmacRandomStream:
    """Generate reproducible uniform fractions from a secret key and context."""

    def __init__(self, key: bytes, context: bytes) -> None:
        if len(key) < 16:
            raise ValueError("sampling key must contain at least 16 bytes")
        self._key = hashlib.sha256(key).digest()
        self._context = hashlib.sha256(context).digest()

    def fraction(self, step: int, domain: bytes = b"sparsamp") -> Fraction:
        """Return a deterministic value in [0, 1) with 256 bits of precision."""

        if step < 0:
            raise ValueError("step must be non-negative")
        message = domain + self._context + step.to_bytes(8, "big", signed=False)
        digest = hmac.new(self._key, message, hashlib.sha256).digest()
        return Fraction(int.from_bytes(digest, "big"), 1 << 256)

