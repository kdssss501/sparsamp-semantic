from __future__ import annotations

from pathlib import Path

import pytest

from scripts.audit_dual_barrier_contracts import (
    compare_traces,
    experiment_config,
    initial_rows,
    load_checkpoint,
    reference_trace_matches_source,
    select_source_rows,
)
from scripts.audit_replay_certificate import config_signature, write_report


def source_report() -> dict[str, object]:
    return {
        "experiment_config": {
            "model": "mock",
            "device": "cpu",
            "reference_dtype": "float32",
            "replay_dtype": "float16",
            "envelope_top_k": 4,
            "contract_top_k": 2,
            "logit_quantum": 0.5,
            "mass_bits": 4,
            "temperature": 1.2,
        },
        "result_signature": "source-result",
        "rows": [
            {
                "prompt_index": prompt,
                "seed": seed,
                "policy": "seeded",
                "prompt": f"p{prompt}",
                "token_count": 1,
            }
            for prompt in range(2)
            for seed in range(2)
        ],
    }


def trace_step(
    *, choice: int, token_ids: list[int], counts: list[int], bins: list[int]
) -> dict[str, object]:
    return {
        "step": 0,
        "contract_token_ids": token_ids,
        "contract_counts": counts,
        "decision_token_id": choice,
        "envelope_token_ids": [1, 2, 3, 4],
        "envelope_logit_bins": bins,
        "rank2_rank3_gap_bins": bins[1] - bins[2],
    }


def test_selection_requires_exact_cartesian_matrix() -> None:
    source = source_report()
    selected = select_source_rows(source, prompt_indices=[0, 1], seeds=[0, 1])
    assert [tuple((row["prompt_index"], row["seed"])) for row in selected] == [
        (0, 0),
        (0, 1),
        (1, 0),
        (1, 1),
    ]
    with pytest.raises(ValueError, match="exact requested trial matrix"):
        select_source_rows(source, prompt_indices=[0, 2], seeds=[0])


def test_trace_comparison_attributes_support_flip_without_target_leakage() -> None:
    source = source_report()
    source_row = {
        "prompt": "p1",
        "prompt_index": 1,
        "seed": 0,
        "reference_token_ids": [2],
        "reference_contracts": [{"token_ids": [1, 2], "counts": [8, 8]}],
        "corrections": [{"step": 0, "token_id": 2}],
    }
    reference = {
        "trace_completed": True,
        "steps": [
            trace_step(choice=2, token_ids=[1, 2], counts=[8, 8], bins=[0, -1, -3, -4])
        ],
    }
    target = {
        "trace_completed": True,
        "steps": [
            trace_step(choice=3, token_ids=[1, 3], counts=[8, 8], bins=[0, -1, -2, -4])
        ],
    }
    result = compare_traces(source, source_row, reference, target)
    assert result["valid"]
    assert result["support_flips"] == 1
    assert result["mass_flips"] == 0
    assert result["steps"][0]["reference_rank2_rank3_gap_bins"] == 2
    assert result["steps"][0]["reference_boundary_slack"] is not None


def test_reference_gate_checks_saved_contract_and_public_choice() -> None:
    source_row = {
        "reference_token_ids": [2],
        "reference_contracts": [{"token_ids": [1, 2], "counts": [8, 8]}],
    }
    trace = {
        "trace_completed": True,
        "steps": [
            trace_step(choice=2, token_ids=[1, 2], counts=[8, 8], bins=[0, -1, -3, -4])
        ],
    }
    assert reference_trace_matches_source(source_row, trace)
    trace["steps"][0]["contract_counts"] = [9, 7]
    assert not reference_trace_matches_source(source_row, trace)


def test_checkpoint_rejects_configuration_drift(tmp_path: Path) -> None:
    source_path = tmp_path / "source.json"
    source_path.write_text("source", encoding="utf-8")
    source = source_report()
    selected = select_source_rows(source, prompt_indices=[0], seeds=[0])
    config = experiment_config(source_path, source, selected, run_label="smoke")
    rows = initial_rows(selected)
    report = {
        "experiment_config": config,
        "experiment_signature": config_signature(config),
        "rows": rows,
    }
    output = tmp_path / "checkpoint.json"
    write_report(output, report)
    assert load_checkpoint(output, config) == rows
    with pytest.raises(ValueError, match="configuration mismatch"):
        load_checkpoint(output, {**config, "run_label": "changed"})
