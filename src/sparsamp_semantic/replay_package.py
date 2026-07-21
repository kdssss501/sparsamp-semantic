"""Portable reference bundles for target-specific precision replay."""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path
from typing import Any, Iterable


BUNDLE_SCHEMA = "precision-replay-reference-bundle-v1"
REFERENCE_FIELDS = (
    "prompt_index",
    "prompt",
    "seed",
    "policy",
    "reference_completed",
    "token_count",
    "reference_token_ids",
    "reference_token_sha256",
    "reference_text",
    "sentence_complete",
    "stopped_on_sentence",
    "reference_contracts",
    "reference_seconds",
    "mean_reference_source_mass",
    "mean_contract_source_mass",
    "mean_contract_truncation_kl_nats",
    "mean_reference_quantization_kl_nats",
    "mean_reference_quantization_tv",
)


def canonical_signature(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: Path, chunk_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def model_fingerprint(model_path: Path, *, hash_weights: bool = True) -> dict[str, Any]:
    if not model_path.is_dir():
        raise ValueError(f"model path is not a directory: {model_path}")
    files = []
    for path in sorted(item for item in model_path.rglob("*") if item.is_file()):
        relative = path.relative_to(model_path).as_posix()
        is_weight = path.suffix in {".bin", ".pt", ".pth", ".safetensors"}
        item = {"path": relative, "size": path.stat().st_size}
        if hash_weights or not is_weight:
            item["sha256"] = file_sha256(path)
        else:
            item["sha256"] = None
        files.append(item)
    value = {
        "schema": "model-directory-fingerprint-v1",
        "hash_weights": hash_weights,
        "files": files,
    }
    value["signature"] = canonical_signature(value)
    return value


def runtime_fingerprint() -> dict[str, Any]:
    value: dict[str, Any] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    try:
        import torch

        value.update(
            {
                "torch": torch.__version__,
                "cuda_runtime": torch.version.cuda,
                "cuda_available": torch.cuda.is_available(),
                "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            }
        )
    except ImportError:
        value["torch"] = None
    try:
        import transformers

        value["transformers"] = transformers.__version__
    except ImportError:
        value["transformers"] = None
    value["signature"] = canonical_signature(value)
    return value


def _selected_rows(rows: Iterable[dict[str, Any]], seeds: set[int]) -> list[dict[str, Any]]:
    selected = []
    for row in rows:
        if int(row["seed"]) not in seeds:
            continue
        if not bool(row.get("reference_completed")):
            raise ValueError("selected source row has no completed reference")
        missing = [field for field in REFERENCE_FIELDS if field not in row]
        if missing:
            raise ValueError(f"selected source row misses reference fields: {missing}")
        selected.append({field: row[field] for field in REFERENCE_FIELDS})
    selected.sort(key=lambda row: (int(row["prompt_index"]), int(row["seed"]), row["policy"]))
    if not selected:
        raise ValueError("no source rows matched the selected seeds")
    return selected


def export_reference_bundle(
    report: dict[str, Any],
    *,
    seeds: Iterable[int],
    model: dict[str, Any],
    source_sha256: str,
) -> dict[str, Any]:
    selected_seeds = {int(seed) for seed in seeds}
    if not selected_seeds:
        raise ValueError("at least one seed must be selected")
    if report.get("phase") != "completed":
        raise ValueError("source report must be completed")
    config = dict(report["experiment_config"])
    config["seeds"] = sorted(selected_seeds)
    rows = _selected_rows(report["rows"], selected_seeds)
    bundle = {
        "schema": BUNDLE_SCHEMA,
        "source": {
            "report_sha256": source_sha256,
            "result_signature": report.get("result_signature"),
            "run_label": report.get("run_label"),
            "environment": report.get("environment"),
        },
        "experiment_config": config,
        "model_fingerprint": model,
        "rows": rows,
    }
    bundle["bundle_signature"] = canonical_signature(bundle)
    return bundle


def validate_reference_bundle(bundle: dict[str, Any]) -> None:
    if bundle.get("schema") != BUNDLE_SCHEMA:
        raise ValueError("unsupported reference bundle schema")
    signature = bundle.get("bundle_signature")
    unsigned = {key: value for key, value in bundle.items() if key != "bundle_signature"}
    if signature != canonical_signature(unsigned):
        raise ValueError("reference bundle signature mismatch")
    rows = bundle.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("reference bundle rows must be a non-empty list")
    keys = [
        (int(row["prompt_index"]), int(row["seed"]), str(row["policy"])) for row in rows
    ]
    if len(keys) != len(set(keys)):
        raise ValueError("reference bundle contains duplicate trials")


def write_atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True), encoding="utf-8"
    )
    temporary.replace(path)
