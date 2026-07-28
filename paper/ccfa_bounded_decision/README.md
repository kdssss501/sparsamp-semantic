# CCF-A style working paper

This directory contains the ACM `sigconf` working draft for the bounded-decision-set study. It is formatted in the style of a CCF-A computer-security conference paper; it is not a claim of acceptance or venue compliance.

## Rebuild

```powershell
& '.venv\Scripts\python.exe' scripts/generate_ccfa_bounded_decision_figures.py
Set-Location paper/ccfa_bounded_decision
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

The generated data figures are written as both PDF and 300-dpi PNG. Figures 1--3 are project-bound image-generation assets governed by `IMAGEGEN_PROMPTS.md`. The LaTeX source shows an explicit placeholder if one is missing, so a draft can be audited without silently substituting a code-drawn diagram.

## Evidence boundary

The primary confirmation result is R059: 40/40 exact trials, zero observed false-safe steps, 3,000 token decisions, and payload equal to 54.6222% of the matching full trace. This is an independent-seed confirmation on one RTX 3060 Laptop GPU, not a cross-hardware floating-point proof.
