"""R036 raw-byte pilot for the fixed bin-mass precision contract."""

from __future__ import annotations

import argparse
import gc
import hashlib
import hmac
import json
import platform
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from sparsamp_semantic.byte_sliced import ByteSlicedCodec, ByteSlicedConfig  # noqa: E402
from sparsamp_semantic.providers.huggingface import (  # noqa: E402
    HuggingFaceConfig,
    HuggingFaceProvider,
)


DEFAULT_PROMPTS = (
    "Explain why reproducible AI experiments matter.",
    "Describe two practices that improve secure software updates.",
    "Explain one benefit and one risk of language models in education.",
)
KEY = b"r036-bin-mass-audit-key-0123456789"
SCHEMA = "sparsamp-r036-bin-mass-raw-byte-pilot-v1"


def payload_for_seed(seed: int, size: int) -> bytes:
    """Derive a deterministic, domain-separated raw payload."""

    output = bytearray()
    counter = 0
    label = f"R036\0payload\0{seed}".encode()
    while len(output) < size:
        output.extend(hmac.new(KEY, label + counter.to_bytes(4, "big"), hashlib.sha256).digest())
        counter += 1
    return bytes(output[:size])


def bit_errors(expected: bytes, observed: bytes | None) -> int:
    if observed is None:
        return len(expected) * 8
    return sum(
        (left ^ right).bit_count() for left, right in zip(expected, observed, strict=False)
    ) + max(0, len(expected) - len(observed)) * 8


def raw_symbol_errors(expected_codeword: bytes, records: list[Any]) -> int:
    """Count wrong, erased, and missing codeword symbols."""

    errors = 0
    for record in records:
        index = int(record.window_index)
        expected = expected_codeword[index] if index < len(expected_codeword) else None
        if record.recovered_symbol is None or expected is None or record.recovered_symbol != expected:
            errors += 1
    return errors + max(0, len(expected_codeword) - len(records))


def normalized_optional_float(value: float | None) -> float | None:
    """Treat CLI zero as a disabled optional float contract."""

    return None if value == 0 else value


def normalized_optional_int(value: int | None) -> int | None:
    """Treat CLI zero as a disabled optional integer contract."""

    return None if value == 0 else value


def variant_name(window_tokens: int, parity_bytes: int) -> str:
    return f"window={window_tokens},parity={parity_bytes}"


def trial_key(row: dict[str, Any]) -> tuple[int, int, int, int]:
    """Return the stable identity of one prompt/payload/variant trial."""

    return (
        int(row["prompt_index"]),
        int(row["payload_seed"]),
        int(row["window_tokens"]),
        int(row["parity_bytes"]),
    )


def _aggregate_rate(rows: list[dict[str, Any]], success_field: str) -> float:
    total_tokens = sum(int(row.get("token_count", 0)) for row in rows)
    recovered_bits = sum(
        int(row["payload_bits"]) for row in rows if bool(row.get(success_field))
    )
    return recovered_bits / total_tokens if total_tokens else 0.0


def summarize(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Summarize every attempted trial, including failures in rates and BER."""

    result: dict[str, dict[str, Any]] = {}
    for variant in sorted({str(row["variant"]) for row in rows}):
        selected = [row for row in rows if row["variant"] == variant]
        encoded = [row for row in selected if bool(row.get("encode_success"))]
        total_bits = sum(int(row["payload_bits"]) for row in selected)
        total_tokens = sum(int(row.get("token_count", 0)) for row in encoded)
        same_successes = sum(bool(row.get("same_precision_success")) for row in selected)
        cross_successes = sum(bool(row.get("cross_precision_success")) for row in selected)
        result[variant] = {
            "trials": len(selected),
            "encode_successes": len(encoded),
            "same_precision_successes": same_successes,
            "same_precision_rate": same_successes / len(selected) if selected else 0.0,
            "cross_precision_successes": cross_successes,
            "cross_precision_rate": cross_successes / len(selected) if selected else 0.0,
            "same_precision_aggregate_ber": (
                sum(int(row.get("same_precision_bit_errors", row["payload_bits"])) for row in selected)
                / total_bits
                if total_bits
                else 0.0
            ),
            "cross_precision_aggregate_ber": (
                sum(int(row.get("cross_precision_bit_errors", row["payload_bits"])) for row in selected)
                / total_bits
                if total_bits
                else 0.0
            ),
            "aggregate_net_payload_bits_per_token": (
                sum(int(row["payload_bits"]) for row in encoded) / total_tokens
                if total_tokens
                else 0.0
            ),
            "same_precision_effective_bits_per_token": _aggregate_rate(
                encoded, "same_precision_success"
            ),
            "cross_precision_effective_bits_per_token": _aggregate_rate(
                encoded, "cross_precision_success"
            ),
            "mean_codeword_bits_per_token": (
                mean(float(row["codeword_bits_per_token"]) for row in encoded)
                if encoded
                else 0.0
            ),
            "mean_same_precision_erasures": (
                mean(int(row.get("same_precision_erasure_count", 0)) for row in selected)
                if selected
                else 0.0
            ),
            "mean_cross_precision_erasures": (
                mean(int(row.get("cross_precision_erasure_count", 0)) for row in selected)
                if selected
                else 0.0
            ),
            "mean_same_precision_raw_symbol_errors": (
                mean(int(row.get("same_precision_raw_symbol_errors", 0)) for row in selected)
                if selected
                else 0.0
            ),
            "mean_cross_precision_raw_symbol_errors": (
                mean(int(row.get("cross_precision_raw_symbol_errors", 0)) for row in selected)
                if selected
                else 0.0
            ),
            "total_encode_seconds": sum(float(row.get("encode_seconds", 0.0)) for row in selected),
            "total_same_precision_decode_seconds": sum(
                float(row.get("same_precision_decode_seconds", 0.0)) for row in selected
            ),
            "total_cross_precision_decode_seconds": sum(
                float(row.get("cross_precision_decode_seconds", 0.0)) for row in selected
            ),
        }
    return result


def release_cuda() -> None:
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


def experiment_config(
    args: Any, variants: list[tuple[int, int]], prompts: tuple[str, ...] = DEFAULT_PROMPTS
) -> dict[str, Any]:
    """Return every field that must match before checkpoint rows can be reused."""

    prompt_bytes = json.dumps(prompts, ensure_ascii=False, separators=(",", ":")).encode()
    trial_keys = [
        [prompt_index, int(seed), window, parity]
        for prompt_index in range(len(prompts))
        for seed in args.payload_seeds
        for window, parity in variants
    ]
    return {
        "schema": SCHEMA,
        "run_label": str(args.run_label),
        "model": str(args.model),
        "device": str(args.device),
        "reference_dtype": str(args.reference_dtype),
        "replay_dtype": str(args.replay_dtype),
        "top_p": float(args.top_p),
        "top_k": normalized_optional_int(args.top_k),
        "logit_quantum": normalized_optional_float(args.logit_quantum),
        "bin_mass_bits": normalized_optional_int(args.bin_mass_bits),
        "temperature": float(args.temperature),
        "candidate_order": "token_id",
        "precision_context": "portable",
        "allow_eos": False,
        "adaptive_temperature": False,
        "payload_bytes": int(args.payload_bytes),
        "payload_seeds": [int(seed) for seed in args.payload_seeds],
        "prompt_count": len(prompts),
        "prompts_sha256": hashlib.sha256(prompt_bytes).hexdigest(),
        "key_sha256": hashlib.sha256(KEY).hexdigest(),
        "variants": [variant_name(window, parity) for window, parity in variants],
        "trial_keys": trial_keys,
    }


def config_signature(config: dict[str, Any]) -> str:
    material = json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(material.encode()).hexdigest()


def acceptance_summary(
    summaries: dict[str, dict[str, Any]], expected_trials: int
) -> dict[str, Any]:
    """Apply the pre-registered R036 gate and deterministic selection rule."""

    required_cross = (5 * expected_trials + 5) // 6
    variants: dict[str, dict[str, Any]] = {}
    eligible: list[tuple[str, dict[str, Any]]] = []
    for name, summary in summaries.items():
        same_go = (
            int(summary["trials"]) == expected_trials
            and int(summary["same_precision_successes"]) == expected_trials
        )
        cross_go = (
            int(summary["trials"]) == expected_trials
            and int(summary["cross_precision_successes"]) >= required_cross
        )
        variants[name] = {
            "same_precision_go": same_go,
            "cross_precision_go": cross_go,
            "go": same_go and cross_go,
        }
        if same_go and cross_go:
            eligible.append((name, summary))
    eligible.sort(
        key=lambda item: (
            -int(item[1]["cross_precision_successes"]),
            -float(item[1]["aggregate_net_payload_bits_per_token"]),
            float(item[1]["total_encode_seconds"])
            + float(item[1]["total_same_precision_decode_seconds"])
            + float(item[1]["total_cross_precision_decode_seconds"]),
            item[0],
        )
    )
    return {
        "expected_trials_per_variant": expected_trials,
        "required_same_precision_successes": expected_trials,
        "required_cross_precision_successes": required_cross,
        "variants": variants,
        "overall_go": bool(eligible),
        "selected_variant": eligible[0][0] if eligible else None,
    }


def build_report(
    args: Any,
    variants: list[tuple[int, int]],
    rows: list[dict[str, Any]],
    phase: str,
) -> dict[str, Any]:
    """Build a complete or checkpoint report without exposing key material."""

    config = experiment_config(args, variants)
    summaries = summarize(rows)
    expected_trials = len(DEFAULT_PROMPTS) * len(args.payload_seeds)
    return {
        "schema": SCHEMA,
        "run_label": args.run_label,
        "phase": phase,
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "experiment_config": config,
        "experiment_signature": config_signature(config),
        "progress": {
            "reference_trials": len(rows),
            "cross_precision_trials": sum(bool(row.get("cross_precision_processed")) for row in rows),
            "expected_total_trials": expected_trials * len(variants),
        },
        "summary": summaries,
        "acceptance": (
            acceptance_summary(summaries, expected_trials) if phase == "completed" else None
        ),
        "rows": rows,
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    """Atomically persist a report so interruptions retain completed trials."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def archive_existing_report(path: Path) -> Path | None:
    """Preserve an earlier run before an explicit fresh initialization."""

    if not path.exists():
        return None
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    archived = path.with_name(f"{path.stem}.{timestamp}{path.suffix}")
    path.replace(archived)
    return archived


def load_checkpoint_rows(path: Path, expected_config: dict[str, Any]) -> list[dict[str, Any]]:
    """Load compatible rows and reject mixed settings or duplicate trials."""

    if not path.exists():
        return []
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("experiment_config") != expected_config:
        raise ValueError(
            "checkpoint experiment_config does not match this command; "
            "use another output path or pass --fresh"
        )
    if report.get("experiment_signature") != config_signature(expected_config):
        raise ValueError("checkpoint experiment_signature is invalid")
    rows = report.get("rows")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("checkpoint rows must be a list of objects")
    keys = [trial_key(row) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("checkpoint contains duplicate trial identities")
    expected_keys = {
        tuple(int(value) for value in values) for values in expected_config["trial_keys"]
    }
    if not set(keys) <= expected_keys:
        raise ValueError("checkpoint contains a trial outside the configured matrix")
    return rows


def _provider_config(args: Any, dtype: str) -> HuggingFaceConfig:
    return HuggingFaceConfig(
        model_name=args.model,
        top_p=args.top_p,
        top_k=normalized_optional_int(args.top_k),
        logit_quantum=normalized_optional_float(args.logit_quantum),
        bin_mass_bits=normalized_optional_int(args.bin_mass_bits),
        candidate_order="token_id",
        temperature=args.temperature,
        precision_context="portable",
        device=args.device,
        dtype=dtype,
        allow_eos=False,
        adaptive_temperature=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="models/gpt2")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--reference-dtype", default="float32")
    parser.add_argument("--replay-dtype", default="float16")
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--top-k", type=int, default=2, help="zero disables fixed top-k")
    parser.add_argument(
        "--logit-quantum", type=float, default=0.5, help="zero disables logit quantization"
    )
    parser.add_argument(
        "--bin-mass-bits", type=int, default=16, help="zero disables integer bin mass"
    )
    parser.add_argument("--temperature", type=float, default=1.2)
    parser.add_argument("--payload-bytes", type=int, default=2)
    parser.add_argument("--payload-seeds", type=int, nargs="+", default=[0, 1])
    parser.add_argument("--parity-bytes", type=int, nargs="+", default=[0, 2])
    parser.add_argument("--window-tokens", type=int, nargs="+", default=[16, 32])
    parser.add_argument("--run-label", default="R036")
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="ignore an existing checkpoint and initialize this output from zero trials",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/R036_gpt2_bin_mass_raw_bytes.json")
    )
    args = parser.parse_args()
    if args.payload_bytes < 1:
        raise ValueError("payload-bytes must be positive")
    if not args.payload_seeds:
        raise ValueError("payload-seeds must not be empty")
    if len(args.payload_seeds) != len(set(args.payload_seeds)):
        raise ValueError("payload-seeds must be unique")
    if any(window < 1 for window in args.window_tokens):
        raise ValueError("window-tokens must be positive")
    if len(args.window_tokens) != len(set(args.window_tokens)):
        raise ValueError("window-tokens must be unique")
    if len(args.parity_bytes) != len(set(args.parity_bytes)):
        raise ValueError("parity-bytes must be unique")

    variants = [
        (window, parity) for window in args.window_tokens for parity in args.parity_bytes
    ]
    config = experiment_config(args, variants)
    rows: list[dict[str, Any]] = [] if args.fresh else load_checkpoint_rows(args.output, config)
    if args.fresh:
        archive_existing_report(args.output)
    if args.fresh or not args.output.exists():
        write_report(args.output, build_report(args, variants, rows, "initialized"))

    reference_keys = {trial_key(row) for row in rows}
    expected_keys = {
        (prompt_index, seed, window, parity)
        for prompt_index in range(len(DEFAULT_PROMPTS))
        for seed in args.payload_seeds
        for window, parity in variants
    }
    if expected_keys - reference_keys:
        reference_provider = HuggingFaceProvider(_provider_config(args, args.reference_dtype))
        for prompt_index, prompt in enumerate(DEFAULT_PROMPTS):
            for seed in args.payload_seeds:
                payload = payload_for_seed(seed, args.payload_bytes)
                for window, parity in variants:
                    key = (prompt_index, seed, window, parity)
                    if key in reference_keys:
                        continue
                    codec_config = ByteSlicedConfig(window_tokens=window, parity_bytes=parity)
                    codec = ByteSlicedCodec(codec_config)
                    row: dict[str, Any] = {
                        "prompt_index": prompt_index,
                        "prompt": prompt,
                        "payload_seed": seed,
                        "payload_bits": len(payload) * 8,
                        "payload_sha256": hashlib.sha256(payload).hexdigest(),
                        "window_tokens": window,
                        "parity_bytes": parity,
                        "variant": variant_name(window, parity),
                        "codec": asdict(codec_config),
                        "encode_success": False,
                        "same_precision_success": False,
                        "cross_precision_success": False,
                        "same_precision_bit_errors": len(payload) * 8,
                        "cross_precision_bit_errors": len(payload) * 8,
                        "same_precision_erasure_count": 0,
                        "cross_precision_erasure_count": 0,
                        "same_precision_raw_symbol_errors": 0,
                        "cross_precision_raw_symbol_errors": 0,
                        "cross_precision_processed": False,
                    }
                    encode_started = perf_counter()
                    try:
                        encoded = codec.encode(reference_provider.start(prompt), payload, KEY)
                    except Exception as error:  # noqa: BLE001 - preserve exact trial failure
                        row["encode_seconds"] = perf_counter() - encode_started
                        row["encode_error"] = {
                            "type": type(error).__name__,
                            "message": str(error),
                        }
                        row["cross_precision_processed"] = True
                        rows.append(row)
                        reference_keys.add(key)
                        write_report(
                            args.output,
                            build_report(args, variants, rows, "reference_partial"),
                        )
                        continue
                    expected_codeword = encoded.codeword_bytes
                    row.update(
                        {
                            "encode_success": True,
                            "encode_seconds": encoded.elapsed_seconds,
                            "token_ids": [int(value) for value in encoded.token_ids],
                            "token_count": len(encoded.token_ids),
                            "net_payload_bits_per_token": encoded.payload_bits_per_token,
                            "codeword_bits_per_token": encoded.codeword_bits_per_token,
                            "codeword_hex": expected_codeword.hex(),
                            "guard_aborted_windows": sum(
                                record.guard_aborted for record in encoded.records
                            ),
                        }
                    )
                    decode_started = perf_counter()
                    try:
                        same = codec.decode(reference_provider.start(prompt), encoded.token_ids, KEY)
                        row["same_precision_success"] = same.payload_bytes == payload
                        row["same_precision_bit_errors"] = bit_errors(payload, same.payload_bytes)
                        row["same_precision_erasure_count"] = same.erasure_count
                        row["same_precision_raw_symbol_errors"] = raw_symbol_errors(
                            expected_codeword, list(same.records)
                        )
                        row["same_precision_decode_error"] = same.error
                    except Exception as error:  # noqa: BLE001
                        row["same_precision_raw_symbol_errors"] = len(expected_codeword)
                        row["same_precision_decode_error"] = (
                            f"{type(error).__name__}: {error}"
                        )
                    row["same_precision_decode_seconds"] = perf_counter() - decode_started
                    rows.append(row)
                    reference_keys.add(key)
                    write_report(
                        args.output,
                        build_report(args, variants, rows, "reference_partial"),
                    )
        del reference_provider
        release_cuda()

    pending_replay = [
        row
        for row in rows
        if bool(row.get("encode_success")) and not bool(row.get("cross_precision_processed"))
    ]
    if pending_replay:
        replay_provider = HuggingFaceProvider(_provider_config(args, args.replay_dtype))
        for row in pending_replay:
            codec = ByteSlicedCodec(ByteSlicedConfig(**row["codec"]))
            payload = payload_for_seed(int(row["payload_seed"]), int(row["payload_bits"]) // 8)
            expected_codeword = bytes.fromhex(str(row["codeword_hex"]))
            decode_started = perf_counter()
            try:
                decoded = codec.decode(
                    replay_provider.start(str(row["prompt"])),
                    tuple(int(value) for value in row["token_ids"]),
                    KEY,
                )
                row["cross_precision_success"] = decoded.payload_bytes == payload
                row["cross_precision_bit_errors"] = bit_errors(payload, decoded.payload_bytes)
                row["cross_precision_erasure_count"] = decoded.erasure_count
                row["cross_precision_raw_symbol_errors"] = raw_symbol_errors(
                    expected_codeword, list(decoded.records)
                )
                row["recovered_payload_hex"] = (
                    decoded.payload_bytes.hex() if decoded.payload_bytes is not None else None
                )
                row["cross_precision_decode_error"] = decoded.error
            except Exception as error:  # noqa: BLE001
                row["cross_precision_raw_symbol_errors"] = len(expected_codeword)
                row["cross_precision_decode_error"] = f"{type(error).__name__}: {error}"
            row["cross_precision_decode_seconds"] = perf_counter() - decode_started
            row["cross_precision_processed"] = True
            write_report(
                args.output,
                build_report(args, variants, rows, "replay_partial"),
            )
        del replay_provider
        release_cuda()

    report = build_report(args, variants, rows, "completed")
    write_report(args.output, report)
    print(json.dumps({"summary": report["summary"], "acceptance": report["acceptance"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
