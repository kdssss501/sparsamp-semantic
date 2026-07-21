"""Run the published SparSamp GPT-2 matrices with resumable per-context checkpoints."""

from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.util
import json
import os
import platform
import random
import sys
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from sparsamp_semantic.replay_package import (  # noqa: E402
    canonical_signature,
    file_sha256,
    model_fingerprint,
    write_atomic_json,
)


SCHEMA = "sparsamp-official-matrix-v1"
DEFAULT_BLOCK_SIZES = (2, 4, 8, 16, 32, 64, 128, 256, 512, 1023)
DEFAULT_TOP_PS = (0.8, 0.95, 1.0)


def load_artifact_module(source_dir: Path) -> Any:
    sys.path.insert(0, str(source_dir))
    spec = importlib.util.spec_from_file_location(
        "official_sparsamp_experiment", source_dir / "sparsamp.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load official Experiments/src/sparsamp.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def trial_plan(
    block_sizes: tuple[int, ...], top_ps: tuple[float, ...], context_indices: tuple[int, ...]
) -> list[dict[str, Any]]:
    configurations: dict[tuple[int, float], set[str]] = {}
    for block_size in block_sizes:
        configurations.setdefault((block_size, 1.0), set()).add("paper_table2")
    for top_p in top_ps:
        configurations.setdefault((64, top_p), set()).add("paper_tables3_4")
    return [
        {
            "block_size": block_size,
            "top_p": top_p,
            "context_index": context_index,
            "paper_suites": sorted(suites),
        }
        for (block_size, top_p), suites in sorted(configurations.items())
        for context_index in context_indices
    ]


def trial_key(value: dict[str, Any]) -> tuple[int, str, int]:
    return int(value["block_size"]), format(float(value["top_p"]), ".12g"), int(
        value["context_index"]
    )


def terminal(row: dict[str, Any]) -> bool:
    return row.get("status") in {"completed", "budget_exhausted"}


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries = []
    configurations = sorted({(int(row["block_size"]), float(row["top_p"])) for row in rows})
    for block_size, top_p in configurations:
        selected = [
            row
            for row in rows
            if int(row["block_size"]) == block_size and float(row["top_p"]) == top_p
        ]
        completed = [row for row in selected if row.get("status") == "completed"]
        eligible = [row for row in completed if not bool(row["token_ambiguity"])]
        token_count = sum(int(row["token_count"]) for row in eligible)
        bits = sum(int(row["encoded_bits"]) for row in eligible)
        entropy = sum(float(row["entropy_bits"]) for row in eligible)
        generation_seconds = sum(float(row["generation_seconds"]) for row in eligible)
        sampling_seconds = sum(float(row["sampling_seconds"]) for row in eligible)
        model_seconds = sum(float(row["model_seconds"]) for row in eligible)
        decode_seconds = sum(float(row["decode_seconds"]) for row in eligible)
        summaries.append(
            {
                "block_size": block_size,
                "top_p": top_p,
                "trials": len(selected),
                "completed": len(completed),
                "budget_exhausted": sum(
                    row.get("status") == "budget_exhausted" for row in selected
                ),
                "token_ambiguity": sum(bool(row["token_ambiguity"]) for row in completed),
                "eligible": len(eligible),
                "decode_success": sum(bool(row["decode_success"]) for row in eligible),
                "decoding_accuracy": (
                    mean(float(bool(row["decode_success"])) for row in eligible)
                    if eligible
                    else None
                ),
                "embedding_rate": bits / token_count if token_count else None,
                "utilization": bits / entropy if entropy else None,
                "embedding_speed_bits_s": (
                    bits / generation_seconds if generation_seconds else None
                ),
                "decoding_speed_bits_s": bits / decode_seconds if decode_seconds else None,
                "sampling_atst_s_token": (
                    sampling_seconds / token_count if token_count else None
                ),
                "sampling_to_inference_ratio": (
                    sampling_seconds / model_seconds if model_seconds else None
                ),
                "generation_speed_tokens_s": (
                    token_count / generation_seconds if generation_seconds else None
                ),
                "artifact_atst_s_token": (
                    generation_seconds / token_count if token_count else None
                ),
                "artifact_sitr": (
                    sampling_seconds / generation_seconds if generation_seconds else None
                ),
                "hardware_inconsistency_trials": sum(
                    bool(row["hardware_inconsistency"]) for row in eligible
                ),
            }
        )
    return summaries


def build_report(
    config: dict[str, Any],
    rows: list[dict[str, Any]],
    expected_trials: int,
    environment: dict[str, Any],
) -> dict[str, Any]:
    complete = len(rows) == expected_trials and all(terminal(row) for row in rows)
    return {
        "schema": SCHEMA,
        "phase": "completed" if complete else "partial",
        "timestamp": datetime.now(UTC).isoformat(),
        "experiment_config": config,
        "experiment_signature": canonical_signature(config),
        "environment": environment,
        "progress": {"completed_trials": len(rows), "expected_trials": expected_trials},
        "summary": summarize(rows),
        "rows": sorted(rows, key=trial_key),
    }


def load_rows(path: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("experiment_config") != config:
        raise ValueError("official matrix checkpoint configuration mismatch")
    rows = report.get("rows")
    if not isinstance(rows, list) or len({trial_key(row) for row in rows}) != len(rows):
        raise ValueError("official matrix checkpoint rows are invalid")
    return rows


def archive_existing(path: Path) -> None:
    if path.exists():
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        path.replace(path.with_name(f"{path.stem}.{stamp}.bak{path.suffix}"))


def token_sha256(token_ids: list[int]) -> str:
    return hashlib.sha256(b"".join(token.to_bytes(4, "big") for token in token_ids)).hexdigest()


def run_trial(
    *,
    official: Any,
    model: Any,
    tokenizer: Any,
    context_text: str,
    context_index: int,
    message: str,
    block_size: int,
    top_p: float,
    paper_suites: list[str],
    args: argparse.Namespace,
) -> dict[str, Any]:
    import torch

    context = tokenizer.encode(context_text, return_tensors="pt").to(args.device)
    started = perf_counter()
    try:
        generated_ids, encoded_messages, entropy_bits, stat_seconds, model_seconds, se_list = (
            official.encode_spar(
                model=model,
                context=context,
                message_bits=message,
                min_token_length=args.min_tokens,
                max_token_length=args.max_tokens,
                device=args.device,
                block_size=block_size,
                top_p=top_p,
                random_seed=args.seed,
            )
        )
    except Exception as error:  # noqa: BLE001
        elapsed = perf_counter() - started
        if isinstance(error, NameError) and "params_dict" in str(error):
            return {
                "block_size": block_size,
                "top_p": top_p,
                "context_index": context_index,
                "paper_suites": paper_suites,
                "status": "budget_exhausted",
                "error": f"{type(error).__name__}: {error}",
                "encode_seconds_before_failure": elapsed,
            }
        raise

    encode_wall = perf_counter() - started
    generation_seconds = max(0.0, encode_wall - float(stat_seconds))
    sampling_seconds = max(0.0, generation_seconds - float(model_seconds))
    decode_started = perf_counter()
    reconstructed, se_diff = official.decode_spar(
        model=model,
        generated_ids=generated_ids,
        context=context,
        enSE_list=se_list,
        device=args.device,
        block_size=block_size,
        top_p=top_p,
        random_seed=args.seed,
    )
    decode_seconds = perf_counter() - decode_started
    rendered = tokenizer.decode(generated_ids)
    regenerated = tokenizer.encode(rendered, return_tensors="pt")[0].tolist()
    token_ids = [int(token) for token in generated_ids]
    encoded_bits = sum(len(part) for part in encoded_messages)
    return {
        "block_size": block_size,
        "top_p": top_p,
        "context_index": context_index,
        "paper_suites": paper_suites,
        "status": "completed",
        "token_count": len(token_ids),
        "encoded_bits": encoded_bits,
        "entropy_bits": float(entropy_bits),
        "decode_success": reconstructed == encoded_messages,
        "hardware_inconsistency": bool(se_diff),
        "token_ambiguity": regenerated != token_ids,
        "token_sha256": token_sha256(token_ids),
        "encode_wall_seconds": encode_wall,
        "entropy_stat_seconds": float(stat_seconds),
        "model_seconds": float(model_seconds),
        "sampling_seconds": sampling_seconds,
        "generation_seconds": generation_seconds,
        "decode_seconds": decode_seconds,
        "cuda_peak_memory_bytes": (
            int(torch.cuda.max_memory_allocated()) if torch.cuda.is_available() else None
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=Path(".artifacts/sparsamp-official/extracted/Artifact new"),
    )
    parser.add_argument("--model", type=Path, default=Path("models/gpt2"))
    parser.add_argument("--output", type=Path, default=Path("outputs/official/R002_matrix.json"))
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--dtype", default="bfloat16")
    parser.add_argument("--contexts", type=int, default=100)
    parser.add_argument("--context-seed", type=int, default=42)
    parser.add_argument("--seed", type=int, default=777)
    parser.add_argument("--min-tokens", type=int, default=100)
    parser.add_argument("--max-tokens", type=int, default=200)
    parser.add_argument("--message-offset", type=int, default=19)
    parser.add_argument("--block-sizes", nargs="+", type=int, default=DEFAULT_BLOCK_SIZES)
    parser.add_argument("--top-ps", nargs="+", type=float, default=DEFAULT_TOP_PS)
    parser.add_argument("--max-new-trials", type=int, default=None)
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()
    if args.contexts < 1 or args.min_tokens < 1 or args.max_tokens < args.min_tokens:
        raise ValueError("context and token budgets are invalid")
    block_sizes = tuple(args.block_sizes)
    top_ps = tuple(args.top_ps)
    if len(block_sizes) != len(set(block_sizes)) or any(not 1 <= value <= 1023 for value in block_sizes):
        raise ValueError("block sizes must be unique and lie in [1, 1023]")
    if len(top_ps) != len(set(top_ps)) or any(not 0 < value <= 1 for value in top_ps):
        raise ValueError("top-p values must be unique and lie in (0, 1]")

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    source_dir = args.artifact_root / "Experiments" / "src"
    context_file = args.artifact_root / "Experiments" / "context_data" / "imdb_context.xlsx"
    message_file = source_dir / "message.txt"
    for required in (source_dir / "sparsamp.py", source_dir / "utils.py", context_file, message_file):
        if not required.is_file():
            raise FileNotFoundError(required)

    import pandas as pd
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    contexts = [str(value) for value in pd.read_excel(context_file)["context"].tolist()]
    if args.contexts > len(contexts):
        raise ValueError("requested more contexts than the artifact provides")
    context_indices = tuple(sorted(random.Random(args.context_seed).sample(range(len(contexts)), args.contexts)))
    message = message_file.read_text(encoding="utf-8").strip()[args.message_offset :]
    model_path = args.model.resolve()
    model_identity = model_fingerprint(model_path)
    source_hashes = {
        name: file_sha256(source_dir / name)
        for name in ("sparsamp.py", "utils.py", "get_statistics.py", "message.txt")
    }
    config = {
        "schema": SCHEMA,
        "artifact": {"zenodo_record": "15025436", "source_sha256": source_hashes},
        "paper_protocol": {
            "contexts": args.contexts,
            "context_seed": args.context_seed,
            "context_indices": list(context_indices),
            "min_tokens": args.min_tokens,
            "max_tokens": args.max_tokens,
            "block_sizes": list(block_sizes),
            "top_ps": list(top_ps),
            "seed": args.seed,
            "message_offset": args.message_offset,
        },
        "model": model_identity,
        "local_model_path": str(model_path),
        "device": args.device,
        "dtype": args.dtype,
    }
    plan = trial_plan(block_sizes, top_ps, context_indices)
    if args.fresh:
        archive_existing(args.output)
    rows = [] if args.fresh else load_rows(args.output, config)
    by_key = {trial_key(row): row for row in rows}
    environment = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "cuda": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "bf16_supported": torch.cuda.is_bf16_supported() if torch.cuda.is_available() else None,
    }
    write_atomic_json(args.output, build_report(config, rows, len(plan), environment))

    dtype = getattr(torch, args.dtype) if str(args.device).startswith("cuda") else torch.float32
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=dtype).to(args.device)
    model.eval()
    official = load_artifact_module(source_dir)
    new_trials = 0
    try:
        for specification in plan:
            key = trial_key(specification)
            if terminal(by_key.get(key, {})):
                continue
            if args.max_new_trials is not None and new_trials >= args.max_new_trials:
                break
            if torch.cuda.is_available():
                torch.cuda.reset_peak_memory_stats()
            try:
                row = run_trial(
                    official=official,
                    model=model,
                    tokenizer=tokenizer,
                    context_text=contexts[specification["context_index"]],
                    context_index=specification["context_index"],
                    message=message,
                    block_size=specification["block_size"],
                    top_p=specification["top_p"],
                    paper_suites=specification["paper_suites"],
                    args=args,
                )
            except Exception as error:  # noqa: BLE001
                row = {
                    **specification,
                    "status": "error",
                    "error": f"{type(error).__name__}: {error}",
                }
            if key in by_key:
                rows[rows.index(by_key[key])] = row
            else:
                rows.append(row)
            by_key[key] = row
            new_trials += 1
            write_atomic_json(args.output, build_report(config, rows, len(plan), environment))
            if row["status"] == "error":
                raise RuntimeError(row["error"])
            if new_trials % 10 == 0:
                print(f"checkpoint: {len(rows)}/{len(plan)} trials")
    finally:
        del model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    report = build_report(config, rows, len(plan), environment)
    write_atomic_json(args.output, report)
    print(json.dumps({"phase": report["phase"], "progress": report["progress"]}, indent=2))
    return 0 if report["phase"] == "completed" or args.max_new_trials is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
