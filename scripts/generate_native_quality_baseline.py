"""Generate a checkpointed, unquantized top-k Qwen quality baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.audit_replay_certificate import (  # noqa: E402
    DEFAULT_SYSTEM_PROMPT,
    archive_existing,
    load_prompts,
    release_cuda,
)
from sparsamp_semantic.finishing import is_sentence_complete  # noqa: E402
from sparsamp_semantic.providers.huggingface import (  # noqa: E402
    HuggingFaceConfig,
    HuggingFaceProvider,
)
from sparsamp_semantic.replay_package import (  # noqa: E402
    canonical_signature,
    runtime_fingerprint,
    write_atomic_json,
)


SCHEMA = "r048-native-top-k-baseline-v1"


def experiment_config(args: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "run_label": args.run_label,
        "model": str(args.model),
        "device": args.device,
        "dtype": args.dtype,
        "seed": args.seed,
        "top_k": args.top_k,
        "temperature": args.temperature,
        "tokens": args.tokens,
        "sentence_stop_min_tokens": args.sentence_stop_min_tokens,
        "system_prompt": args.system_prompt,
        "prompts_file": str(args.prompts_file),
        "prompts": list(args.prompt_values),
    }


def load_rows(path: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("experiment_config") != config:
        raise ValueError("native baseline checkpoint configuration mismatch")
    rows = report.get("rows")
    if not isinstance(rows, list):
        raise ValueError("native baseline checkpoint rows are invalid")
    indices = [int(row["prompt_index"]) for row in rows]
    if len(indices) != len(set(indices)):
        raise ValueError("native baseline checkpoint contains duplicate prompts")
    return rows


def build_report(
    config: dict[str, Any], rows: list[dict[str, Any]], environment: dict[str, Any]
) -> dict[str, Any]:
    expected = len(config["prompts"])
    complete = len(rows) == expected and all(bool(row.get("completed")) for row in rows)
    return {
        "schema": SCHEMA,
        "phase": "completed" if complete else "partial",
        "timestamp": datetime.now(UTC).isoformat(),
        "experiment_config": config,
        "experiment_signature": canonical_signature(config),
        "environment": environment,
        "progress": {"completed_trials": len(rows), "expected_trials": expected},
        "rows": sorted(rows, key=lambda row: int(row["prompt_index"])),
    }


def generate_row(provider: HuggingFaceProvider, args: Any, index: int, prompt: str) -> dict:
    session = provider.start(prompt)
    token_ids: list[int] = []
    stopped_on_sentence = False
    started = perf_counter()
    for step in range(args.tokens):
        snapshot = session.next_distribution()
        token_id = int(snapshot.native_token_id)
        session.append(token_id)
        token_ids.append(token_id)
        if (
            step + 1 >= args.sentence_stop_min_tokens
            and is_sentence_complete(session.render())
        ):
            stopped_on_sentence = True
            break
    text = session.render()
    token_payload = b"".join(token.to_bytes(4, "big") for token in token_ids)
    return {
        "prompt_index": index,
        "prompt": prompt,
        "seed": args.seed,
        "sampler": f"native-top-{args.top_k}",
        "completed": True,
        "text": text,
        "token_ids": token_ids,
        "token_sha256": hashlib.sha256(token_payload).hexdigest(),
        "token_count": len(token_ids),
        "sentence_complete": is_sentence_complete(text),
        "stopped_on_sentence": stopped_on_sentence,
        "seconds": perf_counter() - started,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--prompts-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--dtype", default="float16")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--top-k", type=int, default=16)
    parser.add_argument("--temperature", type=float, default=1.2)
    parser.add_argument("--tokens", type=int, default=96)
    parser.add_argument("--sentence-stop-min-tokens", type=int, default=64)
    parser.add_argument("--system-prompt", default=DEFAULT_SYSTEM_PROMPT)
    parser.add_argument("--run-label", default="R048-native")
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()
    args.prompt_values = load_prompts(args.prompts_file)
    if args.seed < 0 or args.top_k < 2 or args.tokens < 1:
        raise ValueError("seed, top-k or token count is out of range")
    if not 0 <= args.sentence_stop_min_tokens <= args.tokens:
        raise ValueError("sentence stop minimum is out of range")

    config = experiment_config(args)
    if args.fresh:
        archive_existing(args.output)
    rows = [] if args.fresh else load_rows(args.output, config)
    environment = runtime_fingerprint()
    write_atomic_json(args.output, build_report(config, rows, environment))
    completed = {int(row["prompt_index"]) for row in rows if bool(row.get("completed"))}

    provider = HuggingFaceProvider(
        HuggingFaceConfig(
            model_name=str(args.model),
            top_p=1.0,
            top_k=args.top_k,
            logit_quantum=None,
            temperature=args.temperature,
            device=args.device,
            dtype=args.dtype,
            precision_context="portable",
            system_prompt=args.system_prompt,
            allow_eos=False,
            seed=args.seed,
        )
    )
    for index, prompt in enumerate(args.prompt_values):
        if index in completed:
            continue
        row = generate_row(provider, args, index, prompt)
        rows.append(row)
        write_atomic_json(args.output, build_report(config, rows, environment))
    del provider
    release_cuda()

    report = build_report(config, rows, environment)
    write_atomic_json(args.output, report)
    print(json.dumps({"phase": report["phase"], "progress": report["progress"]}, indent=2))
    return 0 if report["phase"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
