from scripts.analyze_unquantized_delta import analyze


def row(
    index: int, sprc_rate: float, top2_rate: float, top16_rate: float
) -> tuple[dict, dict]:
    shared = {
        "prompt_index": index,
        "seed": 0,
        "policy": "seeded",
        "reference_token_sha256": f"hash-{index}",
        "token_count": 10,
    }
    sprc = {**shared, "correction_rate": sprc_rate}
    unquantized = {
        **shared,
        "completed": True,
        "variants": {
            "top_2": {"correction_rate": top2_rate},
            "top_16": {"correction_rate": top16_rate},
        },
    }
    return sprc, unquantized


def test_analysis_pairs_trials_and_reports_delta() -> None:
    pairs = [row(0, 0.1, 0.2, 0.4), row(1, 0.2, 0.2, 0.5)]
    sprc = {"phase": "completed", "rows": [item[0] for item in pairs]}
    unquantized = {
        "phase": "completed",
        "rows": [item[1] for item in pairs],
        "summary": {
            "top_2": {
                "trials": 2,
                "tokens": 20,
                "exact_recovery": 2,
                "mean_correction_rate": 0.2,
                "referenced_package_bytes": 1200,
                "bits_per_token": 8.0,
                "support_shortfall_steps": 0,
                "reference_outside_support_steps": 0,
                "minimum_available_support": 2,
            },
            "top_16": {
                "trials": 2,
                "tokens": 20,
                "exact_recovery": 2,
                "mean_correction_rate": 0.45,
                "referenced_package_bytes": 2000,
                "bits_per_token": 12.0,
                "support_shortfall_steps": 1,
                "reference_outside_support_steps": 0,
                "minimum_available_support": 5,
            },
        },
    }

    result = analyze(sprc, unquantized, repetitions=100, seed=7)

    assert result["matched_trials"] == 2
    assert result["variants"]["top_2"]["correction_rate_delta_vs_sprc"] == 0.05
    assert result["variants"]["top_2"]["package_byte_delta_vs_sprc"] == 52
