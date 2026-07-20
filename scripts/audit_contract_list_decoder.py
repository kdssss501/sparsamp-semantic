"""R036-D4 online Contract-List decoding audit over saved R036 token streams."""

from __future__ import annotations

import argparse
import gc
import hashlib
import itertools
import json
import platform
import sys
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.audit_bin_mass_failure_modes import file_sha256, load_source_report  # noqa: E402
from scripts.audit_byte_sliced_messages import (  # noqa: E402
    archive_existing_report,
    config_signature,
    trial_key,
    write_report,
)
from sparsamp_semantic.contract_list import (  # noqa: E402
    ContractListByteDecoder,
    ContractListConfig,
)
from sparsamp_semantic.providers.huggingface import (  # noqa: E402
    HuggingFaceConfig,
    HuggingFaceProvider,
)

SCHEMA = "sparsamp-r036d4-contract-list-decoder-v1"


def recover_payload_candidates(
    windows: list[tuple[int, ...]], parity_bytes: int, limit: int
) -> tuple[set[bytes], bool, int]:
    """Return RS-valid payloads without using the expected payload as an oracle."""

    product_size = 1
    for candidates in windows:
        product_size *= len(candidates)
    if not windows or any(not candidates for candidates in windows) or product_size > limit:
        return set(), product_size > limit, product_size
    payloads: set[bytes] = set()
    codec = None
    if parity_bytes:
        from reedsolo import RSCodec

        codec = RSCodec(parity_bytes)
    for values in itertools.product(*windows):
        codeword = bytes(values)
        if codec is None:
            payloads.add(codeword)
            continue
        try:
            decoded = codec.decode(bytearray(codeword))
        except Exception:  # library exception types vary
            continue
        payloads.add(bytes(decoded[0] if isinstance(decoded, tuple) else decoded))
    return payloads, False, product_size


def summarize(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for variant in sorted({str(row["variant"]) for row in rows}):
        selected = [row for row in rows if row["variant"] == variant]
        result[variant] = {
            "trials": len(selected),
            "all_true_symbols_covered": sum(bool(row.get("all_true_symbols_covered")) for row in selected),
            "unique_payload_successes": sum(bool(row.get("unique_payload_success")) for row in selected),
            "expected_payload_in_list": sum(bool(row.get("expected_payload_in_list")) for row in selected),
            "enumeration_limit_exceeded": sum(bool(row.get("enumeration_limit_exceeded")) for row in selected),
            "mean_max_window_candidates": mean(int(row.get("max_window_candidates", 0)) for row in selected) if selected else 0.0,
            "mean_peak_active_states": mean(int(row.get("peak_active_states", 0)) for row in selected) if selected else 0.0,
            "total_pruned_states": sum(int(row.get("pruned_states", 0)) for row in selected),
        }
    return result


def experiment_config(args: Any, source: dict[str, Any]) -> dict[str, Any]:
    base = source["experiment_config"]
    return {
        "schema": SCHEMA, "run_label": args.run_label, "source_path": str(args.input),
        "source_sha256": file_sha256(args.input), "source_signature": source["experiment_signature"],
        "model": base["model"], "reference_top_k": base["top_k"], "replay_dtype": base["replay_dtype"],
        "top_k": args.top_k, "bin_radius": args.bin_radius, "beam_width": args.beam_width,
        "enumeration_limit": args.enumeration_limit, "trial_keys": base["trial_keys"],
    }


def build_report(args: Any, source: dict[str, Any], rows: list[dict[str, Any]], phase: str) -> dict[str, Any]:
    config = experiment_config(args, source)
    return {
        "schema": SCHEMA, "run_label": args.run_label, "phase": phase,
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "experiment_config": config, "experiment_signature": config_signature(config),
        "progress": {"completed_trials": len(rows), "expected_trials": len(source["rows"])},
        "summary": summarize(rows), "rows": rows,
    }


def load_rows(path: Path, expected: dict[str, Any]) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("experiment_config") != expected or report.get("experiment_signature") != config_signature(expected):
        raise ValueError("checkpoint configuration/signature mismatch")
    rows = report.get("rows")
    if not isinstance(rows, list):
        raise ValueError("checkpoint rows must be a list")
    keys = [trial_key(row) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("checkpoint contains duplicate trials")
    return rows


def provider_config(base: dict[str, Any], top_k: int) -> HuggingFaceConfig:
    return HuggingFaceConfig(
        model_name=base["model"], device=base["device"], dtype=base["replay_dtype"],
        top_p=1.0, top_k=top_k, logit_quantum=base["logit_quantum"],
        bin_mass_bits=base["bin_mass_bits"], temperature=base["temperature"],
        candidate_order="token_id", precision_context="portable", allow_eos=False,
        adaptive_temperature=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("outputs/R036_gpt2_bin_mass_raw_bytes.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/R036D4_contract_list_decoder.json"))
    parser.add_argument("--run-label", default="R036-D4")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--bin-radius", type=int, default=1)
    parser.add_argument("--beam-width", type=int, default=4096)
    parser.add_argument("--enumeration-limit", type=int, default=1000000)
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()
    source = load_source_report(args.input)
    config = experiment_config(args, source)
    rows = [] if args.fresh else load_rows(args.output, config)
    if args.fresh:
        archive_existing_report(args.output)
    if args.fresh or not args.output.exists():
        write_report(args.output, build_report(args, source, rows, "initialized"))
    done = {trial_key(row) for row in rows}
    pending = [row for row in source["rows"] if trial_key(row) not in done]
    if pending:
        base = source["experiment_config"]
        envelope_config = provider_config(base, args.top_k)
        provider = HuggingFaceProvider(envelope_config)
        stream_config = replace(envelope_config, top_k=int(base["top_k"]))
        for source_row in pending:
            row = {key: source_row[key] for key in ("prompt_index", "payload_seed", "window_tokens", "parity_bytes", "variant")}
            try:
                prompt = str(source_row["prompt"])
                stream_context = provider.start_with_config(prompt, stream_config).context_id
                decoder = ContractListByteDecoder(ContractListConfig(
                    window_tokens=int(source_row["window_tokens"]), top_k=args.top_k,
                    bin_radius=args.bin_radius, logit_quantum=float(base["logit_quantum"]),
                    bin_mass_bits=int(base["bin_mass_bits"]), temperature=float(base["temperature"]),
                    beam_width=args.beam_width,
                ))
                decoded = decoder.decode(
                    provider.start(prompt), [int(value) for value in source_row["token_ids"]],
                    b"r036-bin-mass-audit-key-0123456789", stream_context_id=stream_context,
                )
                expected = bytes.fromhex(str(source_row["codeword_hex"]))
                candidate_windows = [window.candidates for window in decoded.windows]
                payloads, limited, product_size = recover_payload_candidates(
                    candidate_windows, int(source_row["parity_bytes"]), args.enumeration_limit
                )
                expected_payload_sha = str(source_row["payload_sha256"])
                row.update({
                    "decoder_error": decoded.error,
                    "windows": [asdict(window) for window in decoded.windows],
                    "all_true_symbols_covered": len(decoded.windows) == len(expected) and all(
                        symbol in window.candidates for symbol, window in zip(expected, decoded.windows, strict=True)
                    ),
                    "candidate_product_size": product_size,
                    "enumeration_limit_exceeded": limited,
                    "payload_candidate_count": len(payloads),
                    "expected_payload_in_list": any(hashlib.sha256(value).hexdigest() == expected_payload_sha for value in payloads),
                    "unique_payload_success": len(payloads) == 1 and hashlib.sha256(next(iter(payloads))).hexdigest() == expected_payload_sha,
                    "max_window_candidates": max((len(window.candidates) for window in decoded.windows), default=0),
                    "peak_active_states": max((window.peak_active_states for window in decoded.windows), default=0),
                    "pruned_states": sum(window.pruned_states for window in decoded.windows),
                })
            except Exception as error:  # noqa: BLE001
                row["audit_error"] = {"type": type(error).__name__, "message": str(error)}
            rows.append(row)
            write_report(args.output, build_report(args, source, rows, "partial"))
        del provider
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
    report = build_report(args, source, rows, "completed")
    write_report(args.output, report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
