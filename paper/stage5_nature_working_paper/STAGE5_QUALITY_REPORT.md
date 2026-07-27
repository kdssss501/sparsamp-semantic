# Stage 5 Finalization Report

**Status:** PASS within working-paper scope

## Deliverables

| Artifact | Pages | Bytes | SHA-256 |
|---|---:|---:|---|
| `working_paper.pdf` | 24 | 270,003 | `6a66ab1a8ac114c9cdf2a886c8803a530c6ed07bfe3dcfff9f2e23268f41aaed` |
| `supplementary_information.pdf` | 6 | 71,618 | `19f33f2b4b44aeda20778c7de8409321a9390c70a50e73eb0fa04f10e2574f5d` |

The package also contains the final Markdown, LaTeX sources, build instructions and a source/figure/PDF hash manifest.

## Verification

- XeLaTeX: two successful passes for each PDF; zero compilation errors, undefined references, font warnings or overfull boxes.
- PDF metadata: title present; author is exactly `Lei Ke`; no affiliation, email, funding, CRediT, acknowledgement or competing-interest metadata was invented.
- Fonts: all fonts reported by `pdffonts` are embedded; the main text uses TeX Gyre Termes, TeX Gyre Heros and Latin Modern Mono.
- Content: 3 main tables, 4 main figures, 1 supplementary figure and 9 references are present.
- Visual inspection: title/abstract, all three table pages, all four figure pages, supplementary title, Table S2 and Supplementary Figure 1 were rendered and inspected. No clipping, overlap or blank figure was observed.
- Page orientation: every page reports rotation 0. Main Tables 1-3 and Supplementary Table S2 use portrait `xltabular` layouts with automatic wrapping and multi-page support; no `landscape` or `resizebox` command remains in generated LaTeX.
- Extracted-text inspection: title, author, tables, figures, declarations and references are present; no unresolved placeholders or `undefined` markers remain.
- Pytest: 261 passed; one dependency deprecation warning only.
- Ruff: all checks passed.
- Manuscript integrity audit: 50 passed, 0 failed, status `PASS`.

## Scope Notes

- The TeX Live `nature.cls` used here is a community preprint class, not an official current Nature submission template.
- This is a Nature-style working paper, not a claim of journal compliance, acceptance or top-venue readiness.
- The evidence remains limited to target-specific replay on one model family and one GPU/software stack. It does not establish target-independent determinism, native-distribution preservation, semantic equivalence or cross-hardware generality.
- Administrative submission fields and an archival repository DOI remain intentionally absent.
