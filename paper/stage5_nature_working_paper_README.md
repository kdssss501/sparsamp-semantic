# Stage 5 Nature-style working paper

This package is a reproducible working-paper rendering of `paper/MANUSCRIPT_DRAFT.md` and `paper/SUPPLEMENTARY_INFORMATION.md`.

- Author metadata contains only `Lei Ke`; no affiliation, email, funding, CRediT, acknowledgement or competing-interest text is invented.
- `working_paper.pdf` is compiled from `working_paper.tex` with XeLaTeX.
- `supplementary_information.pdf` is compiled separately from `supplementary_information.tex`.
- The main source uses the community-maintained TeX Live `nature.cls` preprint class. It is a Nature-style working paper, not an official Nature template or a journal-ready submission.
- Formatting does not expand the scientific claim boundary. The study remains limited to one model family, one GPU/software stack and target-specific replay certificates.

Rebuild sources from the audited Markdown:

```powershell
.venv\Scripts\python.exe scripts\build_nature_working_paper.py
```

Compile each PDF twice from `paper\stage5_nature_working_paper`:

```powershell
& 'C:\texlive\2026\bin\windows\xelatex.exe' -interaction=nonstopmode -halt-on-error working_paper.tex
& 'C:\texlive\2026\bin\windows\xelatex.exe' -interaction=nonstopmode -halt-on-error working_paper.tex
& 'C:\texlive\2026\bin\windows\xelatex.exe' -interaction=nonstopmode -halt-on-error supplementary_information.tex
& 'C:\texlive\2026\bin\windows\xelatex.exe' -interaction=nonstopmode -halt-on-error supplementary_information.tex
```
