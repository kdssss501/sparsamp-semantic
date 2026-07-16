# Security and Responsible Research

This repository is intended for authorized steganography research, reproducibility studies, and
defensive evaluation. It should not be used to bypass access controls, exfiltrate data, or conceal
malicious activity.

## Secrets and Artifacts

- API keys and shared secrets must be provided through environment variables or local requests.
- `.env`, model weights, experiment outputs, recordings, caches, and downloaded wheels are ignored.
- Before publishing an artifact, confirm that prompts, cover text, and metadata contain no private
  or identifying information.

## Reporting

Do not open a public issue containing a working credential or sensitive experiment artifact.
Revoke an exposed credential first, then provide a minimal reproduction without the secret.

## Research Claims

- Token-ID recovery and public-text recovery are different threat models and must be reported
  separately.
- Top-k API experiments must not be described as full-distribution SparSamp.
- Distribution-preservation claims must state truncation, quantization, finite-precision, and model
  version assumptions.
