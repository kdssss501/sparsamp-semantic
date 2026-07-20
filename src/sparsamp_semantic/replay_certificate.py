"""Explicit sparse certificates for reproducible cross-precision generation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from math import ceil, log2
from typing import Literal

from .prf import HmacRandomStream
from .probability_contract import allocate_logit_bin_mass
from .types import DistributionSnapshot


ReplayPolicy = Literal["seeded", "greedy"]


@dataclass(frozen=True)
class ReplayContractConfig:
    contract_top_k: int = 2
    logit_quantum: float = 0.5
    mass_bits: int = 16
    temperature: float = 1.2
    public_seed: int = 0

    def __post_init__(self) -> None:
        if self.contract_top_k < 1:
            raise ValueError("contract top-k must be positive")
        if self.logit_quantum <= 0 or self.temperature <= 0:
            raise ValueError("quantum and temperature must be positive")
        if not 1 <= self.mass_bits <= 52 or self.public_seed < 0:
            raise ValueError("invalid mass bits or public seed")


@dataclass(frozen=True)
class ContractDecision:
    token_id: int
    token_ids: tuple[int, ...]
    counts: tuple[int, ...]


@dataclass(frozen=True)
class ReplayCorrection:
    step: int
    token_id: int


@dataclass(frozen=True)
class ReplayManifest:
    token_count: int
    corrections: tuple[ReplayCorrection, ...]

    def __post_init__(self) -> None:
        if self.token_count < 1:
            raise ValueError("token count must be positive")
        steps = [item.step for item in self.corrections]
        if steps != sorted(set(steps)) or any(not 0 <= step < self.token_count for step in steps):
            raise ValueError("correction steps must be unique, sorted, and in range")

    def apply(self, step: int, local_token_id: int) -> int:
        for correction in self.corrections:
            if correction.step == step:
                return correction.token_id
            if correction.step > step:
                break
        return local_token_id


def decision_context(model_name: str, prompt: str, config: ReplayContractConfig) -> bytes:
    fields = (
        "replay-certificate-v1",
        model_name,
        prompt,
        str(config.contract_top_k),
        str(config.logit_quantum),
        str(config.mass_bits),
        str(config.temperature),
        str(config.public_seed),
    )
    return hashlib.sha256("\0".join(fields).encode("utf-8")).digest()


def contract_decision(
    snapshot: DistributionSnapshot,
    step: int,
    context: bytes,
    config: ReplayContractConfig,
    policy: ReplayPolicy = "seeded",
) -> ContractDecision:
    if step < 0:
        raise ValueError("step must be non-negative")
    ranked = sorted(snapshot.candidates, key=lambda candidate: int(candidate.rank))
    if len(ranked) < config.contract_top_k:
        raise ValueError("snapshot has fewer candidates than contract top-k")
    selected = ranked[: config.contract_top_k]
    bins_raw = snapshot.metadata.get("quantized_logit_bins")
    if not isinstance(bins_raw, dict):
        raise ValueError("snapshot does not expose quantized logit bins")
    bins = {int(token_id): int(value) for token_id, value in bins_raw.items()}
    ordered = sorted(selected, key=lambda candidate: int(candidate.token_id))
    token_ids = tuple(int(candidate.token_id) for candidate in ordered)
    allocation = allocate_logit_bin_mass(
        token_ids,
        [bins[token_id] for token_id in token_ids],
        quantum=config.logit_quantum,
        temperature=config.temperature,
        mass_bits=config.mass_bits,
    )
    if policy == "greedy":
        index = min(
            range(len(token_ids)), key=lambda item: (-allocation.counts[item], token_ids[item])
        )
    elif policy == "seeded":
        seed_key = hashlib.sha256(
            b"public-replay-seed\0" + config.public_seed.to_bytes(16, "big")
        ).digest()
        sample = HmacRandomStream(seed_key, context).fraction(
            step, domain=b"replay-certificate-choice\0"
        )
        mass_index = sample.numerator * allocation.total_mass // sample.denominator
        cumulative = 0
        index = 0
        for index, count in enumerate(allocation.counts):
            cumulative += count
            if mass_index < cumulative:
                break
    else:
        raise ValueError("policy must be 'seeded' or 'greedy'")
    return ContractDecision(token_ids[index], token_ids, allocation.counts)


def build_manifest(
    reference_token_ids: tuple[int, ...], local_token_ids: tuple[int, ...]
) -> ReplayManifest:
    if not reference_token_ids or len(reference_token_ids) != len(local_token_ids):
        raise ValueError("reference and local token sequences must have equal positive length")
    corrections = tuple(
        ReplayCorrection(step, reference)
        for step, (reference, local) in enumerate(
            zip(reference_token_ids, local_token_ids, strict=True)
        )
        if reference != local
    )
    return ReplayManifest(len(reference_token_ids), corrections)


def manifest_payload_sizes(
    manifest: ReplayManifest, *, vocabulary_size: int
) -> tuple[int, int]:
    """Return sparse and full token payload sizes, excluding a shared header."""

    if vocabulary_size < 2:
        raise ValueError("vocabulary size must be at least two")
    token_bytes = max(1, ceil(log2(vocabulary_size) / 8))
    step_bytes = max(1, ceil(log2(max(2, manifest.token_count)) / 8))
    sparse = len(manifest.corrections) * (step_bytes + token_bytes)
    full = manifest.token_count * token_bytes
    return sparse, full
