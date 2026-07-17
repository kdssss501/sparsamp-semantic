"""Emit and verify the exact rational counterexample used in the RRC theory appendix."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from sparsamp_semantic.rrc_theory import (  # noqa: E402
    paper_failure_region,
    paper_stop_counterexample,
    stopped_process_counterexample,
)


def _render(value: Any) -> Any:
    if isinstance(value, Fraction):
        return {"fraction": f"{value.numerator}/{value.denominator}", "decimal": float(value)}
    if isinstance(value, tuple):
        return [_render(item) for item in value]
    if isinstance(value, dict):
        return {key: _render(item) for key, item in value.items()}
    return value


def main() -> int:
    example = paper_stop_counterexample()
    region = paper_failure_region()
    stopping_leak = stopped_process_counterexample()
    assert Fraction(-1, 2) < example.paper_midpoint_error <= Fraction(1, 2)
    assert example.decoded_message != example.message
    print(
        json.dumps(
            {
                "counterexample": _render(asdict(example)),
                "positive_measure_region": _render(asdict(region)),
                "stopping_leak_counterexample": _render(asdict(stopping_leak)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
