"""Run the unmodified Zenodo SparSamp Basic Test with local model paths."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import sys
from contextlib import redirect_stdout
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _load_official_main(basic_dir: Path) -> Any:
    sys.path.insert(0, str(basic_dir))
    spec = importlib.util.spec_from_file_location("official_sparsamp_main", basic_dir / "main.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load official Basic Test main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=Path(".artifacts/sparsamp-official/extracted/Artifact new"),
    )
    parser.add_argument("--model", type=Path, default=Path("models/gpt2"))
    parser.add_argument("--output", type=Path, default=Path("outputs/official/basic.json"))
    parser.add_argument("--log", type=Path, default=Path("outputs/logs/official-basic.log"))
    parser.add_argument("--message-length", type=int, default=12_800)
    parser.add_argument("--block-size", type=int, default=64)
    parser.add_argument("--min-tokens", type=int, default=100)
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--seed", type=int, default=32)
    args = parser.parse_args()

    import torch
    import transformers

    basic_dir = (args.artifact_root / "Basic Test").resolve()
    model_path = args.model.resolve()
    output_path = args.output.resolve()
    log_path = args.log.resolve()
    message_path = basic_dir / "message_bits.txt"
    for required in (basic_dir / "main.py", basic_dir / "sparsamp.py", message_path):
        if not required.is_file():
            raise FileNotFoundError(required)
    if not (model_path / "model.safetensors").is_file():
        raise FileNotFoundError(model_path / "model.safetensors")

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    official = _load_official_main(basic_dir)
    config = official.SparsampConfig(
        message_file=str(message_path),
        message_length=args.message_length,
        block_size=args.block_size,
        context="Give me a short introduction to large language model.",
        model_path=str(model_path),
        random_seed=args.seed,
        token_num_need_generated=args.min_tokens,
        top_p=args.top_p,
    )
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    previous_cwd = Path.cwd()
    try:
        os.chdir(basic_dir)
        with log_path.open("w", encoding="utf-8") as stream, redirect_stdout(stream):
            print(f"Using device: {device}")
            results = official.test_sparsamp(config, device)
    finally:
        os.chdir(previous_cwd)

    payload = {
        "schema": "sparsamp-official-basic-v1",
        "timestamp": datetime.now(UTC).isoformat(),
        "artifact": {
            "zenodo_record": "15025436",
            "md5": "1cf080219f9f24d0c608151cee26e99e",
        },
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "device": str(device),
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        },
        "config": {
            "message_length": args.message_length,
            "block_size": args.block_size,
            "min_tokens": args.min_tokens,
            "top_p": args.top_p,
            "seed": args.seed,
            "model": str(model_path),
        },
        "results": results,
        "log": str(log_path),
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
