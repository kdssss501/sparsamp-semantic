from __future__ import annotations

from fractions import Fraction
from math import isclose, log

from sparsamp_semantic.rrc_theory import (
    inverse_rotate,
    kl_divergence_nats,
    kl_truncation_quantization_decomposition,
    no_wrap_recovery_certificate,
    paper_failure_region,
    paper_stop_counterexample,
    positive_mod,
    rotate,
    round_half_down,
    same_inverse_branch,
    stopped_process_counterexample,
    verified_stop,
)


def test_positive_mod_uses_half_open_representative() -> None:
    assert positive_mod(Fraction(-1, 4), Fraction(2)) == Fraction(7, 4)
    assert positive_mod(Fraction(2), Fraction(2)) == 0


def test_rotation_inverse_is_exact_on_rational_grid() -> None:
    left, right = Fraction(3), Fraction(5)
    for numerator in range(12):
        value = left + Fraction(numerator, 6)
        if value >= right:
            continue
        for offset in (Fraction(0), Fraction(1, 7), Fraction(1, 2), Fraction(6, 7)):
            assert inverse_rotate(rotate(value, left, right, offset), left, right, offset) == value


def test_round_half_down_matches_paper_definition() -> None:
    assert round_half_down(Fraction(5, 2)) == 2
    assert round_half_down(Fraction(25001, 10000)) == 3
    assert round_half_down(Fraction(24999, 10000)) == 2


def test_exact_two_step_counterexample_invalidates_paper_stop_implication() -> None:
    example = paper_stop_counterexample()

    assert example.rotated_secrets == (Fraction(3), Fraction(4))
    assert example.final_midpoint == Fraction(15, 4)
    assert Fraction(-1, 2) < example.paper_midpoint_error <= Fraction(1, 2)
    assert example.decoded_midpoint == Fraction(19, 4)
    assert example.decoded_message == 5
    assert example.decoded_message != example.message


def test_verified_stop_rejects_the_exact_paper_counterexample() -> None:
    example = paper_stop_counterexample()

    assert not verified_stop(
        example.message,
        example.final_midpoint,
        (example.initial_interval, example.first_token_interval),
        example.offsets,
    )


def test_counterexample_crosses_an_inverse_rotation_cut() -> None:
    example = paper_stop_counterexample()

    assert not same_inverse_branch(
        example.rotated_secrets[1],
        example.final_midpoint,
        *example.first_token_interval,
        example.offsets[1],
    )
    assert not no_wrap_recovery_certificate(
        example.message,
        example.rotated_secrets,
        example.final_midpoint,
        (example.initial_interval, example.first_token_interval),
        example.offsets,
    )


def test_no_wrap_certificate_is_sufficient_for_recovery() -> None:
    initial = (Fraction(0), Fraction(8))
    midpoint = Fraction(7, 2)

    assert no_wrap_recovery_certificate(
        3,
        (Fraction(3),),
        midpoint,
        (initial,),
        (Fraction(0),),
    )
    assert verified_stop(3, midpoint, (initial,), (Fraction(0),))


def test_positive_measure_offset_region_has_the_same_failure() -> None:
    region = paper_failure_region()
    initial = (Fraction(0), Fraction(8))
    first_interval = (Fraction(3), Fraction(5))
    final_interval = (Fraction(3), Fraction(9, 2))
    final_midpoint = sum(final_interval, start=Fraction(0)) / 2

    for first_index in range(17):
        first_offset = Fraction(first_index, 1024)
        for second_index in range(17):
            second_offset = Fraction(15, 32) + Fraction(second_index, 256)
            first_secret = rotate(Fraction(3), *initial, first_offset)
            second_secret = rotate(first_secret, *first_interval, second_offset)
            decoded = round_half_down(
                inverse_rotate(
                    inverse_rotate(
                        final_midpoint, *first_interval, second_offset
                    ),
                    *initial,
                    first_offset,
                )
            )

            assert first_interval[0] <= first_secret < first_interval[1]
            assert final_interval[0] <= second_secret < final_interval[1]
            assert Fraction(-1, 2) < final_midpoint - second_secret <= Fraction(1, 2)
            assert decoded == 5

    assert region.first_secret_range == (Fraction(3), Fraction(25, 8))
    assert region.second_secret_range == (Fraction(63, 16), Fraction(67, 16))
    assert region.midpoint_error_range == (Fraction(-7, 16), Fraction(-3, 16))
    assert region.first_reverse_range == (Fraction(75, 16), Fraction(77, 16))
    assert region.decoded_midpoint_range == (Fraction(73, 16), Fraction(77, 16))
    assert region.decoded_message == 5
    assert region.probability_lower_bound == Fraction(1, 1024)


def test_kl_decomposition_separates_truncation_from_quantization() -> None:
    result = kl_truncation_quantization_decomposition(
        source=(Fraction(1, 2), Fraction(3, 10), Fraction(1, 5)),
        retained_indices=(0, 1),
        implemented=(Fraction(3, 5), Fraction(2, 5)),
    )

    assert result.source_mass == Fraction(4, 5)
    assert result.quantization_kl_nats > 0
    assert isclose(
        result.total_kl_nats,
        result.truncation_kl_nats + result.quantization_kl_nats,
        rel_tol=1e-14,
        abs_tol=1e-14,
    )


def test_unquantized_conditioning_has_only_truncation_kl() -> None:
    result = kl_truncation_quantization_decomposition(
        source=(Fraction(1, 2), Fraction(3, 10), Fraction(1, 5)),
        retained_indices=(0, 1),
        implemented=(Fraction(5, 8), Fraction(3, 8)),
    )

    assert isclose(result.quantization_kl_nats, 0.0, abs_tol=1e-15)
    assert isclose(result.total_kl_nats, result.truncation_kl_nats, abs_tol=1e-15)


def test_forward_kl_is_infinite_when_truncation_removes_source_support() -> None:
    source = (Fraction(1, 2), Fraction(3, 10), Fraction(1, 5))
    truncated = (Fraction(5, 8), Fraction(3, 8), Fraction(0))

    assert kl_divergence_nats(source, truncated) == float("inf")
    assert isclose(
        kl_divergence_nats(truncated, source),
        -log(4 / 5),
        abs_tol=1e-15,
    )


def test_data_dependent_stopping_leaks_despite_matching_length_marginals() -> None:
    example = stopped_process_counterexample()

    assert example.stego_length_distribution == example.cover_length_distribution
    assert example.witness_event_stego_probability == Fraction(1, 2)
    assert example.witness_event_cover_probability == Fraction(1, 4)
    assert example.witness_advantage == Fraction(1, 4)
    assert example.total_variation == Fraction(1, 2)
