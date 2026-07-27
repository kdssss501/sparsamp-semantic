from __future__ import annotations

import json
from pathlib import Path

from scripts.build_nature_working_paper import (
    MAIN_SOURCE,
    SUPPLEMENT_SOURCE,
    build,
    build_main,
    build_supplement,
    clean_working_markdown,
)

PROCESS_REPORT = (
    Path(__file__).resolve().parents[1]
    / "paper"
    / "stage6_process_summary"
    / "paper_creation_process_zh.tex"
)


def test_working_markdown_keeps_only_supplied_author_metadata() -> None:
    markdown = clean_working_markdown(MAIN_SOURCE.read_text(encoding="utf-8"))

    assert "**Authors:** Lei Ke" in markdown
    assert "**Draft status:**" not in markdown
    assert "**Intended format:**" not in markdown
    assert "AUTHOR_INPUT_NEEDED" not in markdown


def test_main_latex_contains_all_audited_display_elements() -> None:
    markdown = clean_working_markdown(MAIN_SOURCE.read_text(encoding="utf-8"))
    latex = build_main(markdown)

    assert r"\author{Lei Ke}" in latex
    assert latex.count(r"\begin{xltabular}") == 3
    assert r"\begin{landscape}" not in latex
    assert r"\usepackage{pdflscape}" not in latex
    assert r"\resizebox" not in latex
    assert r"\usepackage{booktabs,array,xltabular}" in latex
    assert latex.count(r"\NATUREincludegraphics[") == 4
    assert latex.count(r"\bibitem{") == 9
    assert "target-independent determinism" in latex
    assert "native-distribution preservation" in latex
    assert "semantic equivalence" in latex
    assert "cross-hardware generality" in latex


def test_supplement_latex_uses_s2_and_shared_references() -> None:
    main_markdown = clean_working_markdown(MAIN_SOURCE.read_text(encoding="utf-8"))
    supplement_markdown = clean_working_markdown(
        SUPPLEMENT_SOURCE.read_text(encoding="utf-8")
    )
    latex = build_supplement(supplement_markdown, main_markdown)

    assert r"\author{Lei Ke}" in latex
    assert r"\setcounter{table}{1}" in latex
    assert r"\renewcommand{\thetable}{S\arabic{table}}" in latex
    assert latex.count(r"\begin{xltabular}") == 1
    assert r"\begin{landscape}" not in latex
    assert r"\usepackage{pdflscape}" not in latex
    assert r"\resizebox" not in latex
    assert r"\usepackage{booktabs,array,xltabular}" in latex
    assert "supplementary_figure_s1_official.pdf" in latex
    assert latex.count(r"\bibitem{") == 9
    assert "AUTHOR_INPUT_NEEDED" not in latex


def test_build_writes_reproducible_source_package(tmp_path: Path) -> None:
    build(tmp_path)

    expected = {
        "WORKING_PAPER.md",
        "SUPPLEMENTARY_INFORMATION.md",
        "working_paper.tex",
        "supplementary_information.tex",
        "README.md",
        "BUILD_MANIFEST.json",
    }
    assert expected <= {path.name for path in tmp_path.iterdir()}
    manifest = json.loads((tmp_path / "BUILD_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["stage"] == 5
    assert manifest["author"] == "Lei Ke"
    assert manifest["format"] == "Nature-style working paper"


def test_chinese_process_report_stays_portrait_and_table_free() -> None:
    latex = PROCESS_REPORT.read_text(encoding="utf-8")

    assert r"\documentclass[12pt,a4paper]{article}" in latex
    assert r"\setCJKmainfont{FandolSong-Regular}" in latex
    assert r"\begin{landscape}" not in latex
    assert r"\usepackage{pdflscape}" not in latex
    assert r"\resizebox" not in latex
    assert r"\begin{table}" not in latex
