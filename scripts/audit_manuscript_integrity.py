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


def valid_figure_package(root: Path, figure: dict[str, Any], text: str) -> bool:
    number = int(str(figure["artifact_id"]).split("-")[-1])
    matching = list((root / "paper/figures").glob(f"figure_{number:02d}_*.pdf"))
    matching_png = list((root / "paper/figures").glob(f"figure_{number:02d}_*.png"))
    source = figure.get("source_data")
    source_ok = isinstance(source, str) and (root / source).is_file()
    figure_transformation = figure.get("transformation", {})
    transform_path = root / figure_transformation.get("script", "")
    transform_ok = (
        transform_path.is_file()
        and figure_transformation.get("sha256") == sha256(transform_path)
        and bool(figure_transformation.get("operation"))
    )
    supported_claims = figure.get("supported_manuscript_claims", [])
    claims_ok = bool(supported_claims) and all(
        isinstance(item, dict)
        and bool(item.get("claim"))
        and item["claim"] in text
        and bool(item.get("locator"))
        for item in supported_claims
    )
    required_keys = {
        "artifact_id",
        "source_data",
        "transformation",
        "caption_claim",
        "supported_manuscript_claims",
        "limitations",
    }
    return (
        required_keys <= figure.keys()
        and len(matching) == 1
        and len(matching_png) == 1
        and source_ok
        and transform_ok
        and claims_ok
    )


def audit(
    manuscript: Path,
    scale_analysis: Path,
    cost_analysis: Path,
    figure_trace: Path,
    official_analysis: Path | None = None,
    apportionment_analysis: Path | None = None,
    baseline_analysis: Path | None = None,
    unquantized_analysis: Path | None = None,
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

    if apportionment_analysis is not None:
        apportionment = json.loads(
            apportionment_analysis.read_text(encoding="utf-8")
        )
        bound = apportionment["apportionment"]["max_tv_upper_bound"]
        apportionment_claims = {
            "integer apportionment contract count": (
                f"all {apportionment['contracts']:,} saved seed-0 contracts"
            ),
            "integer apportionment TV bound": (
                r"1/32768=3.0518\times10^{-5}"
                if abs(bound - 1 / 32768) < 1e-15
                else f"{bound:.10f}"
            ),
            "integer apportionment KL boundary": (
                "No finite distribution-free KL bound exists"
            ),
        }
        for name, value in apportionment_claims.items():
            check(checks, name, value in text, f"expected manuscript token: {value}")

    if baseline_analysis is not None:
        baselines = json.loads(baseline_analysis.read_text(encoding="utf-8"))
        by_name = {item["name"]: item for item in baselines["baselines"]}
        baseline_claims = {
            "SPRC referenced bytes": (
                f"{by_name['sparse_precision_replay_certificate']['referenced_package_bytes']:,} bytes"
            ),
            "full-trace referenced bytes": (
                f"{by_name['full_token_trace']['referenced_package_bytes']:,} bytes"
            ),
            "block-repair-4 referenced bytes": (
                f"{by_name['block_repair_4']['referenced_package_bytes']:,} bytes"
            ),
        }
        for name, value in baseline_claims.items():
            check(checks, name, value in text, f"expected manuscript token: {value}")

    if unquantized_analysis is not None:
        unquantized = json.loads(unquantized_analysis.read_text(encoding="utf-8"))
        top2 = unquantized["variants"]["top_2"]
        top16 = unquantized["variants"]["top_16"]
        unquantized_claims = {
            "unquantized top-2 correction delta": (
                f"{100 * top2['correction_rate_delta_vs_sprc']:.3f} percentage points"
            ),
            "unquantized top-2 interval": (
                f"{100 * top2['paired_prompt_ci95'][0]:.3f}-"
                f"{100 * top2['paired_prompt_ci95'][1]:.3f}"
            ),
            "unquantized top-2 package": (
                f"{top2['referenced_package_bytes']:,} referenced bytes"
            ),
            "unquantized top-16 correction rate": (
                f"{100 * top16['mean_correction_rate']:.3f}%"
            ),
            "finite-precision support shortfall": (
                "One of 1,500 steps retained only five positive-probability candidates"
            ),
        }
        for name, value in unquantized_claims.items():
            check(checks, name, value in text, f"expected manuscript token: {value}")

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
        "no native-distribution claim": "do not establish target-independent determinism, native-distribution preservation, semantic equivalence or cross-hardware generality",
        "exactness is an integrity gate": "exact replay as an integrity gate",
        "no human ratings": "no human ratings were collected",
        "same-machine external replay": "current 20-trial result is a same-machine smoke test",
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
        passed = valid_figure_package(ROOT, figure, text)
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
    parser.add_argument(
        "--apportionment",
        type=Path,
        default=ROOT / "docs/reproducibility/R050_INTEGER_APPORTIONMENT.json",
    )
    parser.add_argument(
        "--baselines",
        type=Path,
        default=ROOT / "docs/reproducibility/R051_REPLAY_BASELINES.json",
    )
    parser.add_argument(
        "--unquantized",
        type=Path,
        default=ROOT / "docs/reproducibility/R052_UNQUANTIZED_DELTA_ANALYSIS.json",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "paper/MANUSCRIPT_INTEGRITY.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "paper/MANUSCRIPT_INTEGRITY.md")
    args = parser.parse_args()
    report = audit(
        args.manuscript,
        args.scale,
        args.cost,
        args.figure_trace,
        args.official,
        args.apportionment,
        args.baselines,
        args.unquantized,
    )
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    args.markdown.write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    return 1 if report["summary"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
