"""Summarize fixed-block and FH-SparSamp finite-budget experiments."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


VARIANT_ORDER = ("fixed-8", "fixed-16", "fixed-32", "fh-8-16-32")


def _load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSONL at {path}:{line_number}") from error
        if row.get("status") in {"complete", "incomplete"}:
            rows.append(row)
    if not rows:
        raise ValueError(f"no experiment rows found in {path}")
    return rows


def _wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    proportion = successes / total
    denominator = 1 + z**2 / total
    center = (proportion + z**2 / (2 * total)) / denominator
    margin = (
        z / denominator * math.sqrt(proportion * (1 - proportion) / total + z**2 / (4 * total**2))
    )
    return center - margin, center + margin


def _mean_std(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    return statistics.mean(values), statistics.stdev(values) if len(values) > 1 else 0.0


def _percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _summarize_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    successes = [row for row in rows if row["status"] == "complete"]
    success_count = len(successes)
    success_tokens = [float(row["metrics"]["token_count"]) for row in successes]
    mean_tokens, std_tokens = _mean_std(success_tokens)
    completion_values = [float(row["metrics"]["completion_fraction"]) for row in rows]
    completed_bits = [float(row["metrics"]["completed_bits"]) for row in rows]
    ci_low, ci_high = _wilson_interval(success_count, len(rows))
    return {
        "n": len(rows),
        "successes": success_count,
        "success_rate": success_count / len(rows),
        "success_rate_wilson_95": [ci_low, ci_high],
        "mean_completion_fraction": statistics.mean(completion_values),
        "mean_completed_bits": statistics.mean(completed_bits),
        "successful_tokens": {
            "mean": mean_tokens,
            "std": std_tokens,
            "p95": _percentile(success_tokens, 0.95),
        },
        "decode_exact_rate_on_success": (
            sum(row["metrics"].get("decode_exact") is True for row in successes) / success_count
            if success_count
            else None
        ),
        "token_ambiguity_rate": sum(bool(row["metrics"].get("token_ambiguity")) for row in rows)
        / len(rows),
        "derived_rows": sum("derived_from_run_id" in row for row in rows),
    }


def _fmt_optional(value: float | None, digits: int = 1) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


def _markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# R005 FH-SparSamp v1 短预算消融",
        "",
        f"生成时间：{summary['generated_at']}",
        f"输入记录：{summary['row_count']}，每个预算和方法包含 6 条 prompt-seed 轨迹。",
        "",
        "## 按预算汇总",
        "",
        "| 预算 | 方法 | 成功 | 成功率 | Wilson 95% CI | 平均完成 bit | 成功样本 token 均值 +/- 标准差 | p95 | 文本歧义 | 相对最佳固定方法 |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for budget in summary["budgets"]:
        for variant in VARIANT_ORDER:
            metrics = summary["groups"][str(budget)][variant]
            ci = metrics["success_rate_wilson_95"]
            lines.append(
                f"| {budget} | {variant} | {metrics['successes']}/{metrics['n']} | "
                f"{metrics['success_rate']:.1%} | [{ci[0]:.1%}, {ci[1]:.1%}] | "
                f"{metrics['mean_completed_bits']:.1f} | "
                f"{_fmt_optional(metrics['successful_tokens']['mean'])} +/- "
                f"{_fmt_optional(metrics['successful_tokens']['std'])} | "
                f"{_fmt_optional(metrics['successful_tokens']['p95'])} | "
                f"{metrics['token_ambiguity_rate']:.1%} | "
                f"{metrics['delta_vs_best_fixed_pp']:+.1f} pp |"
            )

    lines.extend(
        [
            "",
            "## FH 与最强固定基线逐轨迹对照",
            "",
            "最强固定基线按本轮整体结果选为 `fixed-16`。`1` 表示完整恢复 128-bit payload。",
            "",
            "| Prompt | Seed | "
            + " | ".join(f"{budget}:fixed16/FH" for budget in summary["budgets"])
            + " |",
            "|---:|---:|" + "---:|" * len(summary["budgets"]),
        ]
    )
    indexed = {
        (
            row["spec"]["prompt_index"],
            row["spec"]["payload_seed"],
            row["spec"]["token_budget"],
            row["spec"]["variant"],
        ): row
        for row in rows
    }
    pairs = sorted({(row["spec"]["prompt_index"], row["spec"]["payload_seed"]) for row in rows})
    for prompt_index, seed in pairs:
        cells = []
        for budget in summary["budgets"]:
            fixed = indexed[(prompt_index, seed, budget, "fixed-16")]["status"] == "complete"
            fh = indexed[(prompt_index, seed, budget, "fh-8-16-32")]["status"] == "complete"
            cells.append(f"{int(fixed)}/{int(fh)}")
        lines.append(f"| {prompt_index} | {seed} | " + " | ".join(cells) + " |")

    lines.extend(
        [
            "",
            "## 关键发现",
            "",
            "1. **观察**：FH v1 在 96/128/160 token 的成功率均低于最佳固定 16，192 token 仅打平。",
            "   **解释**：紧预算时控制器过早选择大量 8-bit block，频繁重置稀疏区间带来的开销超过尾块粒度收益。",
            "   **含义**：当前容量比阈值控制器未通过预设的 +10 个百分点门禁，应判定为拒绝而不是继续扩大实验。",
            "2. **观察**：FH 的预算改变会从第一个 token 起改变 block schedule，完成长度对预算并不单调。",
            "   **解释**：较宽预算可能触发更大的 block，生成另一条确定性轨迹。",
            "   **含义**：FH 结果不能像固定 block 一样从小预算成功轨迹推导到大预算；runner 已加入强制测试。",
            "3. **观察**：所有成功样本的 token-ID 解码均精确，但仍出现少量公开文本重分词歧义。",
            "   **含义**：有限预算控制与 Token Ambiguity 必须继续分开报告。",
            "",
            "## 下一步实验",
            "",
            "- 放弃全程容量比切换，改测 `fixed-16 + tail fragmentation`：主体使用 16-bit block，只把最后 16-32 bit 拆成 8-bit block。",
            "- 增加 schedule `[16 x 8]`、`[16 x 7, 8 x 2]`、`[32 x 3, 16 x 2]`，隔离尾块粒度，而不是继续扫描 FH v1 阈值。",
            "- 在选出有效 schedule 后再加入语义收尾；收尾 token 不计入嵌入容量，但计入用户可见总长度和延迟。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("outputs/qwen15-fh-pilot-v2.jsonl"))
    parser.add_argument(
        "--json-output", type=Path, default=Path("outputs/qwen15-fh-pilot-v2-summary.json")
    )
    parser.add_argument(
        "--markdown-output", type=Path, default=Path("refine-logs/R005_FH_V1_RESULTS.md")
    )
    args = parser.parse_args()

    rows = _load_rows(args.results)
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(int(row["spec"]["token_budget"]), row["spec"]["variant"])].append(row)
    budgets = sorted({budget for budget, _ in grouped})
    expected = {(budget, variant) for budget in budgets for variant in VARIANT_ORDER}
    missing = expected - set(grouped)
    if missing:
        raise ValueError(f"missing budget/variant groups: {sorted(missing)}")

    groups = {
        str(budget): {
            variant: _summarize_group(grouped[(budget, variant)]) for variant in VARIANT_ORDER
        }
        for budget in budgets
    }
    for budget in budgets:
        best_fixed = max(
            groups[str(budget)][variant]["success_rate"] for variant in VARIANT_ORDER[:3]
        )
        for variant in VARIANT_ORDER:
            groups[str(budget)][variant]["delta_vs_best_fixed_pp"] = 100 * (
                groups[str(budget)][variant]["success_rate"] - best_fixed
            )

    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": str(args.results),
        "row_count": len(rows),
        "budgets": budgets,
        "groups": groups,
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
