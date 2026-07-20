from __future__ import annotations

from typing import Hashable

from scripts.audit_contract_list_oracle import beam_upper_bound, summarize, trace_oracle
from sparsamp_semantic.providers.base import ProviderSession
from sparsamp_semantic.types import DistributionSnapshot, TokenCandidate


def snap(tokens: list[int], bins: list[int]) -> DistributionSnapshot:
    return DistributionSnapshot(
        candidates=tuple(TokenCandidate(token_id=t, text=str(t), probability=0.25, rank=i) for i, t in enumerate(tokens)),
        metadata={"quantized_logit_bins": dict(zip(tokens, bins, strict=True))},
    )


class Session(ProviderSession):
    def __init__(self, snapshots: list[DistributionSnapshot]) -> None:
        self.snapshots = snapshots
        self.items: list[int] = []
        self.support: set[int] = set()

    @property
    def context_id(self) -> bytes:
        return b"oracle"

    @property
    def generated_token_ids(self) -> tuple[Hashable, ...]:
        return tuple(self.items)

    def next_distribution(self) -> DistributionSnapshot:
        value = self.snapshots[len(self.items)]
        self.support = {int(candidate.token_id) for candidate in value.candidates}
        return value

    def append(self, token_id: Hashable) -> None:
        assert token_id in self.support
        self.items.append(int(token_id))

    def render(self) -> str:
        return ""


def test_oracle_finds_minimum_support_and_bin_envelope() -> None:
    reference = Session([snap([1, 2, 3, 4], [0, -1, -3, -4])])
    replay = Session([snap([1, 3, 2, 4], [0, -2, -2, -4])])
    result = trace_oracle(reference, replay, [1], [2, 4], [0, 1], 0.5, 1.2, 16)
    assert result["trajectory_minimum_top_k"] == 3
    assert result["trajectory_minimum_bin_radius"] == 1
    assert not result["coverage"]["K=2,r=1"]
    assert result["coverage"]["K=4,r=1"]


def test_summary_selects_smallest_oracle_beam() -> None:
    rows = []
    for index in range(6):
        rows.append({
            "variant": "window=32,parity=0", "prompt_index": index, "payload_seed": 0,
            "window_tokens": 32, "parity_bytes": 0,
            "oracle_trace": {"full_trace": True, "coverage": {"K=2,r=0": False, "K=2,r=1": index < 5, "K=4,r=0": index < 5, "K=4,r=1": True}},
        })
    result = summarize(rows, [2, 4], [0, 1])
    assert result["overall_oracle_go"]
    assert result["selected"]["top_k"] == 4
    assert result["selected"]["bin_radius"] == 0
    assert beam_upper_bound(2, 1) == 9
