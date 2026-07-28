"""R057 retrospective development analysis for the nearest-challenger screen."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.analyze_dual_barrier_certificate import (  # noqa: E402
    _reference_features,
    calibrated_threshold,
    calibration_scores,
    evaluate_row as evaluate_dual_row,
    file_sha256,
    load_source,
    split_rows,
)
from sparsamp_semantic.counterfactual_support import nearest_challenger_witness  # noqa: E402
from sparsamp_semantic.dual_barrier import (  # noqa: E402
    DualBarrierThresholds,
    build_dual_barrier_certificate,
)
from sparsamp_semantic.replay_certificate import (  # noqa: E402
    ReplayContractConfig,
    ReplayCorrection,
    ReplayManifest,
    decision_context,
    manifest_payload_sizes,
)
from sparsamp_semantic.replay_package import canonical_signature  # noqa: E402


SCHEMA = "sparsamp-r057-counterfactual-support-screen-v1"


def _screen_features(
    source: dict[str, Any],
    row: dict[str, Any],
    *,
    support_gap_bins: int,
) -> tuple[list[int], list[int], list[int | None], list[int], list[int]]:
    tokens, gaps, slacks = _reference_features(source, row)
    source_config = source["experiment_config"]
    config = ReplayContractConfig(
        contract_top_k=int(source_config["contract_top_k"]),
        logit_quantum=float(source_config["logit_quantum"]),
        mass_bits=int(source_config["mass_bits"]),
        temperature=float(source_config["temperature"]),
        public_seed=int(row["seed"]),
    )
    context = decision_context(str(source_config["model"]), str(row["prompt"]), config)
    witnesses = [
        nearest_challenger_witness(
            step["envelope_token_ids"],
            step["envelope_logit_bins"],
            tokens[index],
            step=index,
            context=context,
            config=config,
            support_gap_bins=support_gap_bins,
        )
        for index, step in enumerate(row["reference_trace"]["steps"])
    ]
    return (
        tokens,
        gaps,
        slacks,
        [index for index, witness in enumerate(witnesses) if witness.challenger_eligible],
        [index for index, witness in enumerate(witnesses) if witness.decision_sensitive],
    )


def evaluate_row(
    source: dict[str, Any],
    row: dict[str, Any],
    *,
    support_gap_bins: int,
    mass_radius: int,
    vocabulary_size: int,
) -> dict[str, Any]:
    tokens, gaps, slacks, candidate_steps, sensitive_steps = _screen_features(
        source, row, support_gap_bins=support_gap_bins
    )
    screen = build_dual_barrier_certificate(
        tokens,
        [0 if index in sensitive_steps else 1 for index in range(len(tokens))],
        slacks,
        DualBarrierThresholds(support_gap_bins=0, mass_radius=mass_radius),
    )
    actual_steps = {
        int(step["step"])
        for step in row["comparison"]["steps"]
        if bool(step["decision_flip"])
    }
    support_flips = {
        int(step["step"])
        for step in row["comparison"]["steps"]
        if bool(step["decision_flip"]) and str(step["cause"]) == "support_flip"
    }
    target = ReplayManifest(
        token_count=len(tokens),
        corrections=tuple(
            ReplayCorrection(step=step, token_id=tokens[step])
            for step in sorted(actual_steps)
        ),
    )
    screen_bytes, full_bytes = manifest_payload_sizes(screen.manifest, vocabulary_size=vocabulary_size)
    target_bytes, _ = manifest_payload_sizes(target, vocabulary_size=vocabulary_size)
    screen_steps = set(screen.ambiguous_steps)
    return {
        "prompt_index": int(row["prompt_index"]),
        "seed": int(row["seed"]),
        "token_count": len(tokens),
        "actual_flip_steps": sorted(actual_steps),
        "support_flip_steps": sorted(support_flips),
        "mass_flip_steps": sorted(actual_steps - support_flips),
        "eligible_support_steps": candidate_steps,
        "decision_sensitive_support_steps": sensitive_steps,
        "mass_steps": list(screen.mass_steps),
        "certificate_steps": list(screen.ambiguous_steps),
        "false_safe_steps": sorted(actual_steps - screen_steps),
        "exact": actual_steps <= screen_steps,
        "payload_bytes": screen_bytes,
        "target_specific_payload_bytes": target_bytes,
        "full_trace_payload_bytes": full_bytes,
    }


def summarize(rows: list[dict[str, Any]], dual_rows: list[dict[str, Any]]) -> dict[str, Any]:
    tokens = sum(int(row["token_count"]) for row in rows)
    payload = sum(int(row["payload_bytes"]) for row in rows)
    dual_payload = sum(int(row["dual_payload_bytes"]) for row in dual_rows)
    full_payload = sum(int(row["full_trace_payload_bytes"]) for row in rows)
    target_payload = sum(int(row["target_specific_payload_bytes"]) for row in rows)
    return {
        "trials": len(rows),
        "exact_trials": sum(bool(row["exact"]) for row in rows),
        "tokens": tokens,
        "actual_flips": sum(len(row["actual_flip_steps"]) for row in rows),
        "support_flips": sum(len(row["support_flip_steps"]) for row in rows),
        "mass_flips": sum(len(row["mass_flip_steps"]) for row in rows),
        "false_safe_flips": sum(len(row["false_safe_steps"]) for row in rows),
        "eligible_support_steps": sum(len(row["eligible_support_steps"]) for row in rows),
        "decision_sensitive_support_steps": sum(
            len(row["decision_sensitive_support_steps"]) for row in rows
        ),
        "mass_steps": sum(len(row["mass_steps"]) for row in rows),
        "certificate_steps": sum(len(row["certificate_steps"]) for row in rows),
        "certificate_density": sum(len(row["certificate_steps"]) for row in rows) / tokens,
        "payload_bytes": payload,
        "dual_payload_bytes": dual_payload,
        "target_specific_payload_bytes": target_payload,
        "full_trace_payload_bytes": full_payload,
        "to_full_ratio": payload / full_payload,
        "to_dual_ratio": payload / dual_payload if dual_payload else None,
        "to_target_specific_ratio": payload / target_payload if target_payload else None,
        "mean_steps_per_trial": mean(len(row["certificate_steps"]) for row in rows),
    }


def decision(summary: dict[str, Any]) -> str:
    exact = int(summary["exact_trials"])
    ratio = float(summary["to_full_ratio"])
    dual_ratio = summary["to_dual_ratio"]
    if exact == 10 and ratio < 0.5 and dual_ratio is not None and dual_ratio < 1.0:
        return "exploratory_go"
    if exact >= 9 and dual_ratio is not None and dual_ratio < 1.0:
        return "exploratory_signal"
    return "no_go"


def analyze(source_path: Path, r044_path: Path) -> dict[str, Any]:
    source = load_source(source_path)
    if file_sha256(r044_path) != source["experiment_config"]["source_sha256"]:
        raise ValueError("R044 source hash does not match the R055 material passport")
    r044 = json.loads(r044_path.read_text(encoding="utf-8"))
    calibration, heldout = split_rows(source["rows"])
    scores = calibration_scores(calibration)
    support = calibrated_threshold(scores["support"])
    mass = calibrated_threshold(scores["mass"])
    vocabulary_size = int(r044["experiment_config"]["vocabulary_size"])
    evaluated = [
        evaluate_row(
            source,
            row,
            support_gap_bins=int(support["radius"]),
            mass_radius=int(mass["radius"]),
            vocabulary_size=vocabulary_size,
        )
        for row in heldout
    ]
    dual_rows = [
        evaluate_dual_row(
            source,
            row,
            support_gap=int(support["radius"]),
            mass_radius=int(mass["radius"]),
            boundary_radius=int(calibrated_threshold(scores["boundary_only"])["radius"]),
            vocabulary_size=vocabulary_size,
        )
        for row in heldout
    ]
    summary = summarize(evaluated, dual_rows)
    result = {
        "schema": SCHEMA,
        "verification_status": "EXPLORATORY_DEVELOPMENT_ONLY",
        "source": {
            "path": str(source_path),
            "sha256": file_sha256(source_path),
            "result_signature": source["result_signature"],
            "r044_path": str(r044_path),
            "r044_sha256": file_sha256(r044_path),
        },
        "method": {
            "name": "nearest-challenger counterfactual support screen",
            "calibration_split": "even prompt indices",
            "evaluation_split": "odd prompt indices (previously observed; retrospective only)",
            "target_passes_per_certificate": 0,
            "support_model": "rank-3 replaces rank-2 under the frozen support gap",
            "confirmation_requirement": "independent R044 seeds 1 and 2 in R058",
        },
        "thresholds": {"support": support, "mass": mass},
        "heldout": {"rows": evaluated, "summary": summary},
        "decision": decision(summary),
    }
    result["result_signature"] = canonical_signature(result)
    return result


def render_markdown(result: dict[str, Any]) -> str:
    summary = result["heldout"]["summary"]
    thresholds = result["thresholds"]
    return "\n".join(
        [
            "# R057 最近挑战者反事实屏幕开发结果",
            "",
            "## 证据状态",
            "",
            "- 状态：`EXPLORATORY_DEVELOPMENT_ONLY`，不得作为确认性性能结论。",
            f"- R055 SHA-256：`{result['source']['sha256']}`。",
            f"- 结果签名：`{result['result_signature']}`。",
            "- 本分析只以参考端 top-3 bins、公开 PRF 和固定整数质量构造证书；目标端比较仅用于评估。",
            "- 奇数 prompt 已在 R056 暴露，故本页只用于机制开发；R058 必须在 R044 未使用的 seed 1/2 上确认。",
            "",
            "## 冻结阈值",
            "",
            f"- 最近挑战者支持 gap：{thresholds['support']['radius']} bins。",
            f"- 同支持质量半径：{thresholds['mass']['radius']} counts。",
            "",
            "## 回顾性开发结果",
            "",
            f"- 精确覆盖 trial：{summary['exact_trials']}/{summary['trials']}；false-safe 修正：{summary['false_safe_flips']}。",
            f"- 支持候选位置：{summary['eligible_support_steps']}；决策敏感支持位置：{summary['decision_sensitive_support_steps']}。",
            f"- 质量位置：{summary['mass_steps']}；总证书位置：{summary['certificate_steps']} / {summary['tokens']} ({summary['certificate_density']:.4%})。",
            f"- 负载/完整轨迹：{summary['to_full_ratio']:.4%}；负载/R056 双屏障：{summary['to_dual_ratio']:.4%}。",
            f"- 负载/目标特定修正：{summary['to_target_specific_ratio']:.3f} 倍。",
            f"- 开发判定：`{result['decision']}`。",
            "",
            "## 解释边界",
            "",
            "若屏幕减少位置而仍覆盖全部已观测修正，它只说明最近挑战者反事实值得在独立 seed 上验证；并不证明任意未观测候选替换、跨硬件或新 prompt 的安全性。R058 必须保持阈值、规则和验收门槛不变。",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("outputs/R055_qwen_dual_barrier_trace.json"))
    parser.add_argument("--r044", type=Path, default=Path("outputs/R044_qwen_replay_scale.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/R057_counterfactual_support_screen.json"))
    parser.add_argument("--report", type=Path, default=Path("docs/reproducibility/R057_COUNTERFACTUAL_SUPPORT_SCREEN_RESULTS.md"))
    args = parser.parse_args()
    result = analyze(args.source, args.r044)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.report.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps(result["heldout"]["summary"], indent=2, ensure_ascii=False))
    print(f"decision={result['decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
