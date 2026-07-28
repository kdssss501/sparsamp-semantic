from scripts.analyze_independent_bounded_decision import confirmation_decision


def _summary(exact: int, ratio: float = 0.8) -> dict[str, float | int]:
    return {"exact_trials": exact, "to_dual_ratio": ratio}


def test_confirmation_decision_requires_each_seed_and_lower_cost() -> None:
    assert confirmation_decision({1: _summary(20), 2: _summary(20)}, _summary(40)) == "confirmation_strong_go"
    assert confirmation_decision({1: _summary(18), 2: _summary(19)}, _summary(37)) == "confirmation_pilot_go"
    assert confirmation_decision({1: _summary(17), 2: _summary(20)}, _summary(37)) == "no_go"
    assert confirmation_decision({1: _summary(20), 2: _summary(20)}, _summary(40, 1.0)) == "no_go"
