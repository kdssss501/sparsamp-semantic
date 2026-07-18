from __future__ import annotations

from scripts.audit_precision_contract import compare_snapshots


def _snapshot(probabilities: list[float]) -> dict[str, object]:
    return {
        "token_ids": [10, 20, 30, 40],
        "probabilities": probabilities,
        "source_mass": 0.95,
    }


def test_integer_contract_can_absorb_drift_that_decimal_contract_records() -> None:
    result = compare_snapshots(
        _snapshot([0.4, 0.3, 0.2, 0.1]),
        _snapshot([0.400000001, 0.299999999, 0.200000001, 0.099999999]),
        mass_bits=(16,),
        preserve_support=True,
    )

    assert result["candidate_order_equal"]
    assert not result["contracts_exact"]["decimal_1e-15"]
    assert result["contracts_exact"]["integer_16"]


def test_candidate_churn_prevents_exact_contract_match() -> None:
    changed = _snapshot([0.4, 0.3, 0.2, 0.1])
    changed["token_ids"] = [10, 20, 30, 99]
    result = compare_snapshots(
        _snapshot([0.4, 0.3, 0.2, 0.1]),
        changed,
        mass_bits=(16,),
        preserve_support=True,
    )

    assert result["candidate_jaccard"] == 0.6
    assert not result["contracts_exact"]["integer_16"]


def test_candidate_reordering_prevents_exact_interval_replay() -> None:
    changed = _snapshot([0.3, 0.4, 0.2, 0.1])
    changed["token_ids"] = [20, 10, 30, 40]
    result = compare_snapshots(
        _snapshot([0.4, 0.3, 0.2, 0.1]),
        changed,
        mass_bits=(16,),
        preserve_support=True,
    )

    assert result["candidate_jaccard"] == 1.0
    assert not result["candidate_order_equal"]
    assert not result["contracts_exact"]["integer_16"]
