import json

from scripts.analyze_independent_bounded_decision import (
    _r058_signature_payload,
    confirmation_decision,
)
from sparsamp_semantic.replay_package import canonical_signature


def _summary(exact: int, ratio: float = 0.8) -> dict[str, float | int]:
    return {"exact_trials": exact, "to_dual_ratio": ratio}


def test_confirmation_decision_requires_each_seed_and_lower_cost() -> None:
    assert confirmation_decision({1: _summary(20), 2: _summary(20)}, _summary(40)) == "confirmation_strong_go"
    assert confirmation_decision({1: _summary(18), 2: _summary(19)}, _summary(37)) == "confirmation_pilot_go"
    assert confirmation_decision({1: _summary(17), 2: _summary(20)}, _summary(37)) == "no_go"
    assert confirmation_decision({1: _summary(20), 2: _summary(20)}, _summary(40, 1.0)) == "no_go"


def test_r058_signature_survives_integer_key_json_round_trip() -> None:
    result = {
        "schema": "sparsamp-r058-bounded-decision-set-v1",
        "calibration_scores": {"bin_shift": {0: 1, 2: 1, 10: 1}},
    }
    result["result_signature"] = canonical_signature(result)
    restored = json.loads(json.dumps(result))
    assert canonical_signature(_r058_signature_payload(restored)) == result["result_signature"]
