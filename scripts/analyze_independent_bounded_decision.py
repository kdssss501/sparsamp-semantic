"""R059 frozen confirmation of R058 on independent replay seeds."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.analyze_bounded_decision_set import (  # noqa: E402
    evaluate_row as evaluate_bounded_row,
    file_sha256,
    summarize,
)
from scripts.analyze_dual_barrier_certificate import evaluate_row as evaluate_dual_row  # noqa: E402
from scripts.audit_replay_certificate import config_signature  # noqa: E402
from sparsamp_semantic.replay_package import canonical_signature  # noqa: E402


SCHEMA = "sparsamp-r059-independent-bounded-decision-v1"
TRACE_SCHEMA = "sparsamp-r055-dual-barrier-trace-v1"
R058_SCHEMA = "sparsamp-r058-bounded-decision-set-v1"


def _without_signature(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "result_signature"}


def load_r058(path: Path) -> dict[str, Any]:
    result = json.loads(path.read_text(encoding="utf-8"))
    if result.get("schema") != R058_SCHEMA or result.get("decision") != "development_go":
        raise ValueError("R059 requires the frozen R058 development GO")
    if result.get("result_signature") != canonical_signature(_without_signature(result)):
        raise ValueError("R058 result signature is invalid")
    return result


def load_trace(path: Path) -> dict[str, Any]:
    trace = json.loads(path.read_text(encoding="utf-8"))
    if trace.get("schema") != TRACE_SCHEMA or trace.get("phase") != "completed":
        raise ValueError("R059 trace must be completed")
    config = trace.get("experiment_config")
    if not isinstance(config, dict) or trace.get("experiment_signature") != config_signature(config):
        raise ValueError("R059 experiment signature is invalid")
    if str(config.get("run_label")) != "R059":
        raise ValueError("R059 trace run label is not frozen")
    rows = trace.get("rows")
    if not isinstance(rows, list) or trace.get("result_signature") != canonical_signature({"rows": rows}):
        raise ValueError("R059 trace result signature is invalid")
    expected = {(prompt, seed) for prompt in range(20) for seed in (1, 2)}
    keys = {(int(row["prompt_index"]), int(row["seed"])) for row in rows}
    if len(rows) != 40 or keys != expected:
        raise ValueError("R059 requires exactly 20 prompts at seeds 1 and 2")
    if any(not bool(row.get("comparison", {}).get("valid")) for row in rows):
        raise ValueError("every R059 comparison must pass the validity gate")
    return trace


def confirmation_decision(per_seed: dict[int, dict[str, Any]], pooled: dict[str, Any]) -> str:
    exact = {seed: int(summary["exact_trials"]) for seed, summary in per_seed.items()}
    cheaper = pooled["to_dual_ratio"] is not None and float(pooled["to_dual_ratio"]) < 1.0
    if exact == {1: 20, 2: 20} and cheaper:
        return "confirmation_strong_go"
    if all(exact.get(seed, 0) >= 18 for seed in (1, 2)) and cheaper:
        return "confirmation_pilot_go"
    return "no_go"


def analyze(trace_path: Path, r058_path: Path, r044_path: Path) -> dict[str, Any]:
    trace = load_trace(trace_path)
    r058 = load_r058(r058_path)
    if file_sha256(r044_path) != trace["experiment_config"]["source_sha256"]:
        raise ValueError("R044 hash does not match the R059 material passport")
    if file_sha256(r044_path) != r058["source"]["r044_sha256"]:
        raise ValueError("R044 hash does not match the frozen R058 source")
    r044 = json.loads(r044_path.read_text(encoding="utf-8"))
    vocabulary_size = int(r044["experiment_config"]["vocabulary_size"])
    thresholds = {
        "bin_shift": int(r058["thresholds"]["bin_shift"]["radius"]),
        "mass": int(r058["thresholds"]["mass"]["radius"]),
        "support": int(r058["thresholds"]["r056_support"]["radius"]),
    }

    bounded_rows = [
        evaluate_bounded_row(
            trace,
            row,
            bin_shift_radius=thresholds["bin_shift"],
            mass_radius=thresholds["mass"],
            vocabulary_size=vocabulary_size,
        )
        for row in trace["rows"]
    ]
    dual_rows = [
        evaluate_dual_row(
            trace,
            row,
            support_gap=thresholds["support"],
            mass_radius=thresholds["mass"],
            boundary_radius=0,
            vocabulary_size=vocabulary_size,
        )
        for row in trace["rows"]
    ]
    per_seed: dict[int, dict[str, Any]] = {}
    for seed in (1, 2):
        selected = [row for row in bounded_rows if int(row["seed"]) == seed]
        selected_dual = [row for row in dual_rows if int(row["seed"]) == seed]
        per_seed[seed] = summarize(selected, selected_dual)
    pooled = summarize(bounded_rows, dual_rows)
    result = {
        "schema": SCHEMA,
        "verification_status": "INDEPENDENT_SEED_CONFIRMATION",
        "source": {
            "trace_path": str(trace_path),
            "trace_sha256": file_sha256(trace_path),
            "trace_result_signature": trace["result_signature"],
            "r058_path": str(r058_path),
            "r058_sha256": file_sha256(r058_path),
            "r058_result_signature": r058["result_signature"],
            "r044_path": str(r044_path),
            "r044_sha256": file_sha256(r044_path),
        },
        "method": {
            "name": "independent-seed bounded decision-set confirmation",
            "seeds": [1, 2],
            "prompts_per_seed": 20,
            "threshold_source": "R058 frozen development result",
            "target_passes_per_certificate": 0,
        },
        "thresholds": thresholds,
        "per_seed": {str(seed): value for seed, value in per_seed.items()},
        "pooled": pooled,
        "decision": confirmation_decision(per_seed, pooled),
    }
    result["result_signature"] = canonical_signature(result)
    return result


def render_markdown(result: dict[str, Any]) -> str:
    pooled = result["pooled"]
    lines = [
        "# R059 有界决策集合独立 seed 确认结果",
        "",
        "## 材料护照",
        "",
        f"- R059 轨迹 SHA-256：`{result['source']['trace_sha256']}`。",
        f"- R058 结果签名：`{result['source']['r058_result_signature']}`。",
        f"- R059 结果签名：`{result['result_signature']}`。",
        "- 阈值直接读取 R058；证书构造不读取 BF16 目标标签。",
        "",
        "## 分 seed 结果",
        "",
    ]
    for seed in ("1", "2"):
        summary = result["per_seed"][seed]
        lines.append(
            f"- seed {seed}：精确 {summary['exact_trials']}/{summary['trials']}，"
            f"false-safe {summary['false_safe_flips']}，负载/完整轨迹 {summary['to_full_ratio']:.4%}，"
            f"负载/R056 {summary['to_dual_ratio']:.4%}。"
        )
    lines.extend(
        [
            "",
            "## 合并结果",
            "",
            f"- 精确覆盖：{pooled['exact_trials']}/{pooled['trials']}；false-safe：{pooled['false_safe_flips']}。",
            f"- 证书密度：{pooled['certificate_density']:.4%}。",
            f"- 负载/完整轨迹：{pooled['to_full_ratio']:.4%}；负载/R056：{pooled['to_dual_ratio']:.4%}。",
            f"- tail 告警：{pooled['tail_alarm_steps']}；平均枚举合同：{pooled['mean_contracts_per_token']:.2f} / token。",
            f"- 冻结判定：`{result['decision']}`。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, default=Path("outputs/R059_qwen_independent_trace.json"))
    parser.add_argument("--r058", type=Path, default=Path("outputs/R058_bounded_decision_set.json"))
    parser.add_argument("--r044", type=Path, default=Path("outputs/R044_qwen_replay_scale.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/R059_independent_bounded_decision.json"))
    parser.add_argument("--report", type=Path, default=Path("docs/reproducibility/R059_INDEPENDENT_BOUNDED_DECISION_RESULTS.md"))
    args = parser.parse_args()
    result = analyze(args.trace, args.r058, args.r044)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.report.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps(result["pooled"], indent=2, ensure_ascii=False))
    print(f"decision={result['decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
