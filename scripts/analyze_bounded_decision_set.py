"""R058 development analysis of bounded public contract decision sets."""

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
from sparsamp_semantic.bounded_decision_set import bounded_decision_witness  # noqa: E402
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


SCHEMA = "sparsamp-r058-bounded-decision-set-v1"
ALPHA = 0.10


def shift_scores(rows: list[dict[str, Any]]) -> dict[int, int]:
    return {
        int(row["prompt_index"]): max(
            int(step["common_envelope_max_bin_shift"])
            for step in row["comparison"]["steps"]
        )
        for row in rows
    }


def _bounded_features(
    source: dict[str, Any],
    row: dict[str, Any],
    *,
    bin_shift_radius: int,
) -> tuple[list[int], list[int | None], list[Any]]:
    tokens, _, slacks = _reference_features(source, row)
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
        bounded_decision_witness(
            step["envelope_token_ids"],
            step["envelope_logit_bins"],
            tokens[index],
            step=index,
            context=context,
            config=config,
            bin_shift_radius=bin_shift_radius,
        )
        for index, step in enumerate(row["reference_trace"]["steps"])
    ]
    return tokens, slacks, witnesses


def evaluate_row(
    source: dict[str, Any],
    row: dict[str, Any],
    *,
    bin_shift_radius: int,
    mass_radius: int,
    vocabulary_size: int,
) -> dict[str, Any]:
    tokens, slacks, witnesses = _bounded_features(
        source, row, bin_shift_radius=bin_shift_radius
    )
    bounded_steps = [
        index for index, witness in enumerate(witnesses) if not witness.decision_invariant
    ]
    certificate = build_dual_barrier_certificate(
        tokens,
        [0 if index in bounded_steps else 1 for index in range(len(tokens))],
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
    payload, full_payload = manifest_payload_sizes(
        certificate.manifest, vocabulary_size=vocabulary_size
    )
    target_payload, _ = manifest_payload_sizes(target, vocabulary_size=vocabulary_size)
    certificate_steps = set(certificate.ambiguous_steps)
    return {
        "prompt_index": int(row["prompt_index"]),
        "seed": int(row["seed"]),
        "token_count": len(tokens),
        "actual_flip_steps": sorted(actual_steps),
        "support_flip_steps": sorted(support_flips),
        "mass_flip_steps": sorted(actual_steps - support_flips),
        "bounded_steps": bounded_steps,
        "mass_steps": list(certificate.mass_steps),
        "tail_alarm_steps": [
            index for index, witness in enumerate(witnesses) if witness.unknown_tail_possible
        ],
        "feasible_pair_count": sum(witness.feasible_pair_count for witness in witnesses),
        "feasible_contract_count": sum(
            witness.feasible_contract_count for witness in witnesses
        ),
        "certificate_steps": list(certificate.ambiguous_steps),
        "false_safe_steps": sorted(actual_steps - certificate_steps),
        "exact": actual_steps <= certificate_steps,
        "payload_bytes": payload,
        "target_specific_payload_bytes": target_payload,
        "full_trace_payload_bytes": full_payload,
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
        "false_safe_flips": sum(len(row["false_safe_steps"]) for row in rows),
        "bounded_steps": sum(len(row["bounded_steps"]) for row in rows),
        "mass_steps": sum(len(row["mass_steps"]) for row in rows),
        "tail_alarm_steps": sum(len(row["tail_alarm_steps"]) for row in rows),
        "certificate_steps": sum(len(row["certificate_steps"]) for row in rows),
        "certificate_density": sum(len(row["certificate_steps"]) for row in rows) / tokens,
        "feasible_pair_count": sum(int(row["feasible_pair_count"]) for row in rows),
        "feasible_contract_count": sum(int(row["feasible_contract_count"]) for row in rows),
        "mean_contracts_per_token": sum(
            int(row["feasible_contract_count"]) for row in rows
        ) / tokens,
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
    if (
        int(summary["exact_trials"]) == 10
        and float(summary["to_full_ratio"]) < 0.630174
        and summary["to_dual_ratio"] is not None
        and float(summary["to_dual_ratio"]) < 1.0
    ):
        return "development_go"
    return "no_go"


def analyze(source_path: Path, r044_path: Path) -> dict[str, Any]:
    source = load_source(source_path)
    if file_sha256(r044_path) != source["experiment_config"]["source_sha256"]:
        raise ValueError("R044 source hash does not match the R055 material passport")
    r044 = json.loads(r044_path.read_text(encoding="utf-8"))
    calibration, heldout = split_rows(source["rows"])
    barrier_scores = calibration_scores(calibration)
    shift = calibrated_threshold(shift_scores(calibration))
    support = calibrated_threshold(barrier_scores["support"])
    mass = calibrated_threshold(barrier_scores["mass"])
    boundary = calibrated_threshold(barrier_scores["boundary_only"])
    vocabulary_size = int(r044["experiment_config"]["vocabulary_size"])
    evaluated = [
        evaluate_row(
            source,
            row,
            bin_shift_radius=int(shift["radius"]),
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
            boundary_radius=int(boundary["radius"]),
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
            "name": "bounded public contract decision set",
            "calibration_split": "even prompt indices",
            "evaluation_split": "odd prompt indices (previously observed; retrospective only)",
            "target_passes_per_certificate": 0,
            "confirmation_requirement": "independent R044 seeds 1 and 2 in R059",
            "alpha": ALPHA,
        },
        "calibration_scores": {"bin_shift": shift_scores(calibration)},
        "thresholds": {"bin_shift": shift, "mass": mass, "r056_support": support},
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
            "# R058 有界决策集合开发结果",
            "",
            "## 证据状态",
            "",
            "- 状态：`EXPLORATORY_DEVELOPMENT_ONLY`。奇数 prompt 已被早期阶段查看，不是确认集。",
            f"- R055 SHA-256：`{result['source']['sha256']}`。",
            f"- 结果签名：`{result['result_signature']}`。",
            "- 证书构造只读参考端 envelope、公开上下文和 calibration 阈值；目标端只用于冻结后的评估。",
            "",
            "## 冻结参数",
            "",
            f"- bin 扰动半径：{thresholds['bin_shift']['radius']}。",
            f"- 同支持质量半径：{thresholds['mass']['radius']} counts。",
            f"- R056 支持 gap 对照：{thresholds['r056_support']['radius']} bins。",
            "",
            "## 开发结果",
            "",
            f"- 精确覆盖 trial：{summary['exact_trials']}/{summary['trials']}；false-safe 修正：{summary['false_safe_flips']}。",
            f"- 证书位置：{summary['certificate_steps']} / {summary['tokens']} ({summary['certificate_density']:.4%})。",
            f"- 负载/完整轨迹：{summary['to_full_ratio']:.4%}；负载/R056：{summary['to_dual_ratio']:.4%}。",
            f"- tail 告警位置：{summary['tail_alarm_steps']}。",
            f"- 枚举合同：{summary['feasible_contract_count']}，平均 {summary['mean_contracts_per_token']:.2f} / token。",
            f"- 开发判定：`{result['decision']}`。",
            "",
            "## 下一门禁",
            "",
            "只有 `development_go` 才运行 R059。R059 使用 R044 seed 1/2 重新采集独立 FP16/BF16 轨迹，规则、半径与代码哈希保持不变；确认结果不得回流修改本阶段阈值。",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("outputs/R055_qwen_dual_barrier_trace.json"))
    parser.add_argument("--r044", type=Path, default=Path("outputs/R044_qwen_replay_scale.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/R058_bounded_decision_set.json"))
    parser.add_argument("--report", type=Path, default=Path("docs/reproducibility/R058_BOUNDED_DECISION_SET_RESULTS.md"))
    args = parser.parse_args()
    result = analyze(args.source, args.r044)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.report.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps(result["heldout"]["summary"], indent=2, ensure_ascii=False))
    print(f"decision={result['decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
