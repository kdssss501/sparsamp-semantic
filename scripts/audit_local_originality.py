"""Screen manuscript paragraphs against locally extracted cited-source text."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORD_RE = re.compile(r"[a-z0-9]+")
CITATION_RE = re.compile(r"\[([0-9,\-\s]+)\]")


def words(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def citation_numbers(text: str) -> set[int]:
    numbers: set[int] = set()
    for group in CITATION_RE.findall(text):
        for part in group.split(","):
            part = part.strip()
            if "-" in part:
                start, end = (int(value.strip()) for value in part.split("-", 1))
                numbers.update(range(start, end + 1))
            elif part:
                numbers.add(int(part))
    return numbers


def manuscript_paragraphs(text: str) -> list[dict[str, Any]]:
    body = text.split("## References", 1)[0]
    paragraphs = []
    section = "Front matter"
    for block in re.split(r"\n\s*\n", body):
        stripped = block.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            section = stripped.lstrip("# ")
            continue
        if (
            stripped.startswith(("|", "- ", "1. ", "2. ", "3. ", "4. ", "5. "))
            or stripped.startswith("```")
            or stripped.startswith("$$")
        ):
            continue
        normalized = words(stripped)
        if len(normalized) < 30:
            continue
        paragraphs.append(
            {
                "index": len(paragraphs) + 1,
                "section": section,
                "text": stripped,
                "words": normalized,
                "citations": sorted(citation_numbers(stripped)),
            }
        )
    return paragraphs


def ngrams(tokens: list[str], size: int) -> set[tuple[str, ...]]:
    if len(tokens) < size:
        return set()
    return {tuple(tokens[index : index + size]) for index in range(len(tokens) - size + 1)}


def audit(manuscript: Path, source_dir: Path) -> dict[str, Any]:
    paragraphs = manuscript_paragraphs(manuscript.read_text(encoding="utf-8"))
    sources = {}
    for path in sorted(source_dir.glob("ref*.txt")):
        match = re.fullmatch(r"ref(\d+)", path.stem)
        if match:
            sources[int(match.group(1))] = words(path.read_text(encoding="utf-8", errors="ignore"))
    if not sources:
        raise ValueError(f"no ref*.txt sources found in {source_dir}")

    source_ngrams = {
        ref: {size: ngrams(tokens, size) for size in (8, 12, 20)}
        for ref, tokens in sources.items()
    }
    results = []
    for paragraph in paragraphs:
        paragraph_ngrams = {
            size: ngrams(paragraph["words"], size) for size in (8, 12, 20)
        }
        matches: dict[int, dict[int, list[tuple[str, ...]]]] = {}
        for ref, by_size in source_ngrams.items():
            shared = {
                size: sorted(paragraph_ngrams[size] & by_size[size])
                for size in (8, 12, 20)
            }
            if any(shared.values()):
                matches[ref] = shared

        if any(shared[20] for shared in matches.values()):
            grade = "VERBATIM"
        elif any(shared[12] for shared in matches.values()):
            matched_refs = {ref for ref, shared in matches.items() if shared[12]}
            grade = (
                "PARAPHRASE"
                if matched_refs <= set(paragraph["citations"])
                else "CLOSE_MATCH"
            )
        elif matches:
            grade = "PARAPHRASE" if paragraph["citations"] else "COMMON_KNOWLEDGE"
        else:
            grade = "ORIGINAL"

        examples = []
        for ref, shared in matches.items():
            size = 20 if shared[20] else (12 if shared[12] else 8)
            examples.append(
                {
                    "reference": ref,
                    "words": size,
                    "phrase": " ".join(shared[size][0]),
                }
            )
        results.append(
            {
                "index": paragraph["index"],
                "section": paragraph["section"],
                "word_count": len(paragraph["words"]),
                "citations": paragraph["citations"],
                "grade": grade,
                "matches": examples,
            }
        )

    counts = Counter(item["grade"] for item in results)
    blocking = counts["CLOSE_MATCH"] + counts["VERBATIM"]
    return {
        "schema": "local-originality-screen-v1",
        "manuscript": str(manuscript),
        "source_dir": str(source_dir),
        "source_references": sorted(sources),
        "eligible_paragraphs": len(paragraphs),
        "screened_paragraphs": len(results),
        "sampling_rate": 1.0 if results else 0.0,
        "counts": dict(sorted(counts.items())),
        "blocking_matches": blocking,
        "status": "PASS_WITH_SCOPE_LIMITATION" if blocking == 0 else "FAIL",
        "results": results,
        "limitations": [
            "Comparison is limited to the nine cited public sources extracted locally.",
            "The screen detects exact contiguous 8-, 12- and 20-word overlap; it is not a semantic plagiarism detector.",
            "The manuscript was not sent to an external search engine or plagiarism service.",
            "Turnitin or iThenticate remains recommended before submission.",
        ],
    }


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Stage 4.5 Local Originality Screen",
        "",
        f"**Status:** {report['status']}",
        f"**Coverage:** {report['screened_paragraphs']}/{report['eligible_paragraphs']} eligible paragraphs ({100 * report['sampling_rate']:.1f}%)",
        f"**Blocking matches:** {report['blocking_matches']}",
        "",
        "| Grade | Count |",
        "|---|---:|",
    ]
    for grade in ("ORIGINAL", "COMMON_KNOWLEDGE", "PARAPHRASE", "CLOSE_MATCH", "VERBATIM"):
        lines.append(f"| {grade} | {report['counts'].get(grade, 0)} |")
    lines.extend(["", "## Matched phrases", ""])
    matched = [item for item in report["results"] if item["matches"]]
    if not matched:
        lines.append("No contiguous eight-word-or-longer matches were found.")
    else:
        lines.extend(["| Paragraph | Section | Grade | Reference | Words | Phrase |", "|---:|---|---|---:|---:|---|"])
        for item in matched:
            for match in item["matches"]:
                phrase = match["phrase"].replace("|", "\\|")
                lines.append(
                    f"| {item['index']} | {item['section']} | {item['grade']} | "
                    f"{match['reference']} | {match['words']} | {phrase} |"
                )
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manuscript",
        type=Path,
        default=ROOT / "paper/MANUSCRIPT_DRAFT.md",
    )
    parser.add_argument(
        "--sources",
        type=Path,
        default=ROOT / "outputs/stage45_sources",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "paper/stage4_5_final_integrity/ORIGINALITY_SCREEN.json",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=ROOT / "paper/stage4_5_final_integrity/ORIGINALITY_SCREEN.md",
    )
    args = parser.parse_args()
    report = audit(args.manuscript, args.sources)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    args.markdown.write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "screened_paragraphs", "blocking_matches")}, indent=2))
    return 0 if report["blocking_matches"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
