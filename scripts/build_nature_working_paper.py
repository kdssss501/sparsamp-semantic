"""Build the Stage 5 Nature-style working-paper sources from audited Markdown.

The converter is intentionally narrow: it supports the Markdown constructs used
by ``paper/MANUSCRIPT_DRAFT.md`` and ``paper/SUPPLEMENTARY_INFORMATION.md``.
It preserves manuscript prose while applying the ordering and typography of the
TeX Live ``nature`` preprint class. The class is community maintained and is not
an official Nature submission template.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_SOURCE = ROOT / "paper" / "MANUSCRIPT_DRAFT.md"
SUPPLEMENT_SOURCE = ROOT / "paper" / "SUPPLEMENTARY_INFORMATION.md"
OUTPUT_DIR = ROOT / "paper" / "stage5_nature_working_paper"

FIGURE_FILES = {
    "Figure 1": "figure_01_workflow.pdf",
    "Figure 2": "figure_02_replay_scale.pdf",
    "Figure 3": "figure_03_contract_width.pdf",
    "Figure 4": "figure_04_precision_direction.pdf",
}


@dataclass(frozen=True)
class MarkdownTable:
    caption: str
    headers: list[str]
    rows: list[list[str]]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def escape_plain(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def latex_code(text: str) -> str:
    escaped = escape_plain(text)
    for separator in (r"\_", "/", ".", ":", "-", " "):
        escaped = escaped.replace(separator, separator + r"\allowbreak{}")
    return r"\texttt{" + escaped + "}"


INLINE_PATTERN = re.compile(
    r"(?P<math>\\\(.*?\\\))"
    r"|(?P<code>`[^`]+`)"
    r"|(?P<bold>\*\*.*?\*\*)"
    r"|(?P<italic>\*[^*]+\*)"
    r"|(?P<cite>\[(?:\d+(?:,\d+)*)\])"
    r"|(?P<url>https?://[^\s]+)"
)


def latex_inline(text: str, *, rich: bool = True) -> str:
    output: list[str] = []
    cursor = 0
    for match in INLINE_PATTERN.finditer(text):
        output.append(escape_plain(text[cursor : match.start()]))
        token = match.group(0)
        kind = match.lastgroup
        if kind == "math":
            output.append(token)
        elif kind == "code":
            value = token[1:-1]
            if value.startswith(("http://", "https://")):
                output.append(r"\url{" + value + "}")
            else:
                output.append(latex_code(value))
        elif kind == "bold" and rich:
            output.append(r"\textbf{" + latex_inline(token[2:-2], rich=False) + "}")
        elif kind == "italic" and rich:
            output.append(r"\textit{" + latex_inline(token[1:-1], rich=False) + "}")
        elif kind == "cite":
            keys = ",".join(f"ref{part}" for part in token[1:-1].split(","))
            output.append(r"\cite{" + keys + "}")
        elif kind == "url":
            trailing = ""
            value = token
            while value and value[-1] in ".,;":
                trailing = value[-1] + trailing
                value = value[:-1]
            output.append(r"\url{" + value + "}" + escape_plain(trailing))
        else:
            output.append(escape_plain(token))
        cursor = match.end()
    output.append(escape_plain(text[cursor:]))
    return "".join(output)


def clean_working_markdown(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.startswith("**Draft status:**") or line.startswith("**Intended format:**"):
            continue
        if line.startswith("**Authors:**"):
            line = "**Authors:** Lei Ke"
        lines.append(line)
    return "\n".join(lines).rstrip() + "\n"


def split_sections(text: str) -> tuple[str, dict[str, list[str]]]:
    lines = text.splitlines()
    title = lines[0].removeprefix("# ").strip()
    sections: dict[str, list[str]] = {}
    current = "Front matter"
    sections[current] = []
    for line in lines[1:]:
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        else:
            sections[current].append(line)
    return title, sections


def paragraph_blocks(lines: list[str]) -> list[str]:
    blocks: list[str] = []
    buffer: list[str] = []
    in_math = False
    for line in lines:
        stripped = line.strip()
        if stripped == r"\[":
            if buffer:
                blocks.append(" ".join(buffer))
                buffer = []
            in_math = True
            buffer.append(stripped)
            continue
        if in_math:
            buffer.append(line)
            if stripped == r"\]":
                blocks.append("\n".join(buffer))
                buffer = []
                in_math = False
            continue
        if not stripped:
            if buffer:
                blocks.append(" ".join(buffer))
                buffer = []
            blocks.append("")
            continue
        if stripped.startswith(("## ", "### ", "|")) or re.match(r"^\d+\. ", stripped):
            if buffer:
                blocks.append(" ".join(buffer))
                buffer = []
            blocks.append(line)
            continue
        buffer.append(line)
    if buffer:
        blocks.append(" ".join(buffer))
    return blocks


def parse_table(blocks: list[str], start: int, caption: str) -> tuple[MarkdownTable, int]:
    raw_rows: list[list[str]] = []
    index = start
    while index < len(blocks) and blocks[index].lstrip().startswith("|"):
        cells = [cell.strip() for cell in blocks[index].strip().strip("|").split("|")]
        raw_rows.append(cells)
        index += 1
    if len(raw_rows) < 2:
        raise ValueError("Markdown table is missing a header separator")
    return MarkdownTable(caption=caption, headers=raw_rows[0], rows=raw_rows[2:]), index


def render_table(table: MarkdownTable, table_number: int, *, supplementary: bool = False) -> str:
    columns = len(table.headers)
    label_prefix = "tab:s" if supplementary else "tab:"
    alignment = r">{\raggedright\arraybackslash}X" + f" *{{{columns - 1}}}{{Y}}"
    header = " & ".join(
        r"\textbf{" + latex_inline(cell) + "}" for cell in table.headers
    ) + r" \\"
    lines = [
        r"\clearpage",
        r"\begingroup",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{2.5pt}",
        r"\renewcommand{\arraystretch}{1.22}",
        r"\begin{xltabular}{\textwidth}{@{}" + alignment + r"@{}}",
        r"\caption{" + latex_inline(table.caption) + r"}\label{" + label_prefix + str(table_number) + r"} \\",
        r"\toprule",
        header,
        r"\midrule",
        r"\endfirsthead",
        r"\multicolumn{" + str(columns) + r"}{l}{\scriptsize\itshape Continued from previous page} \\",
        r"\toprule",
        header,
        r"\midrule",
        r"\endhead",
        r"\midrule",
        r"\multicolumn{" + str(columns) + r"}{r}{\scriptsize\itshape Continued on next page} \\",
        r"\endfoot",
        r"\bottomrule",
        r"\endlastfoot",
    ]
    lines.extend(" & ".join(latex_inline(cell) for cell in row) + r" \\" for row in table.rows)
    lines.extend(
        [
            r"\end{xltabular}",
            r"\endgroup",
            r"\clearpage",
        ]
    )
    return "\n".join(lines)


def caption_text(line: str) -> str:
    match = re.match(r"^\*\*(.+?)\*\*\s*(.*)$", line.strip())
    if not match:
        return line.strip()
    heading = re.sub(r"^Table \d+ \|\s*", "", match.group(1))
    return f"{heading} {match.group(2)}".strip()


def render_blocks(lines: list[str], *, supplementary: bool = False) -> str:
    blocks = paragraph_blocks(lines)
    output: list[str] = []
    list_items: list[str] = []
    pending_caption = ""
    # Supplementary Table 1 is the external machine-readable compatibility
    # matrix. The first rendered supplementary table is therefore Table S2.
    table_number = 1 if supplementary else 0
    index = 0

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            output.append(r"\begin{enumerate}")
            output.extend(r"\item " + latex_inline(item) for item in list_items)
            output.append(r"\end{enumerate}")
            list_items = []

    while index < len(blocks):
        block = blocks[index]
        stripped = block.strip()
        if not stripped:
            flush_list()
            index += 1
            continue
        if stripped.startswith("## "):
            flush_list()
            heading = stripped[3:].strip()
            output.append(r"\section*{" + latex_inline(heading) + "}")
            index += 1
            continue
        if stripped.startswith("### "):
            flush_list()
            heading = stripped[4:].strip().rstrip(".")
            output.append(r"\subsection{" + latex_inline(heading) + ".}")
            index += 1
            continue
        list_match = re.match(r"^\d+\.\s+(.*)$", stripped)
        if list_match:
            list_items.append(list_match.group(1))
            index += 1
            continue
        flush_list()
        if stripped.startswith(r"\[") and stripped.endswith(r"\]"):
            output.append(stripped)
            index += 1
            continue
        if stripped.startswith("**Table "):
            pending_caption = caption_text(stripped)
            index += 1
            continue
        if stripped.startswith("|"):
            table_number += 1
            default_caption = (
                "Mechanism and trust-boundary comparison."
                if supplementary and table_number == 2
                else f"Table {table_number}"
            )
            table, index = parse_table(blocks, index, pending_caption or default_caption)
            output.append(render_table(table, table_number, supplementary=supplementary))
            pending_caption = ""
            continue
        output.append(latex_inline(stripped) + "\n")
        index += 1
    flush_list()
    return "\n".join(output).strip()


def parse_references(lines: list[str]) -> list[tuple[str, str]]:
    references: list[tuple[str, str]] = []
    for line in lines:
        match = re.match(r"^(\d+)\.\s+(.*)$", line.strip())
        if match:
            references.append((f"ref{match.group(1)}", match.group(2)))
    return references


def render_references(references: list[tuple[str, str]]) -> str:
    lines = [r"\begin{thebibliography}{99}"]
    lines.extend(r"\bibitem{" + key + "} " + latex_inline(value) for key, value in references)
    lines.append(r"\end{thebibliography}")
    return "\n".join(lines)


def parse_figure_legends(lines: list[str]) -> dict[str, str]:
    legends: dict[str, str] = {}
    for line in lines:
        match = re.match(r"^\*\*((?:Supplementary )?Figure \d+) \| (.+?)\*\*\s*(.*)$", line.strip())
        if match:
            legends[match.group(1)] = f"{match.group(2)} {match.group(3)}".strip()
    return legends


def render_figures(legends: dict[str, str]) -> str:
    blocks: list[str] = []
    for label, filename in FIGURE_FILES.items():
        blocks.extend(
            [
                r"\clearpage",
                r"\thispagestyle{plain}",
                r"\begin{center}",
                r"\NATUREincludegraphics[width=0.96\textwidth,height=0.72\textheight,keepaspectratio]{"
                + filename
                + "}",
                r"\end{center}",
                r"\noindent\sffamily\textbf{" + label + r" | }" + latex_inline(legends[label]),
            ]
        )
    return "\n".join(blocks)


def main_preamble(title: str) -> str:
    return rf"""\documentclass{{nature}}

\usepackage{{fontspec}}
\setmainfont{{TeX Gyre Termes}}
\setsansfont{{TeX Gyre Heros}}
\setmonofont{{Latin Modern Mono}}
\makeatletter
\renewcommand{{\@maketitle}}{{%
  \newpage\spacing{{1}}\setlength{{\parskip}}{{12pt}}%
  {{\Large\bfseries\noindent\raggedright\textsf{{\@title}}\par}}%
  {{\noindent\@author\par}}}}
\makeatother
\usepackage{{amsmath,amssymb}}
\usepackage{{graphicx}}
\let\NATUREincludegraphics\includegraphics
\usepackage{{booktabs,array,xltabular}}
\newcolumntype{{Y}}{{>{{\centering\arraybackslash}}X}}
\usepackage{{microtype}}
\usepackage{{lineno}}
\usepackage{{xurl}}
\usepackage[hidelinks,unicode]{{hyperref}}
\graphicspath{{{{../figures/}}}}
\hypersetup{{pdftitle={{{escape_plain(title)}}},pdfauthor={{Lei Ke}}}}
\emergencystretch=2em
\title{{{escape_plain(title)}}}
\author{{Lei Ke}}

\begin{{document}}
\maketitle
\par\smallskip
\noindent\textsf{{\small Nature-style working paper; not a journal-formatted submission.}}\par
\spacing{{1.15}}
"""


def build_main(markdown: str) -> str:
    title, sections = split_sections(markdown)
    references = parse_references(sections["References"])
    legends = parse_figure_legends(sections["Figure legends"])
    keywords = next(
        line.removeprefix("**Keywords:**").strip()
        for line in sections["Front matter"]
        if line.startswith("**Keywords:**")
    )
    addendum = [
        ("Supplementary information", "Supplementary information accompanies this working paper."),
        ("Data availability", render_blocks(sections["Data availability"])),
        ("Code availability", render_blocks(sections["Code availability"])),
        ("Ethics declaration", render_blocks(sections["Ethics declaration"])),
        ("AI-assisted work disclosure", render_blocks(sections["AI-assisted work disclosure"])),
    ]
    parts = [
        main_preamble(title),
        r"\begin{abstract}",
        render_blocks(sections["Abstract"]),
        r"\end{abstract}",
        r"\noindent\textbf{Keywords:} " + latex_inline(keywords),
        r"\linenumbers",
        render_blocks(sections["Introduction"]),
        r"\section*{Results}",
        render_blocks(sections["Results"]),
        r"\section*{Discussion}",
        render_blocks(sections["Discussion"]),
        r"\begin{methods}",
        render_blocks(sections["Methods"]),
        r"\end{methods}",
        render_references(references),
        r"\begin{addendum}",
    ]
    for label, content in addendum:
        parts.append(r"\item[" + label + "] " + content)
    parts.extend([r"\end{addendum}", render_figures(legends), r"\end{document}"])
    return "\n\n".join(parts) + "\n"


def supplement_preamble(title: str) -> str:
    return rf"""\documentclass[11pt,a4paper]{{article}}
\usepackage[margin=22mm]{{geometry}}
\usepackage{{newtxtext,newtxmath}}
\usepackage{{graphicx}}
\usepackage{{booktabs,array,xltabular}}
\newcolumntype{{Y}}{{>{{\centering\arraybackslash}}X}}
\usepackage{{microtype}}
\usepackage{{xurl}}
\usepackage[hidelinks,unicode]{{hyperref}}
\graphicspath{{{{../figures/}}}}
\hypersetup{{pdftitle={{Supplementary Information: {escape_plain(title)}}},pdfauthor={{Lei Ke}}}}
\emergencystretch=2em
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{7pt}}
\setcounter{{secnumdepth}}{{0}}
\renewcommand{{\thetable}}{{S\arabic{{table}}}}
\setcounter{{table}}{{1}}
\title{{\textbf{{Supplementary Information}}\\[4pt]\large {escape_plain(title)}}}
\author{{Lei Ke}}
\date{{}}
\begin{{document}}
\maketitle
"""


def build_supplement(markdown: str, main_markdown: str) -> str:
    lines = markdown.splitlines()
    title = next(line[3:] for line in lines if line.startswith("## Target-specific"))
    main_title, main_sections = split_sections(main_markdown)
    if title != main_title:
        raise ValueError("Main and supplementary titles differ")
    references = parse_references(main_sections["References"])
    legends = parse_figure_legends(main_sections["Figure legends"])
    body_lines: list[str] = []
    skip_figure_description = False
    for line in lines:
        if line.startswith("# Supplementary Information"):
            continue
        if line.startswith("## Target-specific") or line.startswith("**Authors:**"):
            continue
        if line.startswith("## Supplementary Figure 1"):
            skip_figure_description = True
            continue
        if skip_figure_description:
            if not line.strip():
                continue
            skip_figure_description = False
            continue
        body_lines.append(line)
    body = render_blocks(body_lines, supplementary=True)
    figure = "\n".join(
        [
            r"\clearpage",
            r"\section*{Supplementary Figure 1}",
            r"\begin{center}",
            r"\includegraphics[width=0.96\textwidth,height=0.70\textheight,keepaspectratio]{supplementary_figure_s1_official.pdf}",
            r"\end{center}",
            r"\noindent\textbf{Supplementary Figure 1 | }"
            + latex_inline(legends["Supplementary Figure 1"]),
        ]
    )
    return "\n\n".join(
        [supplement_preamble(title), body, figure, render_references(references), r"\end{document}"]
    ) + "\n"


def write_manifest(output_dir: Path, files: list[Path]) -> None:
    manifest = {
        "stage": 5,
        "format": "Nature-style working paper",
        "author": "Lei Ke",
        "source_files": {
            str(MAIN_SOURCE.relative_to(ROOT)): sha256(MAIN_SOURCE),
            str(SUPPLEMENT_SOURCE.relative_to(ROOT)): sha256(SUPPLEMENT_SOURCE),
        },
        "generated_files": {
            str(path.relative_to(output_dir)): sha256(path) for path in files
        },
        "figure_files": {
            name: sha256(ROOT / "paper" / "figures" / filename)
            for name, filename in FIGURE_FILES.items()
        }
        | {
            "Supplementary Figure 1": sha256(
                ROOT / "paper" / "figures" / "supplementary_figure_s1_official.pdf"
            )
        },
        "claim_boundary": (
            "Working-paper formatting only; no claim of Nature compliance, acceptance, "
            "target-independent determinism, native-distribution preservation, semantic "
            "equivalence or cross-hardware generality."
        ),
    }
    (output_dir / "BUILD_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )


def finalize_manifest(output_dir: Path) -> None:
    manifest_path = output_dir / "BUILD_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pdf_names = ("working_paper.pdf", "supplementary_information.pdf")
    pdf_paths = [output_dir / name for name in pdf_names]
    missing = [str(path) for path in pdf_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing compiled PDFs: {missing}")
    manifest["compiled_pdfs"] = {
        path.name: {"sha256": sha256(path), "bytes": path.stat().st_size}
        for path in pdf_paths
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )


def build(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    main_markdown = clean_working_markdown(MAIN_SOURCE.read_text(encoding="utf-8"))
    supplement_markdown = clean_working_markdown(SUPPLEMENT_SOURCE.read_text(encoding="utf-8"))

    outputs = {
        output_dir / "WORKING_PAPER.md": main_markdown,
        output_dir / "SUPPLEMENTARY_INFORMATION.md": supplement_markdown,
        output_dir / "working_paper.tex": build_main(main_markdown),
        output_dir / "supplementary_information.tex": build_supplement(
            supplement_markdown, main_markdown
        ),
    }
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8", newline="\n")

    for filename in [*FIGURE_FILES.values(), "supplementary_figure_s1_official.pdf"]:
        source = ROOT / "paper" / "figures" / filename
        if not source.exists():
            raise FileNotFoundError(source)

    readme_source = ROOT / "paper" / "stage5_nature_working_paper_README.md"
    if readme_source.exists():
        shutil.copyfile(readme_source, output_dir / "README.md")
        outputs[output_dir / "README.md"] = (output_dir / "README.md").read_text(encoding="utf-8")
    write_manifest(output_dir, list(outputs))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument(
        "--finalize",
        action="store_true",
        help="Record hashes for already compiled PDFs without regenerating sources.",
    )
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    if args.finalize:
        finalize_manifest(output_dir)
    else:
        build(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
