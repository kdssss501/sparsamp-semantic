"""Run block-size and top-p ablations while loading model weights only once."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, replace
from pathlib import Path
from time import time

from sparsamp_semantic.core import CodecConfig, SparSampCodec
from sparsamp_semantic.payload import PayloadCodec
from sparsamp_semantic.providers.huggingface import HuggingFaceConfig, HuggingFaceProvider


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/semantic_grid.example.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/semantic-grid.jsonl"))
    args = parser.parse_args()

    secret = os.environ.get("SPARSAMP_SECRET_KEY", "").encode("utf-8")
    if len(secret) < 16:
        raise RuntimeError("SPARSAMP_SECRET_KEY must contain at least 16 bytes")
    settings = json.loads(args.config.read_text(encoding="utf-8"))
    payload_bits = PayloadCodec().seal(settings["message"], secret)
    base_config = HuggingFaceConfig(
        model_name=settings["model"],
        revision=settings.get("revision"),
        top_p=float(settings["top_ps"][0]),
        top_k=settings.get("top_k"),
        temperature=float(settings.get("temperature", 1.0)),
        device=settings.get("device", "auto"),
        dtype=settings.get("dtype", "float16"),
        load_in_4bit=bool(settings.get("load_in_4bit", False)),
    )
    provider = HuggingFaceProvider(base_config)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("a", encoding="utf-8") as stream:
        for prompt_index, prompt in enumerate(settings["prompts"]):
            for top_p in settings["top_ps"]:
                session_config = replace(base_config, top_p=float(top_p))
                for block_size in settings["block_sizes"]:
                    codec = SparSampCodec(
                        CodecConfig(
                            block_size=int(block_size),
                            max_tokens=int(settings.get("max_tokens", 2048)),
                            probability_quantum=settings.get("probability_quantum", "1e-15"),
                        )
                    )
                    session = provider.start_with_config(prompt, session_config)
                    encoded = codec.encode(session, payload_bits, secret)
                    retokenized = session.retokenize(encoded.text)
                    row = {
                        "timestamp": time(),
                        "prompt_index": prompt_index,
                        "prompt": prompt,
                        "model": asdict(session_config),
                        "codec": asdict(codec.config),
                        "cover_text": encoded.text,
                        "token_ambiguity": retokenized != encoded.token_ids,
                        "metrics": {
                            "embedded_bits": encoded.embedded_bits,
                            "token_count": len(encoded.token_ids),
                            "bits_per_token": encoded.bits_per_token,
                            "bits_per_second": encoded.bits_per_second,
                            "entropy_utilization": encoded.entropy_utilization,
                            "truncation_kl_nats": encoded.truncation_kl_nats,
                        },
                    }
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                    stream.flush()
                    print(
                        f"prompt={prompt_index} top_p={top_p} block={block_size} "
                        f"bpt={encoded.bits_per_token:.3f} ambiguity={row['token_ambiguity']}"
                    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
