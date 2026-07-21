"""Audit manuscript claims against saved analysis artifacts and figure traces."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(checks: list[dict[str, Any]], name: str, passed: bool, detail: str) -> None:
    checks.append({"name": name, "pass": passed, "detail": detail})


def citation_numbers(text: str) -> set[int]:
    numbers = set()
    for group in re.findall(r"\[([0-9,\-\s]+)\]", text):
        for part in group.split(","):
            part = part.strip()
            if "-" in part:
                start, end = (int(value.strip()) for value in part.split("-", 1))
                numbers.update(range(start, end + 1))
            elif part:
                numbers.add(int(part))
    return numbers


def audit(
    manuscript: Path,
    scale_analysis: Path,
    cost_analysis: Path,
    figure_trace: Path,
    official_analysis: Path | None = None,
) -> dict[str, Any]:
    text = manuscript.read_text(encoding="utf-8")
    scale = json.loads(scale_analysis.read_text(encoding="utf-8"))
    cost = json.loads(cost_analysis.read_text(encoding="utf-8"))
    trace = json.loads(figure_trace.read_text(encoding="utf-8"))
    overall = scale["groups"]["overall"]
    serialization = cost["serialization"]
    checks: list[dict[str, Any]] = []

    expected_claims = {
        "corrected recovery": f"{overall['corrected_exact']} of {overall['trials']}",
        "uncorrected recovery": f"{overall['uncorrected_exact']} of {overall['trials']}",
        "mean correction rate": f"{100 * overall['correction_rate']['mean']:.2f}%",
        "correction interval": (
            f"{100 * overall['correction_rate']['ci95_low']:.2f}-"
            f"{100 * overall['correction_rate']['ci95_high']:.2f}%"
        ),
        "sentence completion": f"{overall['sentence_complete']} of {overall['trials']}",
        "payload ratio": f"{100 * serialization['payload_ratio']:.2f}%",
        "referenced package ratio": (
            f"{100 * serialization['referenced_package_ratio']:.2f}%"
        ),
        "self-contained package ratio": (
            f"{100 * serialization['complete_package_ratio']:.2f}%"
        ),
    }
    for name, value in expected_claims.items():
        check(checks, name, value in text, f"expected manuscript token: {value}")

    if official_analysis is not None:
        official = json.loads(official_analysis.read_text(encoding="utf-8"))
        official_acceptance = official["acceptance"]
        official_claims = {
            "official eligible decoding": (
                f"All {official_acceptance['decode_without_token_ambiguity']['trials']} completed trials without Token Ambiguity decoded exactly"
            ),
            "official capacity checks": (
                f"All {official_acceptance['capacity_within_tolerance']['checks']} capacity comparisons were within 5% relative error"
            ),
            "official budget boundary": (
                f"Of {official_acceptance['budget_completion']['configured']:,} configured trials, "
                f"{official_acceptance['budget_completion']['completed']:,} completed"
            ),
            "official status": "PASS_WITH_LIMITATIONS",
        }
        for name, value in official_claims.items():
            check(checks, name, value in text, f"expected manuscript token: {value}")
        raw_source = ROOT / official["source"]
        check(
            checks,
            "official raw checkpoint hash",
            raw_source.is_file() and sha256(raw_source) == official["source_sha256"],
            official["source"],
        )

    cited = citation_numbers(text)
    references = {
        int(value)
        for value in re.findall(r"^(\d+)\.\s", text, flags=re.MULTILINE)
    }
    check(
        checks,
        "citation numbering",
        cited == references == set(range(1, 10)),
        f"cited={sorted(cited)}, references={sorted(references)}",
    )

    required_boundaries = {
        "no zero-divergence claim": "do not establish target-independent determinism, zero distributional divergence or cross-hardware generality",
        "no human ratings": "no human ratings have been collected",
        "same-machine external replay": "same-machine smoke test rather than independent hardware evidence",
        "token-id boundary": "does not test recovery after public-text re-tokenization",
    }
    lowered = text.lower()
    for name, phrase in required_boundaries.items():
        check(checks, name, phrase.lower() in lowered, f"required boundary: {phrase}")

    trace_inputs = trace.get("inputs", {})
    for name, item in trace_inputs.items():
        path = ROOT / item["path"]
        passed = path.is_file() and sha256(path) == item["sha256"]
        check(checks, f"figure input hash: {name}", passed, item["path"])
    transformation = trace["transformation"]
    script_path = ROOT / transformation["script"]
    check(
        checks,
        "figure transformation hash",
        script_path.is_file() and sha256(script_path) == transformation["sha256"],
        transformation["script"],
    )
    for figure in trace["figures"]:
        number = int(str(figure["artifact_id"]).split("-")[-1])
        matching = list((ROOT / "paper/figures").glob(f"figure_{number:02d}_*.pdf"))
        matching_png = list((ROOT / "paper/figures").glob(f"figure_{number:02d}_*.png"))
        source = figure.get("source_data")
        source_ok = source is None or (ROOT / source).is_file()
        passed = len(matching) == 1 and len(matching_png) == 1 and source_ok
        check(checks, f"figure package: {number}", passed, str(figure))

    placeholders = text.count("AUTHOR_INPUT_NEEDED")
    failures = [item for item in checks if not item["pass"]]
    return {
        "schema": "manuscript-integrity-audit-v1",
        "manuscript": str(manuscript),
        "manuscript_sha256": sha256(manuscript),
        "checks": checks,
        "summary": {
            "passed": len(checks) - len(failures),
            "failed": len(failures),
            "author_placeholders": placeholders,
            "status": "PASS_WITH_AUTHOR_INPUT" if not failures and placeholders else (
                "PASS" if not failures else "FAIL"
            ),
        },
    }


def markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Manuscript Integrity Audit",
        "",
        f"**Status:** {summary['status']}",
        f"**Checks:** {summary['passed']} passed, {summary['failed']} failed",
        f"**Author placeholders:** {summary['author_placeholders']}",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for item in report["checks"]:
        detail = str(item["detail"]).replace("|", "\\|")
        lines.append(
            f"| {item['name']} | {'PASS' if item['pass'] else 'FAIL'} | {detail} |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This executable audit checks selected numerical tokens, source hashes, figure packages,",
            "citation numbering and mandatory limitation statements. It does not replace source-level",
            "citation verification, statistical review or author approval.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manuscript", type=Path, default=ROOT / "paper/MANUSCRIPT_DRAFT.md")
    parser.add_argument("--scale", type=Path, default=ROOT / "outputs/R044_qwen_replay_scale_analysis.json")
    parser.add_argument("--cost", type=Path, default=ROOT / "outputs/R049_cost_analysis.json")
    parser.add_argument("--figure-trace", type=Path, default=ROOT / "paper/source_data/figure_trace.json")
    parser.add_argument("--official", type=Path, default=ROOT / "docs/reproducibility/R002_OFFICIAL_ANALYSIS.json")
    parser.add_argument("--output", type=Path, default=ROOT / "paper/MANUSCRIPT_INTEGRITY.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "paper/MANUSCRIPT_INTEGRITY.md")
    args = parser.parse_args()
    report = audit(
        args.manuscript,
        args.scale,
        args.cost,
        args.figure_trace,
        args.official,
    )
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    args.markdown.write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    return 1 if report["summary"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
