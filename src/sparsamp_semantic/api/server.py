"""Development and local-production server entry point."""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from threading import Timer
from urllib.error import URLError
from urllib.request import urlopen

import uvicorn


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--open", action="store_true", help="open the workbench in a browser")
    args = parser.parse_args()
    url = f"http://{args.host}:{args.port}"
    open_browser = args.open or len(sys.argv) == 1
    if _workbench_is_running(url):
        print(f"SparSamp is already running at {url}")
        if open_browser:
            webbrowser.open(url)
        return 0
    if open_browser:
        Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(
        "sparsamp_semantic.api.app:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


def _workbench_is_running(url: str) -> bool:
    try:
        with urlopen(f"{url}/api/v1/system/status", timeout=1.5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        return False
    return bool(payload.get("data", {}).get("model"))


if __name__ == "__main__":
    raise SystemExit(main())
