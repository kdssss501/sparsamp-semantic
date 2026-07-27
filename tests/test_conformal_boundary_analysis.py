from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.analyze_conformal_boundary_certificate import (
    decision,
    evaluate_row,
    prompt_scores,
    split_prompt_rows,
)


def _split_rows() -> list[dict[str, object]]:
    return [
        {"prompt_index": prompt_index, "seed": seed}
        for prompt_index in range(20)
        for seed in range(3)
    ]


def test_frozen_split_uses_even_calibration_and_odd_heldout_prompts() -> None:
    calibration, heldout = split_prompt_rows(_split_rows())
    assert {int(row["prompt_index"]) for row in calibration} == set(range(0, 20, 2))
    assert {int(row["prompt_index"]) for row in heldout} == set(range(1, 20, 2))


def test_frozen_split_rejects_missing_or_duplicate_seed() -> None:
    rows = _split_rows()
    rows[-1] = {"prompt_index": 19, "seed": 1}
    with pytest.raises(ValueError, match="exactly seeds 0, 1, and 2"):
        split_prompt_rows(rows)


def test_prompt_score_is_cluster_maximum_across_three_seeds(monkeypatch) -> None:
    rows = [
        {"prompt_index": 4, "seed": 0, "test_score": 2},
        {"prompt_index": 4, "seed": 1, "test_score": 9},
        {"prompt_index": 4, "seed": 2, "test_score": 5},
    ]
    monkeypatch.setattr(
        "scripts.analyze_conformal_boundary_certificate.row_score",
        lambda _source, row: int(row["test_score"]),
    )
    assert prompt_scores({}, rows) == {4: 9}


def test_heldout_corrections_do_not_change_reference_certificate() -> None:
    source = {
        "experiment_config": {
            "contract_top_k": 2,
            "logit_quantum": 0.5,
            "mass_bits": 4,
            "temperature": 1.2,
            "model": "mock",
            "vocabulary_size": 32,
        }
    }
    base = {
        "prompt_index": 1,
        "prompt": "held-out",
        "seed": 0,
        "policy": "seeded",
        "reference_token_ids": [3, 4],
        "reference_contracts": [{"counts": [8, 8]}, {"counts": [8, 8]}],
        "corrections": [{"step": 0, "token_id": 3}],
        "sparse_payload_bytes": 8,
    }
    changed_target = deepcopy(base)
    changed_target["corrections"] = [{"step": 1, "token_id": 4}]

    first = evaluate_row(source, base, radius=2)
    second = evaluate_row(source, changed_target, radius=2)

    assert first["ambiguous_steps"] == second["ambiguous_steps"]
    assert first["certificate_payload_bytes"] == second["certificate_payload_bytes"]
    assert first["false_safe_steps"] != second["false_safe_steps"]


@pytest.mark.parametrize(
    ("exact_prompts", "ratio", "expansion", "expected"),
    [
        (10, 0.49, 2.0, "strong_go"),
        (10, 0.49, 2.01, "pilot_go"),
        (9, 0.49, 5.0, "pilot_go"),
        (8, 0.49, 1.0, "no_go"),
        (10, 0.50, 1.0, "no_go"),
    ],
)
def test_prespecified_decision_rule(
    exact_prompts: int, ratio: float, expansion: float, expected: str
) -> None:
    summary = {
        "exact_prompts": exact_prompts,
        "certificate_to_full_ratio": ratio,
        "certificate_to_target_specific_ratio": expansion,
    }
    assert decision(summary) == expected
