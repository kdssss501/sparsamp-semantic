from copy import deepcopy

from scripts.analyze_bounded_decision_set import evaluate_row, shift_scores


def _source() -> dict[str, object]:
    return {
        "experiment_config": {
            "model": "mock",
            "contract_top_k": 2,
            "logit_quantum": 0.5,
            "mass_bits": 8,
            "temperature": 1.2,
        }
    }


def _row() -> dict[str, object]:
    return {
        "prompt_index": 1,
        "seed": 0,
        "prompt": "prompt",
        "reference_trace": {
            "trace_completed": True,
            "steps": [
                {
                    "step": 0,
                    "decision_token_id": 10,
                    "contract_counts": [240, 16],
                    "rank2_rank3_gap_bins": 8,
                    "envelope_token_ids": [10, 20, 30, 40],
                    "envelope_logit_bins": [0, -8, -16, -24],
                }
            ],
        },
        "comparison": {
            "steps": [
                {
                    "step": 0,
                    "decision_flip": True,
                    "cause": "support_flip",
                    "common_envelope_max_bin_shift": 1,
                }
            ],
        },
    }


def test_bounded_certificate_does_not_read_target_labels() -> None:
    row = _row()
    changed = deepcopy(row)
    changed["comparison"]["steps"][0]["decision_flip"] = False
    first = evaluate_row(_source(), row, bin_shift_radius=1, mass_radius=0, vocabulary_size=100)
    second = evaluate_row(_source(), changed, bin_shift_radius=1, mass_radius=0, vocabulary_size=100)
    assert first["certificate_steps"] == second["certificate_steps"]
    assert first["payload_bytes"] == second["payload_bytes"]
    assert first["actual_flip_steps"] != second["actual_flip_steps"]


def test_shift_score_is_prompt_level_maximum() -> None:
    row = _row()
    row["comparison"]["steps"].append({"common_envelope_max_bin_shift": 3})
    assert shift_scores([row]) == {1: 3}
