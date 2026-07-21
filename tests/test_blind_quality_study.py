from scripts.prepare_blind_quality_study import METHODS, assignment_for, build_packages


def report(field: str, prefix: str) -> dict:
    rows = []
    for index in range(20):
        rows.append(
            {
                "prompt_index": index,
                "seed": 0,
                "prompt": f"prompt-{index}",
                field: f"{prefix}-{index}",
            }
        )
    return {"phase": "completed", "rows": rows}


def test_assignment_is_deterministic_and_balanced_per_trial() -> None:
    key = bytes(range(32))
    first = assignment_for(key, 3)
    assert first == assignment_for(key, 3)
    assert set(first) == set(METHODS)


def test_build_packages_separates_participant_and_private_mapping() -> None:
    participant, private = build_packages(
        report("text", "native"),
        report("reference_text", "top2"),
        report("reference_text", "top4"),
        key=bytes(range(32)),
        source_hashes={"native": "a", "top2": "b", "top4": "c"},
    )
    assert participant["ethics_status"] == "ETHICS_PENDING"
    assert participant["trial_count"] == 20
    assert "key_hex" not in participant
    assert "mapping" not in str(participant)
    assert len(private["mappings"]) == 20
    for trial in participant["trials"]:
        assert {response["label"] for response in trial["responses"]} == {"A", "B", "C"}
