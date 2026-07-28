# Image-generation manifest

All non-data figures in this paper must be generated as raster illustrations. Data figures 4--7 are produced by `scripts/generate_ccfa_bounded_decision_figures.py` and are not image-generated.

## Shared visual language

- Use case: `scientific-educational`.
- Asset type: two-column security-paper figure, landscape, 3:2.
- Style: precise editorial scientific illustration, flat paper texture, thin ink outlines, subtle depth, no photorealism.
- Palette: Okabe--Ito blue `#0072B2`, orange `#E69F00`, green `#009E73`, vermilion `#D55E00`, neutral charcoal.
- Typography: short English labels only, high-contrast sans serif, no paragraph text.
- Constraints: white background, no gradient, no decorative blobs, no logo, no watermark, no equations rendered as text.

## Figure 1: Cross-precision system architecture

Filename: `figures/figure_01_architecture.png`

Prompt:

> Create a rigorous but lively scientific architecture illustration for a top-tier computer-security paper. Left-to-right pipeline: an FP16 sender represented by a compact language-model chip emits a reference token stream; a PUBLIC INTEGER CONTRACT represented by a transparent ledger quantizes logits and apportions integer probability mass; a BOUNDED DECISION SET engine represented by a finite lattice of candidate choices certifies invariant steps; only unsafe steps flow into a sparse manifest shown as a few indexed correction slips; a BF16 receiver uses the same public random tape and sparse manifest to reconstruct the exact token stream. Show public information in blue, uncertain intervals in orange, certified decisions in green, corrections in vermilion. Exact labels, each used once: "FP16 Sender", "Integer Contract", "Bounded Set", "Sparse Manifest", "BF16 Replay". The reconstructed tokens at both ends should visually match. No locks, spies, secret messages, or offensive-security imagery.

## Figure 2: Mathematical principle

Filename: `figures/figure_02_math_principle.png`

Prompt:

> Create a scientific mathematical-principle illustration for a two-column security paper. Depict five vertical integer logit interval boxes with lower and upper endpoints, where only two boxes can jointly rise into the top-2 region. Connect the feasible pair to a discrete integer-mass ruler and one public random point. Split the outcome into two visual branches: a singleton green decision set marked "Invariant" and a multi-choice orange-red set marked "Record". Use exact short labels: "Logit Intervals", "Feasible Top-2", "Integer Mass", "Public Point", "Invariant", "Record". Emphasize finite enumeration and conservative uncertainty. Do not print formulas; leave formulas to the paper text. White background, flat editorial style, crisp geometry, no decorative gradients.

## Figure 3: Frozen evaluation protocol

Filename: `figures/figure_03_protocol.png`

Prompt:

> Create a clean scientific experimental-protocol illustration for a top-tier security paper. Show three separated stages on a horizontal time axis. Stage one: "Seed 0 Development" with ten prompt cards and threshold calibration. A visibly frozen glass-like rulebook then prevents feedback. Stage two: "Frozen Contract" containing three fixed values Delta=1, mass radius=1984, support gap=1. Stage three: "Seeds 1 and 2" with forty untouched trial cards entering independent FP16-to-BF16 evaluation, ending in a green seal "40/40" and a small cost arrow "54.62%". Exact labels: "Seed 0 Development", "Frozen Contract", "Seeds 1 and 2", "40/40", "54.62%". Make the no-feedback separation visually unmistakable. White background, editorial scientific illustration, no decorative gradients, no watermark.

## Validation checklist

- Labels match the quoted text exactly.
- Architecture arrows have one direction and no disconnected stage.
- Figure 2 shows intervals and a singleton-versus-multiple decision split.
- Figure 3 separates development from independent seeds and visibly freezes thresholds.
- Each final PNG is copied into this directory rather than referenced from a temporary image-generation directory.
