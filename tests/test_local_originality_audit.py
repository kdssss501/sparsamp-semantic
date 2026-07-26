from pathlib import Path

from scripts.audit_local_originality import audit, citation_numbers, manuscript_paragraphs


def test_citation_numbers_expand_ranges() -> None:
    assert citation_numbers("Claims [1,3-5].") == {1, 3, 4, 5}


def test_manuscript_paragraphs_exclude_tables_and_references() -> None:
    text = (
        "## Results\n\n"
        + " ".join(["original"] * 35)
        + "\n\n| table | row |\n\n## References\n\n"
        + " ".join(["reference"] * 35)
    )
    paragraphs = manuscript_paragraphs(text)
    assert len(paragraphs) == 1
    assert paragraphs[0]["section"] == "Results"


def test_audit_flags_twenty_word_verbatim_overlap(tmp_path: Path) -> None:
    phrase = " ".join(f"word{index}" for index in range(25))
    manuscript = tmp_path / "paper.md"
    manuscript.write_text(f"## Results\n\n{phrase} additional words for paragraph length\n", encoding="utf-8")
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "ref1.txt").write_text(f"prefix {phrase} suffix", encoding="utf-8")
    report = audit(manuscript, sources)
    assert report["status"] == "FAIL"
    assert report["counts"]["VERBATIM"] == 1
