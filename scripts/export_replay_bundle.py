"""Export completed reference trajectories for target-side precision replay."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from sparsamp_semantic.replay_package import (  # noqa: E402
    export_reference_bundle,
    file_sha256,
    model_fingerprint,
    write_atomic_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=[0])
    parser.add_argument("--metadata-only-weights", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    bundle = export_reference_bundle(
        report,
        seeds=args.seeds,
        model=model_fingerprint(args.model, hash_weights=not args.metadata_only_weights),
        source_sha256=file_sha256(args.input),
    )
    write_atomic_json(args.output, bundle)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "trials": len(bundle["rows"]),
                "bundle_signature": bundle["bundle_signature"],
                "model_signature": bundle["model_fingerprint"]["signature"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
