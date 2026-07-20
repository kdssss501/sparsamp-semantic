from __future__ import annotations

from types import SimpleNamespace
from typing import Hashable

import pytest

from scripts.audit_bin_mass_failure_modes import (
    SOURCE_SCHEMA,
    build_report,
    diagnostic_config,
    load_checkpoint_rows,
    load_source_report,
    summarize,
    trace_contract,
)
from scripts.audit_byte_sliced_messages import config_signature, write_report
from sparsamp_semantic.providers.base import ProviderSession
from sparsamp_semantic.types import DistributionSnapshot, TokenCandidate


def snapshot(support: tuple[int, ...], counts: tuple[int, ...]) -> DistributionSnapshot:
    total = sum(counts)
    return DistributionSnapshot(
        candidates=tuple(
            TokenCandidate(
                token_id=token_id,
                text=str(token_id),
                probability=count / total,
                rank=rank,
            )
            for rank, (token_id, count) in enumerate(zip(support, counts, strict=True))
        ),
        metadata={"bin_mass_counts": dict(zip(support, counts, strict=True))},
    )


class TraceSession(ProviderSession):
    def __init__(self, snapshots: list[DistributionSnapshot]) -> None:
        self.snapshots = snapshots
        self.generated: list[int] = []
        self.last_support: set[int] = set()

    @property
    def context_id(self) -> bytes:
        return b"trace"

    @property
    def generated_token_ids(self) -> tuple[Hashable, ...]:
        return tuple(self.generated)

    def next_distribution(self) -> DistributionSnapshot:
        current = self.snapshots[len(self.generated)]
        self.last_support = {int(candidate.token_id) for candidate in current.candidates}
        return current

    def append(self, token_id: Hashable) -> None:
        if token_id not in self.last_support:
            raise ValueError("outside support")
        self.generated.append(int(token_id))

    def render(self) -> str:
        return ""


def source_report() -> dict[str, object]:
    config = {
        "model": "models/gpt2",
        "device": "cuda",
        "reference_dtype": "float32",
        "replay_dtype": "float16",
        "top_p": 1.0,
        "top_k": 2,
        "logit_quantum": 0.5,
        "bin_mass_bits": 16,
        "temperature": 1.2,
        "trial_keys": [[0, 0, 16, 0]],
    }
    return {"experiment_signature": "source-signature", "experiment_config": config, "rows": [{}]}


def diagnostic_row(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "prompt_index": 0,
        "payload_seed": 0,
        "window_tokens": 16,
        "parity_bytes": 0,
        "variant": "window=16,parity=0",
        "same_precision_success": True,
        "cross_precision_success": False,
        "source_same_outcome_match": True,
        "source_cross_outcome_match": True,
        "same_precision_records": [
            {"completed": True, "singleton_step": 7},
            {"completed": False, "singleton_step": None},
        ],
        "contract_trace": {
            "first_support_divergence_step": 10,
            "first_count_divergence_step": 4,
            "first_replay_rejection_step": 12,
            "full_support_agreement": False,
            "full_count_agreement": False,
            "trace_fraction": 0.75,
        },
    }
    values.update(overrides)
    return values


def test_trace_contract_separates_count_support_and_rejection() -> None:
    reference = TraceSession(
        [
            snapshot((1, 2), (4, 4)),
            snapshot((1, 2), (4, 4)),
            snapshot((1, 2), (4, 4)),
            snapshot((1, 2), (4, 4)),
        ]
    )
    replay = TraceSession(
        [
            snapshot((1, 2), (4, 4)),
            snapshot((1, 2), (5, 3)),
            snapshot((1, 3), (4, 4)),
            snapshot((1, 3), (4, 4)),
        ]
    )

    result = trace_contract(reference, replay, [1, 1, 1, 2])

    assert result["first_count_divergence_step"] == 1
    assert result["first_support_divergence_step"] == 2
    assert result["first_replay_rejection_step"] == 3
    assert result["appended_tokens"] == 3
    assert not result["full_trace"]
    assert [event["step"] for event in result["events"]] == [1, 2, 3]


def test_summary_reports_right_censored_singleton_completion() -> None:
    result = summarize([diagnostic_row()])["window=16,parity=0"]

    assert result["symbols"] == 2
    assert result["same_precision_completed_symbols"] == 1
    assert result["same_precision_symbol_completion_rate"] == 0.5
    assert result["singleton_completion_cdf"][6] == 0.0
    assert result["singleton_completion_cdf"][7] == 0.5
    assert result["median_first_count_divergence_step"] == 4


def test_checkpoint_requires_exact_source_hash_and_rejects_duplicates(tmp_path) -> None:
    source = tmp_path / "source.json"
    source.write_text("source", encoding="utf-8")
    args = SimpleNamespace(run_label="R036-D1")
    report = source_report()
    row = diagnostic_row()
    output = tmp_path / "checkpoint.json"
    write_report(output, build_report(args, source, report, [row], "partial"))
    expected = diagnostic_config(args, source, report)

    assert load_checkpoint_rows(output, expected) == [row]
    with pytest.raises(ValueError, match="does not match"):
        load_checkpoint_rows(output, {**expected, "source_sha256": "changed"})

    duplicate_report = build_report(args, source, report, [row, dict(row)], "partial")
    duplicate_report["experiment_signature"] = config_signature(
        duplicate_report["experiment_config"]
    )
    write_report(output, duplicate_report)
    with pytest.raises(ValueError, match="duplicate"):
        load_checkpoint_rows(output, expected)


def test_checkpoint_rejects_trial_outside_source_matrix(tmp_path) -> None:
    source = tmp_path / "source.json"
    source.write_text("source", encoding="utf-8")
    args = SimpleNamespace(run_label="R036-D1")
    report = source_report()
    output = tmp_path / "outside.json"
    row = diagnostic_row(payload_seed=9)
    write_report(output, build_report(args, source, report, [row], "partial"))

    with pytest.raises(ValueError, match="outside"):
        load_checkpoint_rows(output, diagnostic_config(args, source, report))


def test_source_report_requires_completed_signed_exact_matrix(tmp_path) -> None:
    config = {"trial_keys": [[0, 0, 16, 0]]}
    report = {
        "schema": SOURCE_SCHEMA,
        "phase": "completed",
        "experiment_config": config,
        "experiment_signature": config_signature(config),
        "rows": [
            {
                "prompt_index": 0,
                "payload_seed": 0,
                "window_tokens": 16,
                "parity_bytes": 0,
            }
        ],
    }
    path = tmp_path / "source.json"
    write_report(path, report)
    assert load_source_report(path) == report

    report["experiment_signature"] = "0" * 64
    write_report(path, report)
    with pytest.raises(ValueError, match="signature"):
        load_source_report(path)
