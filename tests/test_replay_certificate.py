from __future__ import annotations

from sparsamp_semantic.replay_certificate import (
    ReplayContractConfig,
    build_manifest,
    contract_decision,
    decision_context,
    manifest_payload_sizes,
)
from sparsamp_semantic.types import DistributionSnapshot, TokenCandidate


def snapshot(bins: dict[int, int]) -> DistributionSnapshot:
    ranked = [10, 20, 30]
    return DistributionSnapshot(
        candidates=tuple(
            TokenCandidate(token_id, str(token_id), 1 / 3, rank=rank)
            for rank, token_id in enumerate(ranked)
        ),
        metadata={"quantized_logit_bins": bins},
    )


def test_seeded_contract_decision_is_exactly_reproducible() -> None:
    config = ReplayContractConfig(public_seed=7)
    context = decision_context("mock", "prompt", config)
    first = contract_decision(snapshot({10: 0, 20: -1, 30: -2}), 3, context, config)
    second = contract_decision(snapshot({10: 0, 20: -1, 30: -2}), 3, context, config)
    assert first == second
    assert first.token_id in {10, 20}
    assert sum(first.counts) == 1 << 16


def test_contract_uses_ranked_top_k_then_public_token_order() -> None:
    config = ReplayContractConfig()
    context = decision_context("mock", "prompt", config)
    value = snapshot({10: 0, 20: 0, 30: 10})
    decision = contract_decision(value, 0, context, config, policy="greedy")
    assert decision.token_ids == (10, 20)
    assert decision.token_id == 10


def test_sparse_manifest_records_only_explicit_mismatches() -> None:
    manifest = build_manifest((1, 2, 3, 4), (1, 9, 3, 8))
    assert [(item.step, item.token_id) for item in manifest.corrections] == [(1, 2), (3, 4)]
    assert tuple(manifest.apply(step, token) for step, token in enumerate((1, 9, 3, 8))) == (
        1,
        2,
        3,
        4,
    )


def test_manifest_payload_size_compares_sparse_and_full_records() -> None:
    manifest = build_manifest(tuple(range(64)), tuple([99] + list(range(1, 64))))
    sparse, full = manifest_payload_sizes(manifest, vocabulary_size=50257)
    assert sparse == 3
    assert full == 128
