"""Command-line interface for reproducible local and mock experiments."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .core import CodecConfig, EncodeResult, SparSampCodec
from .payload import PayloadCodec
from .providers.huggingface import HuggingFaceConfig, HuggingFaceProvider
from .providers.mock import MockProvider


def _secret_key() -> bytes:
    value = os.environ.get("SPARSAMP_SECRET_KEY", "")
    if len(value.encode("utf-8")) < 16:
        raise RuntimeError("set SPARSAMP_SECRET_KEY to a random value containing at least 16 bytes")
    return value.encode("utf-8")


def _result_dict(
    result: EncodeResult,
    prompt: str,
    codec_config: CodecConfig,
    payload_codec: PayloadCodec,
    provider: dict[str, Any],
    token_ambiguity: bool | None,
) -> dict[str, Any]:
    return {
        "schema": "sparsamp-semantic-result-v1",
        "prompt": prompt,
        "provider": provider,
        "codec": asdict(codec_config),
        "payload": {"repetitions": payload_codec.repetitions},
        "cover_text": result.text,
        "token_ids": list(result.token_ids),
        "token_ambiguity": token_ambiguity,
        "metrics": {
            "embedded_bits": result.embedded_bits,
            "padded_bits": result.padded_bits,
            "token_count": len(result.token_ids),
            "elapsed_seconds": result.elapsed_seconds,
            "bits_per_token": result.bits_per_token,
            "bits_per_second": result.bits_per_second,
            "entropy_utilization": result.entropy_utilization,
            "truncation_kl_nats": result.truncation_kl_nats,
        },
        "records": [asdict(record) for record in result.records],
    }


def _write_result(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _common_codec(args: argparse.Namespace) -> tuple[SparSampCodec, PayloadCodec]:
    codec = SparSampCodec(
        CodecConfig(
            block_size=args.block_size,
            max_tokens=args.max_tokens,
            min_source_mass=args.min_source_mass,
            probability_quantum=args.probability_quantum,
        )
    )
    return codec, PayloadCodec(repetitions=args.repetitions)


def _message(args: argparse.Namespace) -> str:
    if args.message_file:
        return Path(args.message_file).read_text(encoding="utf-8")
    if args.message is None:
        raise RuntimeError("provide --message or --message-file")
    return args.message


def mock_demo(args: argparse.Namespace) -> int:
    key = _secret_key()
    codec, payload_codec = _common_codec(args)
    prompt = args.prompt or "Explain reproducible research in one concise paragraph."
    payload_bits = payload_codec.seal(_message(args), key)
    provider = MockProvider()
    encoded = codec.encode(provider.start(prompt), payload_bits, key)
    decoded = codec.decode(provider.start(prompt), list(encoded.token_ids), key)
    plaintext = payload_codec.open(decoded.bits, key)
    print(encoded.text)
    print(
        json.dumps(
            {
                "decoded": plaintext,
                "metrics": _result_dict(
                    encoded,
                    prompt,
                    codec.config,
                    payload_codec,
                    {"type": "mock", "model_name": "mock-semantic-v1"},
                    False,
                )["metrics"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def encode_local(args: argparse.Namespace) -> int:
    key = _secret_key()
    codec, payload_codec = _common_codec(args)
    payload_bits = payload_codec.seal(_message(args), key)
    config = HuggingFaceConfig(
        model_name=args.model,
        revision=args.revision,
        top_p=args.top_p,
        top_k=args.top_k,
        temperature=args.temperature,
        device=args.device,
        dtype=args.dtype,
        load_in_4bit=args.load_in_4bit,
        seed=args.seed,
    )
    provider = HuggingFaceProvider(config)
    session = provider.start(args.prompt)
    encoded = codec.encode(session, payload_bits, key)
    try:
        retokenized = session.retokenize(encoded.text)
        token_ambiguity = retokenized != encoded.token_ids
    except NotImplementedError:
        token_ambiguity = None
    data = _result_dict(
        encoded,
        args.prompt,
        codec.config,
        payload_codec,
        {"type": "huggingface", **asdict(config)},
        token_ambiguity,
    )
    _write_result(Path(args.output), data)
    print(encoded.text)
    print(json.dumps(data["metrics"] | {"token_ambiguity": token_ambiguity}, indent=2))
    return 0


def decode_local(args: argparse.Namespace) -> int:
    key = _secret_key()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    provider_data = data["provider"]
    config = HuggingFaceConfig(
        **{key_: value for key_, value in provider_data.items() if key_ != "type"}
    )
    codec = SparSampCodec(CodecConfig(**data["codec"]))
    payload_codec = PayloadCodec(**data["payload"])
    provider = HuggingFaceProvider(config)
    session = provider.start(data["prompt"])
    token_ids = tuple(data["token_ids"])
    if args.from_text:
        token_ids = session.retokenize(data["cover_text"])
        if token_ids != tuple(data["token_ids"]):
            print("warning: Token Ambiguity detected during text re-tokenization", file=sys.stderr)
    decoded = codec.decode(session, list(token_ids), key)
    print(payload_codec.open(decoded.bits, key))
    return 0


def native_local(args: argparse.Namespace) -> int:
    config = HuggingFaceConfig(
        model_name=args.model,
        revision=args.revision,
        top_p=args.top_p,
        top_k=args.top_k,
        temperature=args.temperature,
        device=args.device,
        dtype=args.dtype,
        load_in_4bit=args.load_in_4bit,
        seed=args.seed,
    )
    session = HuggingFaceProvider(config).start(args.prompt)
    rng = random.Random(args.seed)
    for _ in range(args.tokens):
        snapshot = session.next_distribution()
        target = rng.random()
        cumulative = 0.0
        selected = snapshot.candidates[-1]
        for candidate in snapshot.candidates:
            cumulative += candidate.probability
            if target < cumulative:
                selected = candidate
                break
        session.append(selected.token_id)
    print(session.render())
    return 0


def _add_codec_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--block-size", type=int, default=32)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--min-source-mass", type=float, default=0.0)
    parser.add_argument("--probability-quantum", default="1e-15")
    parser.add_argument("--repetitions", type=int, default=1)


def _add_model_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--revision")
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--dtype", default="float16")
    parser.add_argument("--load-in-4bit", action="store_true")
    parser.add_argument("--seed", type=int, default=42)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    mock = subparsers.add_parser("mock-demo", help="run a dependency-light round trip")
    mock.add_argument("--prompt")
    mock.add_argument("--message")
    mock.add_argument("--message-file")
    _add_codec_arguments(mock)
    mock.set_defaults(handler=mock_demo)

    encode = subparsers.add_parser("encode-local", help="encode with a local instruction model")
    encode.add_argument("--prompt", required=True)
    encode.add_argument("--message")
    encode.add_argument("--message-file")
    encode.add_argument("--output", default="outputs/local-run.json")
    _add_codec_arguments(encode)
    _add_model_arguments(encode)
    encode.set_defaults(handler=encode_local)

    decode = subparsers.add_parser("decode-local", help="decode a saved local-model result")
    decode.add_argument("--input", required=True)
    decode.add_argument("--from-text", action="store_true")
    decode.set_defaults(handler=decode_local)

    native = subparsers.add_parser("native-local", help="generate a non-stego semantic baseline")
    native.add_argument("--prompt", required=True)
    native.add_argument("--tokens", type=int, default=128)
    _add_model_arguments(native)
    native.set_defaults(handler=native_local)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return int(args.handler(args))
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
