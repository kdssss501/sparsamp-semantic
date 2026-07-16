"""Authenticated payload framing for human-readable secret messages."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass


MAGIC = b"SSP1"
ASSOCIATED_DATA = b"sparsamp-semantic-payload-v1"


def bytes_to_bits(data: bytes) -> str:
    """Convert bytes to a big-endian bit string."""

    return "".join(f"{byte:08b}" for byte in data)


def bits_to_bytes(bits: str) -> bytes:
    """Convert a complete big-endian bit string to bytes."""

    if len(bits) % 8:
        raise ValueError("bit length must be a multiple of 8")
    if set(bits) - {"0", "1"}:
        raise ValueError("payload contains non-binary characters")
    return bytes(int(bits[index : index + 8], 2) for index in range(0, len(bits), 8))


def repeat_bits(bits: str, repetitions: int) -> str:
    """Apply a simple repetition code used by the initial robustness experiments."""

    if repetitions < 1 or repetitions % 2 == 0:
        raise ValueError("repetitions must be a positive odd integer")
    return "".join(bit * repetitions for bit in bits)


def recover_repeated_bits(bits: str, repetitions: int) -> str:
    """Majority-decode a repetition-coded bit string."""

    if repetitions < 1 or repetitions % 2 == 0:
        raise ValueError("repetitions must be a positive odd integer")
    complete = len(bits) - (len(bits) % repetitions)
    groups = (bits[index : index + repetitions] for index in range(0, complete, repetitions))
    return "".join("1" if group.count("1") > repetitions // 2 else "0" for group in groups)


@dataclass(frozen=True)
class PayloadCodec:
    """Encrypt, authenticate, frame, and optionally repeat-code a text message."""

    repetitions: int = 1

    def seal(self, message: str, key: bytes) -> str:
        """Return an encrypted framed message as binary text."""

        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

        nonce = os.urandom(12)
        cipher = ChaCha20Poly1305(hashlib.sha256(key).digest())
        ciphertext = cipher.encrypt(nonce, message.encode("utf-8"), ASSOCIATED_DATA)
        frame = MAGIC + len(ciphertext).to_bytes(4, "big") + nonce + ciphertext
        return repeat_bits(bytes_to_bits(frame), self.repetitions)

    def open(self, encoded_bits: str, key: bytes) -> str:
        """Authenticate and decode a binary payload, ignoring trailing block padding."""

        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

        bits = recover_repeated_bits(encoded_bits, self.repetitions)
        minimum_header_bits = (len(MAGIC) + 4 + 12) * 8
        if len(bits) < minimum_header_bits:
            raise ValueError("decoded payload is shorter than the frame header")
        header = bits_to_bytes(bits[:minimum_header_bits])
        if header[:4] != MAGIC:
            raise ValueError("payload magic mismatch; key, prompt, or token sequence is wrong")
        ciphertext_size = int.from_bytes(header[4:8], "big")
        frame_bits = (len(MAGIC) + 4 + 12 + ciphertext_size) * 8
        if len(bits) < frame_bits:
            raise ValueError("decoded payload is incomplete")
        frame = bits_to_bytes(bits[:frame_bits])
        nonce = frame[8:20]
        ciphertext = frame[20:]
        cipher = ChaCha20Poly1305(hashlib.sha256(key).digest())
        plaintext = cipher.decrypt(nonce, ciphertext, ASSOCIATED_DATA)
        return plaintext.decode("utf-8")
