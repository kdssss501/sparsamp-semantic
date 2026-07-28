from sparsamp_semantic.bounded_decision_set import bounded_decision_witness
from sparsamp_semantic.replay_certificate import ReplayContractConfig, decision_context


def _context() -> tuple[bytes, ReplayContractConfig]:
    config = ReplayContractConfig(logit_quantum=0.5, mass_bits=8, temperature=1.2)
    return decision_context("mock", "prompt", config), config


def test_bounded_decision_is_invariant_for_a_large_margin() -> None:
    context, config = _context()
    result = bounded_decision_witness(
        (10, 20, 30, 40), (0, -8, -16, -24), 10,
        step=0, context=context, config=config, bin_shift_radius=1,
    )
    assert result.possible_token_ids == (10,)
    assert result.feasible_pair_count == 1
    assert result.unknown_tail_possible is False
    assert result.decision_invariant is True


def test_bounded_decision_marks_a_tied_support_as_non_invariant() -> None:
    context, config = _context()
    witnesses = [
        bounded_decision_witness(
            (10, 20, 30, 40), (0, 0, 0, -8), 10,
            step=step, context=context, config=config, bin_shift_radius=1,
        )
        for step in range(16)
    ]
    assert any(not item.decision_invariant for item in witnesses)
    assert all(item.feasible_pair_count >= 3 for item in witnesses)


def test_bounded_decision_marks_a_possible_tail_as_unsafe() -> None:
    context, config = _context()
    result = bounded_decision_witness(
        (10, 20, 30), (0, -1, -2), 10,
        step=0, context=context, config=config, bin_shift_radius=1,
    )
    assert result.unknown_tail_possible is True
    assert result.decision_invariant is False
