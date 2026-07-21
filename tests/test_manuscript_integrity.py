import json
from pathlib import Path

from scripts.audit_manuscript_integrity import (
    audit,
    citation_numbers,
    sha256,
    valid_figure_package,
)


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


def test_figure_package_requires_per_figure_traceability(tmp_path: Path) -> None:
    figures = tmp_path / "paper" / "figures"
    figures.mkdir(parents=True)
    (figures / "figure_01_test.pdf").write_bytes(b"pdf")
    (figures / "figure_01_test.png").write_bytes(b"png")
    source = tmp_path / "paper" / "source.csv"
    source.write_text("value\n1\n", encoding="utf-8")
    script = tmp_path / "render.py"
    script.write_text("print('render')\n", encoding="utf-8")
    figure = {
        "artifact_id": "fig-1",
        "source_data": "paper/source.csv",
        "transformation": {
            "script": "render.py",
            "sha256": sha256(script),
            "operation": "test render",
        },
        "caption_claim": "Caption claim.",
        "supported_manuscript_claims": [
            {"claim": "Supported claim.", "locator": "Results"}
        ],
        "limitations": [],
    }
    assert valid_figure_package(tmp_path, figure, "Supported claim.")
    del figure["transformation"]
    assert not valid_figure_package(tmp_path, figure, "Supported claim.")
