from copy import deepcopy

from scripts.analyze_counterfactual_support_screen import evaluate_row


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
                    "contract_counts": [128, 128],
                    "rank2_rank3_gap_bins": 0,
                    "envelope_token_ids": [10, 20, 30],
                    "envelope_logit_bins": [0, 0, 0],
                }
            ],
        },
        "comparison": {
            "steps": [
                {"step": 0, "decision_flip": True, "cause": "support_flip"}
            ],
        },
    }


def test_counterfactual_certificate_does_not_read_target_labels() -> None:
    row = _row()
    changed = deepcopy(row)
    changed["comparison"]["steps"][0]["decision_flip"] = False
    first = evaluate_row(_source(), row, support_gap_bins=0, mass_radius=0, vocabulary_size=100)
    second = evaluate_row(_source(), changed, support_gap_bins=0, mass_radius=0, vocabulary_size=100)
    assert first["certificate_steps"] == second["certificate_steps"]
    assert first["payload_bytes"] == second["payload_bytes"]
    assert first["actual_flip_steps"] != second["actual_flip_steps"]
