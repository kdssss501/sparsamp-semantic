from __future__ import annotations

from copy import deepcopy

from scripts.analyze_dual_barrier_certificate import (
    calibration_scores,
    decision,
    evaluate_row,
    split_rows,
)


def _source() -> dict[str, object]:
    return {
        "experiment_config": {
            "model": "mock",
            "contract_top_k": 2,
            "logit_quantum": 0.5,
            "mass_bits": 4,
            "temperature": 1.2,
        }
    }


def _row(prompt_index: int, cause: str, *, gap: int, slack: int) -> dict[str, object]:
    return {
        "prompt_index": prompt_index,
        "seed": 0,
        "prompt": f"prompt-{prompt_index}",
        "reference_trace": {
            "trace_completed": True,
            "steps": [
                {
                    "step": 0,
                    "decision_token_id": 11,
                    "contract_counts": [8, 8],
                    "rank2_rank3_gap_bins": gap,
                },
                {
                    "step": 1,
                    "decision_token_id": 12,
                    "contract_counts": [8, 8],
                    "rank2_rank3_gap_bins": 9,
                },
            ]
        },
        "comparison": {
            "steps": [
                {
                    "step": 0,
                    "decision_flip": True,
                    "cause": cause,
                    "reference_rank2_rank3_gap_bins": gap,
                    "reference_boundary_slack": slack,
                },
                {
                    "step": 1,
                    "decision_flip": False,
                    "cause": "no_flip",
                    "reference_rank2_rank3_gap_bins": 9,
                    "reference_boundary_slack": 9,
                },
            ],
            "valid": True,
        },
    }


def test_even_odd_split_and_stratified_scores() -> None:
    rows = [
        _row(index, "support_flip" if index % 2 == 0 else "mass_flip", gap=index, slack=10 + index)
        for index in range(20)
    ]
    calibration, heldout = split_rows(rows)
    assert [row["prompt_index"] for row in calibration] == list(range(0, 20, 2))
    assert [row["prompt_index"] for row in heldout] == list(range(1, 20, 2))
    scores = calibration_scores(calibration)
    assert scores["support"][18] == 18
    assert scores["mass"][18] == 0
    assert scores["boundary_only"][18] == 29


def test_heldout_target_labels_do_not_change_certificate_construction() -> None:
    row = _row(1, "support_flip", gap=1, slack=8)
    changed = deepcopy(row)
    changed["comparison"]["steps"][0]["cause"] = "mass_flip"
    changed["comparison"]["steps"][0]["decision_flip"] = False
    first = evaluate_row(
        _source(),
        row,
        support_gap=1,
        mass_radius=2,
        boundary_radius=5,
        vocabulary_size=100,
    )
    second = evaluate_row(
        _source(),
        changed,
        support_gap=1,
        mass_radius=2,
        boundary_radius=5,
        vocabulary_size=100,
    )
    assert first["dual_certificate_steps"] == second["dual_certificate_steps"]
    assert first["dual_payload_bytes"] == second["dual_payload_bytes"]
    assert first["actual_flip_steps"] != second["actual_flip_steps"]


def test_prespecified_decision_rule() -> None:
    assert decision({"exact_trials": 10, "dual_to_full_ratio": 0.4, "dual_to_boundary_ratio": 0.5}) == "strong_go"
    assert decision({"exact_trials": 9, "dual_to_full_ratio": 0.4, "dual_to_boundary_ratio": 0.8}) == "pilot_go"
    assert decision({"exact_trials": 8, "dual_to_full_ratio": 0.4, "dual_to_boundary_ratio": 0.4}) == "no_go"
