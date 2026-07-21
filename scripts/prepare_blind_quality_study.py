"""Build an anonymous offline A/B/C quality-study package without collecting ratings."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import secrets
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from sparsamp_semantic.replay_package import (  # noqa: E402
    canonical_signature,
    file_sha256,
    write_atomic_json,
)


METHODS = ("native_top16", "contract_top2", "contract_top4")
LABELS = ("A", "B", "C")


def completed_rows(report: dict[str, Any], *, text_field: str) -> dict[int, dict[str, Any]]:
    if report.get("phase") != "completed":
        raise ValueError("all study sources must be completed")
    rows = report.get("rows")
    if not isinstance(rows, list):
        raise ValueError("study source rows are invalid")
    selected: dict[int, dict[str, Any]] = {}
    for row in rows:
        if int(row.get("seed", 0)) != 0:
            continue
        index = int(row["prompt_index"])
        if index in selected or not str(row.get(text_field, "")).strip():
            raise ValueError("study source contains duplicate or empty rows")
        selected[index] = row
    return selected


def assignment_for(key: bytes, prompt_index: int) -> tuple[str, ...]:
    scored = []
    for method in METHODS:
        digest = hmac.new(
            key, f"r048\0{prompt_index}\0{method}".encode("ascii"), hashlib.sha256
        ).digest()
        scored.append((digest, method))
    return tuple(method for _, method in sorted(scored))


def build_packages(
    native: dict[str, Any],
    top2: dict[str, Any],
    top4: dict[str, Any],
    *,
    key: bytes,
    source_hashes: dict[str, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if len(key) != 32:
        raise ValueError("blinding key must contain 32 bytes")
    rows_by_method = {
        "native_top16": completed_rows(native, text_field="text"),
        "contract_top2": completed_rows(top2, text_field="reference_text"),
        "contract_top4": completed_rows(top4, text_field="reference_text"),
    }
    indices = set.intersection(*(set(rows) for rows in rows_by_method.values()))
    if len(indices) != 20:
        raise ValueError("R048 requires exactly 20 matched seed-0 prompts")

    trials = []
    mappings = []
    for prompt_index in sorted(indices):
        prompts = {rows[prompt_index]["prompt"] for rows in rows_by_method.values()}
        if len(prompts) != 1:
            raise ValueError("matched study rows disagree on prompt text")
        prompt = prompts.pop()
        order = assignment_for(key, prompt_index)
        trial_id = hmac.new(
            key, f"trial\0{prompt_index}".encode("ascii"), hashlib.sha256
        ).hexdigest()[:16]
        labels = []
        mapping = {}
        for label, method in zip(LABELS, order, strict=True):
            field = "text" if method == "native_top16" else "reference_text"
            labels.append({"label": label, "text": rows_by_method[method][prompt_index][field]})
            mapping[label] = method
        trials.append(
            {
                "trial_id": trial_id,
                "prompt_index": prompt_index,
                "language": "zh" if prompt_index >= 10 else "en",
                "prompt": prompt,
                "responses": labels,
            }
        )
        mappings.append({"trial_id": trial_id, "prompt_index": prompt_index, "mapping": mapping})

    participant = {
        "schema": "r048-blind-quality-participant-v1",
        "study_id": "R048",
        "ethics_status": "ETHICS_PENDING",
        "rating_schema": "study/R048/rating_schema.json",
        "trial_count": len(trials),
        "trials": trials,
    }
    participant["package_signature"] = canonical_signature(participant)
    private = {
        "schema": "r048-blinding-key-v1",
        "study_id": "R048",
        "ethics_status": "ETHICS_PENDING",
        "participant_package_signature": participant["package_signature"],
        "key_hex": key.hex(),
        "source_sha256": source_hashes,
        "mappings": mappings,
    }
    private["key_signature"] = canonical_signature(private)
    return participant, private


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--top2", type=Path, required=True)
    parser.add_argument("--top4", type=Path, required=True)
    parser.add_argument("--participant-output", type=Path, required=True)
    parser.add_argument("--private-key-output", type=Path, required=True)
    parser.add_argument("--fresh-key", action="store_true")
    args = parser.parse_args()
    if args.private_key_output.exists() and not args.fresh_key:
        private_existing = json.loads(args.private_key_output.read_text(encoding="utf-8"))
        key = bytes.fromhex(private_existing["key_hex"])
    else:
        key = secrets.token_bytes(32)

    paths = {"native": args.native, "top2": args.top2, "top4": args.top4}
    reports = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in paths.items()}
    participant, private = build_packages(
        reports["native"],
        reports["top2"],
        reports["top4"],
        key=key,
        source_hashes={name: file_sha256(path) for name, path in paths.items()},
    )
    write_atomic_json(args.participant_output, participant)
    write_atomic_json(args.private_key_output, private)
    print(
        json.dumps(
            {
                "ethics_status": participant["ethics_status"],
                "trials": participant["trial_count"],
                "participant_package_signature": participant["package_signature"],
                "private_key_output": str(args.private_key_output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
