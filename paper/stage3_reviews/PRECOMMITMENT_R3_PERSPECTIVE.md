# Phase 1 Precommitment - R3 Perspective

## Contract Paraphrase

- D1 mandatory: artifacts, fingerprints, checkpoints and audit boundaries must make the result independently testable.
- D2 mandatory: practical claims must respect the actual model, hardware, tokenizer and data boundaries.
- D3 mandatory: deployment implications must follow from the demonstrated workflow.
- D4 high: the method must be meaningful for research software, auditability and responsible deployment.
- D5 normal: users must be able to understand what is shared, what is private and what remains unresolved.

## D1-D5 Scoring Plan

| dimension_id | what_to_look_for | what_triggers_block | what_triggers_warn |
|---|---|---|---|
| D1 | Portable artifacts, immutable identity, independent replay and checkpoint recovery | The reported package cannot actually reconstruct or verify the frozen result | Same-machine validation or missing archive limits independent use |
| D2 | Honest scope, data/code availability and stakeholder-facing terminology | Deployment or security claims materially exceed tested conditions | Boundaries are stated but critical practical assumptions remain implicit |
| D3 | End-to-end logic from contract construction to recipient replay | Claimed operational value requires unavailable state or circular trust | The workflow works only under a costly shared-state assumption not foregrounded |
| D4 | Transfer to audit, governance and reproducible ML workflows | No credible practical use survives outside the experiment | Use cases are credible but cost, privacy or governance trade-offs are missing |
| D5 | Availability statements, package-boundary explanations and accessibility | Missing documentation makes the artifact unusable | Metadata placeholders or overly technical presentation remain |

[CONTRACT-ACKNOWLEDGED]
