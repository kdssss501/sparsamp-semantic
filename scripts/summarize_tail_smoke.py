"""Compare tail-fragmentation schedules with fixed-16 on matched payloads."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


VARIANTS = ("fixed-16", "tail-16x7-8x2", "tail-16x6-8x4", "mixed-32x3-16x2")


def _read(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    successes = [row for row in rows if row["status"] == "complete"]
    success_tokens = [float(row["metrics"]["token_count"]) for row in successes]
    return {
        "n": len(rows),
        "successes": len(successes),
        "success_rate": len(successes) / len(rows),
        "mean_completed_bits": statistics.mean(
            float(row["metrics"]["completed_bits"]) for row in rows
        ),
        "successful_tokens_mean": statistics.mean(success_tokens) if success_tokens else None,
        "decode_exact": all(row["metrics"].get("decode_exact") is True for row in successes),
    }


def _fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:.1f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=Path("outputs/qwen15-fh-pilot-v2.jsonl"))
    parser.add_argument(
        "--tail-results", type=Path, default=Path("outputs/qwen15-tail-schedule-smoke.jsonl")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("refine-logs/R005_TAIL_SCHEDULE_SMOKE.md")
    )
    args = parser.parse_args()

    baseline = [
        row
        for row in _read(args.baseline)
        if row["spec"]["prompt_index"] == 0 and row["spec"]["variant"] == "fixed-16"
    ]
    tail = _read(args.tail_results)
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in [*baseline, *tail]:
        grouped[(int(row["spec"]["token_budget"]), row["spec"]["variant"])].append(row)

    budgets = sorted({budget for budget, _ in grouped})
    summary = {
        str(budget): {variant: _summarize(grouped[(budget, variant)]) for variant in VARIANTS}
        for budget in budgets
    }
    lines = [
        "# R005 Tail Fragmentation 烟雾实验",
        "",
        f"生成时间：{datetime.now(UTC).isoformat()}",
        "",
        "同一实验 ID、prompt 和 payload seed 下比较固定 16 与三个预定 schedule。每组 N=2。",
        "",
        "| 预算 | 方法 | 成功 | 成功率 | 平均完成 bit | 成功样本 token 均值 |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for budget in budgets:
        for variant in VARIANTS:
            metrics = summary[str(budget)][variant]
            lines.append(
                f"| {budget} | {variant} | {metrics['successes']}/{metrics['n']} | "
                f"{metrics['success_rate']:.1%} | {metrics['mean_completed_bits']:.1f} | "
                f"{_fmt(metrics['successful_tokens_mean'])} |"
            )
    lines.extend(
        [
            "",
            "## 决策",
            "",
            "- `tail-16x7-8x2` 在 96 token 与 fixed-16 同为 1/2 成功，成功样本多用 1 token。",
            "- 在 128 token，两者均为 2/2 成功，但 tail schedule 的两个样本分别比 fixed-16 多用 5 和 1 token。",
            "- 更早拆分和 32-bit 混合 schedule 在 128 token 均损失一个完整消息成功样本。",
            "- 因此 tail fragmentation 未显示扩大实验的信号，停止 block schedule 路线。",
            "- 下一优先级转为语义收尾和有限精度重放，两者对应已经观测到的实际失败，而不是继续改 block。",
            "",
        ]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
