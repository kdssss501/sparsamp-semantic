"""Summarize completion-pilot JSONL without double-counting derived budget rows."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _trajectory_key(row: dict[str, Any]) -> str:
    spec = {key: value for key, value in row["spec"].items() if key != "token_budget"}
    return json.dumps(spec, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load_unique_rows(path: Path) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSONL at {path}:{line_number}") from error
        if row.get("status") not in {"complete", "incomplete"}:
            continue
        key = _trajectory_key(row)
        current = unique.get(key)
        if current is None or (
            "derived_from_run_id" in current and "derived_from_run_id" not in row
        ):
            unique[key] = row
    return sorted(
        unique.values(),
        key=lambda row: (
            row["spec"]["block_size"],
            row["spec"]["prompt_index"],
            row["spec"]["payload_seed"],
        ),
    )


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _mean_std(values: list[float]) -> tuple[float, float]:
    return statistics.mean(values), statistics.stdev(values) if len(values) > 1 else 0.0


def _summarize_group(rows: list[dict[str, Any]], horizons: list[int]) -> dict[str, Any]:
    token_counts = [float(row["metrics"]["token_count"]) for row in rows]
    bits_per_token = [float(row["metrics"]["completed_bits_per_token"]) for row in rows]
    tokens_per_second = [float(row["metrics"]["tokens_per_second"]) for row in rows]
    mean_tokens, std_tokens = _mean_std(token_counts)
    mean_bpt, std_bpt = _mean_std(bits_per_token)
    mean_speed, std_speed = _mean_std(tokens_per_second)
    return {
        "n": len(rows),
        "completion_rate": sum(row["status"] == "complete" for row in rows) / len(rows),
        "decode_exact_rate": sum(row["metrics"].get("decode_exact") is True for row in rows)
        / len(rows),
        "token_ambiguity_rate": sum(bool(row["metrics"].get("token_ambiguity")) for row in rows)
        / len(rows),
        "tokens": {
            "mean": mean_tokens,
            "std": std_tokens,
            "p50": _percentile(token_counts, 0.50),
            "p95": _percentile(token_counts, 0.95),
            "min": min(token_counts),
            "max": max(token_counts),
        },
        "bits_per_token": {"mean": mean_bpt, "std": std_bpt},
        "tokens_per_second": {"mean": mean_speed, "std": std_speed},
        "horizon_success": {
            str(horizon): sum(
                row["status"] == "complete" and float(row["metrics"]["token_count"]) <= horizon
                for row in rows
            )
            / len(rows)
            for horizon in horizons
        },
    }


def _markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# R003 Qwen 固定 Block 烟雾实验",
        "",
        f"生成时间：{summary['generated_at']}",
        f"独立轨迹数：{summary['independent_trajectories']}",
        "",
        "## 汇总结果",
        "",
        "| Block | N | 完整消息成功率 | Token-ID 精确解码 | 文本重分词歧义 | Token 均值 +/- 标准差 | p95 | Bit/token 均值 +/- 标准差 | Token/s |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for block_size, metrics in summary["by_block_size"].items():
        lines.append(
            f"| {block_size} | {metrics['n']} | {metrics['completion_rate']:.1%} | "
            f"{metrics['decode_exact_rate']:.1%} | {metrics['token_ambiguity_rate']:.1%} | "
            f"{metrics['tokens']['mean']:.1f} +/- {metrics['tokens']['std']:.1f} | "
            f"{metrics['tokens']['p95']:.1f} | {metrics['bits_per_token']['mean']:.3f} +/- "
            f"{metrics['bits_per_token']['std']:.3f} | "
            f"{metrics['tokens_per_second']['mean']:.2f} |"
        )

    horizons = summary["horizons"]
    lines.extend(
        [
            "",
            "## 有限预算成功率",
            "",
            "成功率根据每条确定性轨迹实际完成 payload 所需的 token 数推导。",
            "",
            "| Block | " + " | ".join(str(value) for value in horizons) + " |",
            "|---:|" + "---:|" * len(horizons),
        ]
    )
    for block_size, metrics in summary["by_block_size"].items():
        rates = [metrics["horizon_success"][str(value)] for value in horizons]
        lines.append(f"| {block_size} | " + " | ".join(f"{rate:.1%}" for rate in rates) + " |")

    lines.extend(
        [
            "",
            "## 独立轨迹原始表",
            "",
            "| Prompt | Seed | Block | Tokens | Bits/token | Token/s | 精确解码 | 重分词歧义 |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in rows:
        metrics = row["metrics"]
        lines.append(
            f"| {row['spec']['prompt_index']} | {row['spec']['payload_seed']} | "
            f"{row['spec']['block_size']} | {metrics['token_count']} | "
            f"{metrics['completed_bits_per_token']:.3f} | {metrics['tokens_per_second']:.2f} | "
            f"{metrics.get('decode_exact')} | {metrics.get('token_ambiguity')} |"
        )

    lines.extend(
        [
            "",
            "## 结果解释",
            "",
            "- Qwen 生成的中文内容连贯且切题，所有 token-ID payload 均精确恢复。",
            "- 本实验只有 3 个 prompt x 2 个 payload seed，规模不足以支持方法性能声明。",
            "- payload 完成后立即停止会截断句子或列表，面向真实用户需要公开状态驱动的语义收尾。",
            "- 公开文本 Token Ambiguity 与 token-ID 正确性是两个问题，需要加入 ReTokSync 类基线。",
            "- 下一轮有限预算实验应使用 96/128/160 token；对本轮 128-bit payload，512/1024 预算没有约束作用。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("outputs/qwen15-completion.jsonl"))
    parser.add_argument(
        "--json-output", type=Path, default=Path("outputs/qwen15-completion-summary.json")
    )
    parser.add_argument(
        "--markdown-output", type=Path, default=Path("refine-logs/R003_PILOT_RESULTS.md")
    )
    parser.add_argument("--horizons", default="96,128,160,192,256,512")
    args = parser.parse_args()

    horizons = [int(value) for value in args.horizons.split(",")]
    if any(value < 1 for value in horizons):
        raise ValueError("horizons must be positive integers")
    rows = _load_unique_rows(args.results)
    if not rows:
        raise ValueError(f"no completed experiment rows found in {args.results}")

    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["spec"]["block_size"])].append(row)
    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": str(args.results),
        "independent_trajectories": len(rows),
        "horizons": horizons,
        "by_block_size": {
            str(block_size): _summarize_group(group_rows, horizons)
            for block_size, group_rows in sorted(grouped.items())
        },
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(_markdown(summary, rows), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
