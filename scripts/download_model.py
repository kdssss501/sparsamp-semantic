"""Download a Hugging Face model snapshot with conservative resumable settings."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--output", type=Path, default=Path("models/qwen2.5-1.5b-instruct"))
    parser.add_argument("--revision", default="main")
    parser.add_argument(
        "--allow-pattern",
        action="append",
        dest="allow_patterns",
        help="download only matching repository paths; repeat for multiple patterns",
    )
    parser.add_argument(
        "--ignore-pattern",
        action="append",
        dest="ignore_patterns",
        help="skip matching repository paths; repeat for multiple patterns",
    )
    args = parser.parse_args()

    os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "600")
    os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "60")
    from huggingface_hub import snapshot_download

    path = snapshot_download(
        repo_id=args.repo,
        revision=args.revision,
        local_dir=args.output,
        max_workers=1,
        allow_patterns=args.allow_patterns,
        ignore_patterns=args.ignore_patterns,
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
