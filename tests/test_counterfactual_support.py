from sparsamp_semantic.counterfactual_support import nearest_challenger_witness
from sparsamp_semantic.replay_certificate import ReplayContractConfig, decision_context


def _context() -> tuple[bytes, ReplayContractConfig]:
    config = ReplayContractConfig(logit_quantum=0.5, mass_bits=8, temperature=1.2)
    return decision_context("mock", "prompt", config), config


def test_nearest_challenger_skips_a_stable_support_boundary() -> None:
    context, config = _context()
    result = nearest_challenger_witness(
        (10, 20, 30), (0, -1, -4), 10,
        step=0, context=context, config=config, support_gap_bins=1,
    )
    assert result.rank2_rank3_gap_bins == 3
    assert result.challenger_eligible is False
    assert result.counterfactual_token_id is None
    assert result.decision_sensitive is False


def test_nearest_challenger_is_decision_conditioned() -> None:
    context, config = _context()
    sensitive = []
    for step in range(64):
        result = nearest_challenger_witness(
            (10, 20, 30), (0, 0, 0), 10,
            step=step, context=context, config=config, support_gap_bins=0,
        )
        sensitive.append(result)
    assert all(item.challenger_eligible for item in sensitive)
    assert any(item.decision_sensitive for item in sensitive)
    assert any(not item.decision_sensitive for item in sensitive)


def test_nearest_challenger_rejects_invalid_envelopes() -> None:
    context, config = _context()
    try:
        nearest_challenger_witness(
            (10, 20), (0, -1), 10,
            step=0, context=context, config=config, support_gap_bins=0,
        )
    except ValueError as error:
        assert "top-3" in str(error)
    else:
        raise AssertionError("short envelope must be rejected")
