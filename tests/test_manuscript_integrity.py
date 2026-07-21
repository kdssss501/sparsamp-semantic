import json
from pathlib import Path

from scripts.audit_manuscript_integrity import audit, citation_numbers


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def test_citation_numbers_expand_groups_and_ranges() -> None:
    assert citation_numbers("Claims [1], [3,4] and [7-9].") == {1, 3, 4, 7, 8, 9}


def test_audit_fails_when_required_claims_are_missing(tmp_path: Path) -> None:
    manuscript = tmp_path / "paper.md"
    manuscript.write_text("## References\n1. One\n", encoding="utf-8")
    scale = tmp_path / "scale.json"
    write_json(
        scale,
        {
            "groups": {
                "overall": {
                    "trials": 60,
                    "corrected_exact": 60,
                    "uncorrected_exact": 10,
                    "sentence_complete": 58,
                    "correction_rate": {
                        "mean": 0.0216,
                        "ci95_low": 0.018,
                        "ci95_high": 0.0253,
                    },
                }
            }
        },
    )
    cost = tmp_path / "cost.json"
    write_json(
        cost,
        {
            "serialization": {
                "payload_ratio": 0.0665,
                "referenced_package_ratio": 0.2476,
                "complete_package_ratio": 0.6389,
            }
        },
    )
    trace = tmp_path / "trace.json"
    write_json(trace, {"inputs": {}, "transformation": {"script": "missing", "sha256": "x"}, "figures": []})
    report = audit(manuscript, scale, cost, trace)
    assert report["summary"]["status"] == "FAIL"
    assert report["summary"]["failed"] > 0
