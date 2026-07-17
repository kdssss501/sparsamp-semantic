"""Run resumable finite-token completion experiments with a local instruction model."""

from __future__ import annotations

import argparse
import copy
import hashlib
import hmac
import json
import os
import platform
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from sparsamp_semantic.core import (  # noqa: E402
    CodecConfig,
    IncompleteEncodeError,
    SparSampCodec,
    StepRecord,
)
from sparsamp_semantic.fh import FhCodecConfig, FhSparSampCodec  # noqa: E402
from sparsamp_semantic.finishing import FinishingConfig, finish_session  # noqa: E402
from sparsamp_semantic.fixed_length_rrc import (  # noqa: E402
    FixedLengthCoverSampler,
    FixedLengthRotationRangeCodec,
    FixedLengthRrcConfig,
)
from sparsamp_semantic.payload import PayloadCodec, bytes_to_bits  # noqa: E402
from sparsamp_semantic.providers.huggingface import (  # noqa: E402
    HuggingFaceConfig,
    HuggingFaceProvider,
)
from sparsamp_semantic.rrc import RrcConfig, RotationRangeCodec  # noqa: E402


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _git_value(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _runtime_metadata() -> dict[str, Any]:
    import torch
    import transformers

    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_version": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "git_commit": _git_value("rev-parse", "HEAD"),
        "git_dirty": bool(_git_value("status", "--porcelain")),
    }


def _deterministic_bytes(key: bytes, label: bytes, size: int) -> bytes:
    output = bytearray()
    counter = 0
    while len(output) < size:
        output.extend(hmac.new(key, label + counter.to_bytes(4, "big"), hashlib.sha256).digest())
        counter += 1
    return bytes(output[:size])


def _payload_for_seed(settings: dict[str, Any], key: bytes, seed: int) -> tuple[str, str]:
    payload = settings.get("payload", {"mode": "raw", "bit_length": 128})
    mode = payload.get("mode", "raw")
    label = f"{settings['experiment_id']}\0payload\0{seed}".encode()
    if mode == "raw":
        bit_length = int(payload.get("bit_length", 128))
        if bit_length < 1:
            raise ValueError("payload.bit_length must be positive")
        data = _deterministic_bytes(key, label, (bit_length + 7) // 8)
        return bytes_to_bits(data)[:bit_length], mode
    if mode == "message":
        message = str(payload.get("message", "experiment-{seed}")).format(seed=seed)
        repetitions = int(payload.get("repetitions", 1))
        nonce = _deterministic_bytes(key, label + b"\0nonce", 12)
        return PayloadCodec(repetitions=repetitions).seal(message, key, nonce=nonce), mode
    raise ValueError(f"unsupported payload mode: {mode}")


def _record_metrics(records: tuple[StepRecord, ...]) -> dict[str, Any]:
    embedded = [record for record in records if record.embedded]
    visible_entropies = [record.entropy_bits for record in records]
    total_latency_ms = sum(record.latency_ms for record in records)
    block_token_counts = Counter(
        record.block_size for record in records if record.block_size is not None
    )
    completed_block_schedule = [
        record.block_size
        for record in records
        if record.block_completed and record.block_size is not None
    ]
    rescue_records = [record for record in records if record.rescue_active]
    base_entropies = [
        record.base_entropy_bits
        for record in records
        if record.base_entropy_bits is not None
    ]
    forward_quantization_kls = [record.forward_quantization_kl_nats for record in records]
    quantization_tvs = [record.quantization_total_variation for record in records]
    return {
        "embedded_steps": len(embedded),
        "skipped_steps": len(records) - len(embedded),
        "completed_blocks": sum(record.block_completed for record in records),
        "mean_entropy_bits": (
            sum(record.entropy_bits for record in embedded) / len(embedded) if embedded else 0.0
        ),
        "mean_visible_entropy_bits": (
            mean(visible_entropies) if visible_entropies else 0.0
        ),
        "mean_source_mass": (
            sum(record.source_mass for record in records) / len(records) if records else 0.0
        ),
        "model_latency_ms": total_latency_ms,
        "mean_model_latency_ms": total_latency_ms / len(records) if records else 0.0,
        "candidate_count_mean": (
            sum(record.candidate_count for record in records) / len(records) if records else 0.0
        ),
        "truncation_kl_nats": sum(record.truncation_kl_nats for record in records),
        "forward_quantization_kl_nats": sum(forward_quantization_kls),
        "mean_forward_quantization_kl_nats": (
            mean(forward_quantization_kls) if forward_quantization_kls else 0.0
        ),
        "max_forward_quantization_kl_nats": max(forward_quantization_kls, default=0.0),
        "mean_quantization_total_variation": (
            mean(quantization_tvs) if quantization_tvs else 0.0
        ),
        "max_quantization_total_variation": max(quantization_tvs, default=0.0),
        "quantization_tv_step_sum": sum(quantization_tvs),
        "block_token_counts": {
            str(block_size): count for block_size, count in sorted(block_token_counts.items())
        },
        "completed_block_schedule": completed_block_schedule,
        "rescue_steps": len(rescue_records),
        "rescue_fraction": len(rescue_records) / len(records) if records else 0.0,
        "mean_base_entropy_bits": (
            sum(base_entropies) / len(base_entropies) if base_entropies else None
        ),
        "max_low_entropy_streak": max(
            (record.low_entropy_streak for record in records), default=0
        ),
    }


def _run_id(spec: dict[str, Any]) -> str:
    canonical = json.dumps(spec, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _existing_results(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    completed: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSONL at {path}:{line_number}") from error
        if row.get("status") in {"complete", "incomplete", "cover", "cover_fallback"}:
            completed[str(row["run_id"])] = row
    return completed


def _trajectory_key(spec: dict[str, Any]) -> str:
    variant = spec.get("codec_variant")
    budget_changes_trajectory = variant is not None and variant.get("kind") in {
        "fh",
        "fixed_rrc",
        "fixed_rrc_cover",
    }
    trajectory = {
        key: value
        for key, value in spec.items()
        if key != "token_budget" or budget_changes_trajectory
    }
    return json.dumps(trajectory, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sequence_difference(
    expected: tuple[Any, ...], observed: tuple[Any, ...]
) -> dict[str, Any] | None:
    for index in range(max(len(expected), len(observed))):
        expected_value = expected[index] if index < len(expected) else None
        observed_value = observed[index] if index < len(observed) else None
        if expected_value != observed_value:
            return {
                "first_index": index,
                "generated_token_id": expected_value,
                "retokenized_token_id": observed_value,
                "generated_token_count": len(expected),
                "retokenized_token_count": len(observed),
            }
    return None


def _iter_specs(settings: dict[str, Any]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    variants = settings.get("variants")
    for prompt_index, prompt in enumerate(settings["prompts"]):
        for payload_seed in settings["payload_seeds"]:
            for token_budget in settings["token_budgets"]:
                if variants is None:
                    for block_size in settings["block_sizes"]:
                        specs.append(
                            {
                                "experiment_id": settings["experiment_id"],
                                "prompt_index": prompt_index,
                                "prompt": prompt,
                                "payload_seed": int(payload_seed),
                                "token_budget": int(token_budget),
                                "block_size": int(block_size),
                                "top_p": float(settings.get("top_p", 0.95)),
                                "top_k": settings.get("top_k"),
                                "temperature": float(settings.get("temperature", 1.0)),
                            }
                        )
                    continue
                for variant in variants:
                    specs.append(
                        {
                            "experiment_id": settings["experiment_id"],
                            "prompt_index": prompt_index,
                            "prompt": prompt,
                            "payload_seed": int(payload_seed),
                            "token_budget": int(token_budget),
                            "variant": str(variant["name"]),
                            "codec_variant": variant,
                            "top_p": float(settings.get("top_p", 0.95)),
                            "top_k": settings.get("top_k"),
                            "temperature": float(settings.get("temperature", 1.0)),
                        }
                    )
    return specs


def _build_codec(
    spec: dict[str, Any], settings: dict[str, Any], total_bits: int
) -> SparSampCodec | FhSparSampCodec | RotationRangeCodec:
    common = {
        "max_tokens": spec["token_budget"],
        "min_source_mass": float(settings.get("min_source_mass", 0.0)),
        "probability_quantum": settings.get("probability_quantum", "1e-15"),
    }
    variant = spec.get("codec_variant")
    if variant is None:
        return SparSampCodec(CodecConfig(block_size=spec["block_size"], **common))
    kind = variant.get("kind")
    if kind == "fixed":
        return SparSampCodec(CodecConfig(block_size=int(variant["block_size"]), **common))
    if kind == "fh":
        return FhSparSampCodec(
            FhCodecConfig(
                total_bits=total_bits,
                block_sizes=tuple(int(value) for value in variant.get("block_sizes", [8, 16, 32])),
                entropy_ema_alpha=float(variant.get("entropy_ema_alpha", 0.2)),
                min_entropy_bits=float(variant.get("min_entropy_bits", 0.25)),
                tight_capacity_ratio=float(variant.get("tight_capacity_ratio", 1.0)),
                loose_capacity_ratio=float(variant.get("loose_capacity_ratio", 1.5)),
                **common,
            )
        )
    if kind == "schedule":
        schedule = tuple(int(value) for value in variant["block_schedule"])
        return FhSparSampCodec(
            FhCodecConfig(
                total_bits=total_bits,
                block_sizes=tuple(sorted(set(schedule))),
                block_schedule=schedule,
                **common,
            )
        )
    if kind == "rrc":
        return RotationRangeCodec(
            RrcConfig(
                message_bits=total_bits,
                max_tokens=spec["token_budget"],
                probability_quantum=settings.get("probability_quantum", "1e-15"),
                guard_digits=int(variant.get("guard_digits", 24)),
                min_precision=int(variant.get("min_precision", 48)),
                termination_mode=str(variant.get("termination_mode", "verified")),
            )
        )
    if kind == "fixed_rrc":
        return FixedLengthRotationRangeCodec(
            FixedLengthRrcConfig(
                payload_bits=total_bits,
                total_tokens=spec["token_budget"],
                tag_bits=int(variant.get("tag_bits", 128)),
                probability_quantum=settings.get("probability_quantum", "1e-15"),
                guard_digits=int(variant.get("guard_digits", 24)),
                min_precision=int(variant.get("min_precision", 48)),
                failure_mode=str(variant.get("failure_mode", "raise")),
            )
        )
    if kind == "fixed_rrc_cover":
        return FixedLengthCoverSampler(
            FixedLengthRrcConfig(
                payload_bits=total_bits,
                total_tokens=spec["token_budget"],
                tag_bits=int(variant.get("tag_bits", 128)),
                probability_quantum=settings.get("probability_quantum", "1e-15"),
                guard_digits=int(variant.get("guard_digits", 24)),
                min_precision=int(variant.get("min_precision", 48)),
                failure_mode="cover",
            )
        )
    raise ValueError(f"unsupported codec variant kind: {kind!r}")


def _finishing_config(spec: dict[str, Any], settings: dict[str, Any]) -> FinishingConfig:
    variant = spec.get("codec_variant") or {}
    return FinishingConfig(
        mode=str(variant.get("finish_mode", settings.get("finish_mode", "none"))),
        max_tokens=int(
            variant.get("finish_max_tokens", settings.get("finish_max_tokens", 32))
        ),
        min_tokens=int(
            variant.get("finish_min_tokens", settings.get("finish_min_tokens", 4))
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/qwen15_completion_pilot.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/qwen15-completion.jsonl"))
    parser.add_argument("--limit-runs", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings = json.loads(args.config.read_text(encoding="utf-8"))
    specs = _iter_specs(settings)
    existing = _existing_results(args.output)
    pending = [spec for spec in specs if _run_id(spec) not in existing]
    if args.limit_runs is not None:
        if args.limit_runs < 1:
            raise ValueError("--limit-runs must be positive")
        pending = pending[: args.limit_runs]
    print(
        f"planned={len(specs)} completed={len(existing)} pending={len(pending)} "
        f"max_token_steps={sum(spec['token_budget'] for spec in pending)}",
        flush=True,
    )
    if args.dry_run or not pending:
        return 0

    key = os.environ.get("SPARSAMP_SECRET_KEY", "").encode("utf-8")
    if len(key) < 16:
        raise RuntimeError("SPARSAMP_SECRET_KEY must contain at least 16 bytes")

    base_config = HuggingFaceConfig(
        model_name=settings["model"],
        revision=settings.get("revision"),
        top_p=float(settings.get("top_p", 0.95)),
        top_k=settings.get("top_k"),
        temperature=float(settings.get("temperature", 1.0)),
        device=settings.get("device", "auto"),
        dtype=settings.get("dtype", "float16"),
        load_in_4bit=bool(settings.get("load_in_4bit", False)),
        system_prompt=settings.get("system_prompt", HuggingFaceConfig.system_prompt),
        allow_eos=bool(settings.get("allow_eos", False)),
        seed=int(settings.get("model_seed", 42)),
        adaptive_temperature=bool(settings.get("adaptive_temperature", False)),
        entropy_floor_bits=float(settings.get("entropy_floor_bits", 0.75)),
        rescue_temperature=float(settings.get("rescue_temperature", 1.1)),
        rescue_patience=int(settings.get("rescue_patience", 8)),
    )
    provider = HuggingFaceProvider(base_config)
    runtime = _runtime_metadata()
    key_fingerprint = hashlib.sha256(key).hexdigest()[:12]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    completion_cache = {
        _trajectory_key(row["spec"]): row
        for row in existing.values()
        if row.get("status") == "complete"
    }

    with args.output.open("a", encoding="utf-8") as stream:
        for index, spec in enumerate(pending, start=1):
            run_id = _run_id(spec)
            cached = completion_cache.get(_trajectory_key(spec))
            if cached is not None and int(
                cached["metrics"].get("embedded_token_count", cached["metrics"]["token_count"])
            ) <= spec["token_budget"]:
                row = copy.deepcopy(cached)
                row.update(
                    {
                        "run_id": run_id,
                        "timestamp": _utc_now(),
                        "spec": spec,
                        "derived_from_run_id": cached["run_id"],
                    }
                )
                row["codec"]["max_tokens"] = spec["token_budget"]
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
                print(
                    f"[{index}/{len(pending)}] run={run_id} derived={cached['run_id']} "
                    f"budget={spec['token_budget']} tokens={row['metrics']['token_count']}",
                    flush=True,
                )
                continue
            payload_bits, payload_mode = _payload_for_seed(settings, key, spec["payload_seed"])
            codec = _build_codec(spec, settings, len(payload_bits))
            finishing_config = _finishing_config(spec, settings)
            if (
                isinstance(codec, (FixedLengthRotationRangeCodec, FixedLengthCoverSampler))
                and finishing_config.mode != "none"
            ):
                raise ValueError("fixed_rrc requires finish_mode='none'")
            session_config = replace(
                base_config,
                top_p=spec["top_p"],
                top_k=spec["top_k"],
                temperature=spec["temperature"],
            )
            variant_label = spec.get("variant", f"fixed-{spec.get('block_size')}")
            print(
                f"[{index}/{len(pending)}] run={run_id} prompt={spec['prompt_index']} "
                f"seed={spec['payload_seed']} budget={spec['token_budget']} "
                f"variant={variant_label}",
                flush=True,
            )
            row: dict[str, Any] = {
                "run_id": run_id,
                "timestamp": _utc_now(),
                "status": "error",
                "spec": spec,
                "payload": {
                    "mode": payload_mode,
                    "bit_length": len(payload_bits),
                    "sha256": hashlib.sha256(payload_bits.encode()).hexdigest(),
                    "key_fingerprint": key_fingerprint,
                },
                "model": asdict(session_config),
                "codec": asdict(codec.config),
                "finishing": asdict(finishing_config),
                "runtime": runtime,
            }
            try:
                session = provider.start_with_config(spec["prompt"], session_config)
                try:
                    encoded = codec.encode(session, payload_bits, key)
                except IncompleteEncodeError as error:
                    status = "incomplete"
                    token_ids = error.token_ids
                    embedded_token_count = len(token_ids)
                    cover_text = error.text
                    completed_bits = error.completed_bits
                    embedding_elapsed_seconds = error.elapsed_seconds
                    finishing_elapsed_seconds = 0.0
                    records = error.records
                    padded_bits = (
                        0
                        if isinstance(
                            codec,
                            (
                                FhSparSampCodec,
                                RotationRangeCodec,
                                FixedLengthRotationRangeCodec,
                                FixedLengthCoverSampler,
                            ),
                        )
                        else (-len(payload_bits)) % codec.config.block_size
                    )
                else:
                    is_cover = isinstance(codec, FixedLengthCoverSampler)
                    payload_embedded = bool(getattr(encoded, "payload_embedded", True))
                    status = (
                        "cover"
                        if is_cover
                        else "complete" if payload_embedded else "cover_fallback"
                    )
                    embedded_token_count = int(
                        getattr(encoded, "embedded_token_count", len(encoded.token_ids))
                    )
                    finished = finish_session(session, finishing_config)
                    token_ids = finished.token_ids
                    cover_text = finished.text
                    completed_bits = encoded.embedded_bits
                    embedding_elapsed_seconds = encoded.elapsed_seconds
                    finishing_elapsed_seconds = finished.elapsed_seconds
                    records = encoded.records
                    padded_bits = encoded.padded_bits

                retokenized = session.retokenize(cover_text)
                ambiguity_detail = _sequence_difference(token_ids, retokenized)
                token_ambiguity = ambiguity_detail is not None
                decode_exact: bool | None = None
                recovered_message: str | None = None
                if status == "complete" and bool(settings.get("verify_decode", True)):
                    decode_tokens = (
                        token_ids
                        if isinstance(codec, FixedLengthRotationRangeCodec)
                        else token_ids[:embedded_token_count]
                    )
                    decoded = codec.decode(
                        provider.start_with_config(spec["prompt"], session_config),
                        decode_tokens,
                        key,
                    )
                    decode_exact = decoded.bits[: len(payload_bits)] == payload_bits
                    if decode_exact and payload_mode == "message":
                        repetitions = int(settings["payload"].get("repetitions", 1))
                        recovered_message = PayloadCodec(repetitions=repetitions).open(
                            decoded.bits, key
                        )

                metrics = _record_metrics(records)
                metrics.update(
                    {
                        "success": status == "complete",
                        "completed_bits": completed_bits,
                        "total_bits": len(payload_bits),
                        "completion_fraction": completed_bits / len(payload_bits),
                        "token_count": len(token_ids),
                        "fixed_padding_token_count": (
                            len(token_ids) - embedded_token_count
                            if isinstance(
                                codec, (FixedLengthRotationRangeCodec, FixedLengthCoverSampler)
                            )
                            else 0
                        ),
                        "embedded_token_count": embedded_token_count,
                        "visible_token_count": len(token_ids),
                        "tail_token_count": len(token_ids) - embedded_token_count,
                        "completed_bits_per_token": (
                            completed_bits / embedded_token_count
                            if embedded_token_count
                            else 0.0
                        ),
                        "completed_bits_per_visible_token": (
                            completed_bits / len(token_ids) if token_ids else 0.0
                        ),
                        "elapsed_seconds": (
                            embedding_elapsed_seconds + finishing_elapsed_seconds
                        ),
                        "embedding_elapsed_seconds": embedding_elapsed_seconds,
                        "finishing_elapsed_seconds": finishing_elapsed_seconds,
                        "tokens_per_second": (
                            embedded_token_count / embedding_elapsed_seconds
                            if embedding_elapsed_seconds
                            else 0.0
                        ),
                        "visible_tokens_per_second": (
                            len(token_ids)
                            / (embedding_elapsed_seconds + finishing_elapsed_seconds)
                            if embedding_elapsed_seconds + finishing_elapsed_seconds
                            else 0.0
                        ),
                        "padded_bits": padded_bits,
                        "decode_exact": decode_exact,
                        "token_ambiguity": token_ambiguity,
                        "token_ambiguity_detail": ambiguity_detail,
                    }
                )
                row.update(
                    {
                        "status": status,
                        "cover_text": cover_text,
                        "token_ids": token_ids,
                        "recovered_message": recovered_message,
                        "metrics": metrics,
                    }
                )
            except Exception as error:
                row["error"] = {"type": type(error).__name__, "message": str(error)}
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
                if not bool(settings.get("continue_on_error", False)):
                    raise
            else:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
                if row["status"] == "complete":
                    completion_cache[_trajectory_key(spec)] = row
                print(
                    f"  status={row['status']} embedded={row['metrics']['embedded_token_count']} "
                    f"visible={row['metrics']['visible_token_count']} "
                    f"progress={row['metrics']['completion_fraction']:.1%} "
                    f"tok/s={row['metrics']['tokens_per_second']:.2f} "
                    f"ambiguity={row['metrics']['token_ambiguity']}",
                    flush=True,
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
