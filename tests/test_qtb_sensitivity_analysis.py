from scripts.analyze_qtb_sensitivity import referenced_package_bytes


def make_row(prompt_index: int, corrections: list[dict]) -> dict:
    return {
        "prompt_index": prompt_index,
        "seed": 0,
        "policy": "seeded",
        "token_count": 10,
        "reference_token_sha256": f"{prompt_index:064x}",
        "corrections": corrections,
    }


def test_referenced_package_has_fixed_header_and_grows_with_corrections() -> None:
    empty = referenced_package_bytes([make_row(0, [])])
    corrected = referenced_package_bytes(
        [make_row(0, [{"step": 3, "token_id": 42}])]
    )
    assert empty > 101
    assert corrected > empty


def test_referenced_package_accumulates_trial_records() -> None:
    one = referenced_package_bytes([make_row(0, [])])
    two = referenced_package_bytes([make_row(0, []), make_row(1, [])])
    assert two > one
