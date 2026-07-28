"""R056 frozen even/odd evaluation of the stratified dual-barrier certificate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from statistics import mean
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.audit_replay_certificate import config_signature  # noqa: E402
from sparsamp_semantic.conformal_replay import (  # noqa: E402
    contract_boundary_margin,
    split_conformal_upper_radius,
)
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


SCHEMA = "sparsamp-r056-dual-barrier-analysis-v1"
SOURCE_SCHEMA = "sparsamp-r055-dual-barrier-trace-v1"
ALPHA = 0.10


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_source(path: Path) -> dict[str, Any]:
    source = json.loads(path.read_text(encoding="utf-8"))
    if source.get("schema") != SOURCE_SCHEMA or source.get("phase") != "completed":
        raise ValueError("source must be a completed R055 trace")
    rows = source.get("rows")
    if not isinstance(rows, list) or len(rows) != 20:
        raise ValueError("R056 requires the frozen 20-trial R055 pilot")
    if source.get("result_signature") != canonical_signature({"rows": rows}):
        raise ValueError("R055 result signature is invalid")
    config = source.get("experiment_config")
    if (
        not isinstance(config, dict)
        or source.get("experiment_signature") != config_signature(config)
    ):
        raise ValueError("R055 experiment signature is invalid")
    if any(not bool(row.get("comparison", {}).get("valid")) for row in rows):
        raise ValueError("every R055 trial must pass the validity gate")
    keys = {(int(row["prompt_index"]), int(row["seed"])) for row in rows}
    if keys != {(prompt, 0) for prompt in range(20)}:
        raise ValueError("R055 must contain prompt indices 0 through 19 at seed 0")
    return source


def split_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    calibration = [row for row in rows if int(row["prompt_index"]) % 2 == 0]
    heldout = [row for row in rows if int(row["prompt_index"]) % 2 == 1]
    if len(calibration) != 10 or len(heldout) != 10:
        raise ValueError("R056 requires ten calibration and ten held-out prompts")
    return calibration, heldout


def _prompt_score(
    row: dict[str, Any],
    *,
    cause: str | None,
    feature: Callable[[dict[str, Any]], int],
) -> int:
    values = [
        feature(step)
        for step in row["comparison"]["steps"]
        if bool(step["decision_flip"]) and (cause is None or str(step["cause"]) == cause)
    ]
    return max(values, default=0)


def calibration_scores(rows: list[dict[str, Any]]) -> dict[str, dict[int, int]]:
    return {
        "support": {
            int(row["prompt_index"]): _prompt_score(
                row,
                cause="support_flip",
                feature=lambda step: int(step["reference_rank2_rank3_gap_bins"]),
            )
            for row in rows
        },
        "mass": {
            int(row["prompt_index"]): _prompt_score(
                row,
                cause="mass_flip",
                feature=lambda step: int(step["reference_boundary_slack"]) + 1,
            )
            for row in rows
        },
        "boundary_only": {
            int(row["prompt_index"]): _prompt_score(
                row,
                cause=None,
                feature=lambda step: int(step["reference_boundary_slack"]) + 1,
            )
            for row in rows
        },
    }


def calibrated_threshold(values: dict[int, int]) -> dict[str, int | float]:
    conformal = split_conformal_upper_radius(list(values.values()), alpha=ALPHA)
    if conformal.radius is None:
        raise ValueError("frozen alpha has no finite calibration threshold")
    return {
        "alpha": ALPHA,
        "order_rank": conformal.order_rank,
        "radius": conformal.radius,
    }


def _reference_features(
    source: dict[str, Any], row: dict[str, Any]
) -> tuple[list[int], list[int], list[int | None]]:
    reference_steps = row["reference_trace"]["steps"]
    if not bool(row["reference_trace"]["trace_completed"]):
        raise ValueError("reference trace must be complete")
    source_config = source["experiment_config"]
    config = ReplayContractConfig(
        contract_top_k=int(source_config["contract_top_k"]),
        logit_quantum=float(source_config["logit_quantum"]),
        mass_bits=int(source_config["mass_bits"]),
        temperature=float(source_config["temperature"]),
        public_seed=int(row["seed"]),
    )
    context = decision_context(str(source_config["model"]), str(row["prompt"]), config)
    slacks = [
        contract_boundary_margin(
            step["contract_counts"],
            step=int(step["step"]),
            context=context,
            public_seed=config.public_seed,
        ).minimum_slack
        for step in reference_steps
    ]
    return (
        [int(step["decision_token_id"]) for step in reference_steps],
        [int(step["rank2_rank3_gap_bins"]) for step in reference_steps],
        slacks,
    )


def evaluate_row(
    source: dict[str, Any],
    row: dict[str, Any],
    *,
    support_gap: int,
    mass_radius: int,
    boundary_radius: int,
    vocabulary_size: int,
) -> dict[str, Any]:
    tokens, gaps, slacks = _reference_features(source, row)
    dual = build_dual_barrier_certificate(
        tokens,
        gaps,
        slacks,
        DualBarrierThresholds(support_gap, mass_radius),
    )
    # Disable the support barrier in the boundary-only baseline. Gaps are non-negative,
    # so a sentinel sequence one unit above the threshold preserves length safely.
    boundary = build_dual_barrier_certificate(
        tokens,
        [1 for _ in gaps],
        slacks,
        DualBarrierThresholds(0, boundary_radius),
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
    mass_flips = actual_steps - support_flips
    target_manifest = ReplayManifest(
        token_count=len(tokens),
        corrections=tuple(
            ReplayCorrection(step=step, token_id=tokens[step])
            for step in sorted(actual_steps)
        ),
    )
    dual_bytes, full_bytes = manifest_payload_sizes(
        dual.manifest, vocabulary_size=vocabulary_size
    )
    boundary_bytes, _ = manifest_payload_sizes(
        boundary.manifest, vocabulary_size=vocabulary_size
    )
    target_bytes, _ = manifest_payload_sizes(
        target_manifest, vocabulary_size=vocabulary_size
    )
    dual_steps = set(dual.ambiguous_steps)
    boundary_steps = set(boundary.ambiguous_steps)
    return {
        "prompt_index": int(row["prompt_index"]),
        "seed": int(row["seed"]),
        "token_count": len(tokens),
        "actual_flip_steps": sorted(actual_steps),
        "support_flip_steps": sorted(support_flips),
        "mass_flip_steps": sorted(mass_flips),
        "dual_certificate_steps": list(dual.ambiguous_steps),
        "dual_support_steps": list(dual.support_steps),
        "dual_mass_steps": list(dual.mass_steps),
        "dual_false_safe_steps": sorted(actual_steps - dual_steps),
        "boundary_false_safe_steps": sorted(actual_steps - boundary_steps),
        "dual_exact": actual_steps <= dual_steps,
        "boundary_exact": actual_steps <= boundary_steps,
        "dual_payload_bytes": dual_bytes,
        "boundary_payload_bytes": boundary_bytes,
        "target_specific_payload_bytes": target_bytes,
        "full_trace_payload_bytes": full_bytes,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tokens = sum(int(row["token_count"]) for row in rows)
    dual_steps = sum(len(row["dual_certificate_steps"]) for row in rows)
    support_steps = sum(len(row["dual_support_steps"]) for row in rows)
    mass_steps = sum(len(row["dual_mass_steps"]) for row in rows)
    actual = sum(len(row["actual_flip_steps"]) for row in rows)
    dual_bytes = sum(int(row["dual_payload_bytes"]) for row in rows)
    boundary_bytes = sum(int(row["boundary_payload_bytes"]) for row in rows)
    target_bytes = sum(int(row["target_specific_payload_bytes"]) for row in rows)
    full_bytes = sum(int(row["full_trace_payload_bytes"]) for row in rows)
    return {
        "trials": len(rows),
        "exact_trials": sum(bool(row["dual_exact"]) for row in rows),
        "boundary_exact_trials": sum(bool(row["boundary_exact"]) for row in rows),
        "tokens": tokens,
        "actual_flips": actual,
        "support_flips": sum(len(row["support_flip_steps"]) for row in rows),
        "mass_flips": sum(len(row["mass_flip_steps"]) for row in rows),
        "dual_false_safe_flips": sum(len(row["dual_false_safe_steps"]) for row in rows),
        "boundary_false_safe_flips": sum(
            len(row["boundary_false_safe_steps"]) for row in rows
        ),
        "dual_certificate_steps": dual_steps,
        "support_barrier_steps": support_steps,
        "mass_barrier_steps": mass_steps,
        "dual_certificate_density": dual_steps / tokens,
        "dual_payload_bytes": dual_bytes,
        "boundary_payload_bytes": boundary_bytes,
        "target_specific_payload_bytes": target_bytes,
        "full_trace_payload_bytes": full_bytes,
        "dual_to_full_ratio": dual_bytes / full_bytes,
        "boundary_to_full_ratio": boundary_bytes / full_bytes,
        "dual_to_boundary_ratio": dual_bytes / boundary_bytes if boundary_bytes else None,
        "dual_to_target_specific_ratio": dual_bytes / target_bytes if target_bytes else None,
        "mean_dual_steps_per_trial": mean(
            len(row["dual_certificate_steps"]) for row in rows
        ),
    }


def decision(summary: dict[str, Any]) -> str:
    exact = int(summary["exact_trials"])
    ratio = float(summary["dual_to_full_ratio"])
    improvement = summary["dual_to_boundary_ratio"]
    if exact == 10 and ratio < 0.5 and improvement is not None and improvement <= 0.5:
        return "strong_go"
    if exact >= 9 and ratio < 0.5 and improvement is not None and improvement < 1.0:
        return "pilot_go"
    return "no_go"


def analyze(source_path: Path, r044_path: Path) -> dict[str, Any]:
    source = load_source(source_path)
    if file_sha256(r044_path) != source["experiment_config"]["source_sha256"]:
        raise ValueError("R044 source hash does not match the R055 material passport")
    r044 = json.loads(r044_path.read_text(encoding="utf-8"))
    vocabulary_size = int(r044["experiment_config"]["vocabulary_size"])
    calibration, heldout = split_rows(source["rows"])
    scores = calibration_scores(calibration)
    thresholds = {name: calibrated_threshold(values) for name, values in scores.items()}
    evaluated = [
        evaluate_row(
            source,
            row,
            support_gap=int(thresholds["support"]["radius"]),
            mass_radius=int(thresholds["mass"]["radius"]),
            boundary_radius=int(thresholds["boundary_only"]["radius"]),
            vocabulary_size=vocabulary_size,
        )
        for row in heldout
    ]
    summary = summarize(evaluated)
    calibration_size = len(calibration)
    marginal_floor = int(thresholds["support"]["order_rank"]) / (
        calibration_size + 1
    )
    joint_floor = max(0.0, 2 * marginal_floor - 1)
    result = {
        "schema": SCHEMA,
        "verification_status": "ANALYZED",
        "source": {
            "path": str(source_path),
            "sha256": file_sha256(source_path),
            "result_signature": source["result_signature"],
            "r044_path": str(r044_path),
            "r044_sha256": file_sha256(r044_path),
        },
        "method": {
            "name": "stratified conformal dual-barrier certificate",
            "calibration_split": "even prompt indices",
            "heldout_split": "odd prompt indices",
            "target_passes_per_heldout_certificate": 0,
            "alpha_per_barrier": ALPHA,
            "marginal_prompt_coverage_floor": marginal_floor,
            "joint_prompt_coverage_union_bound": joint_floor,
            "coverage_condition": "prompt-level exchangeability",
        },
        "calibration_scores": scores,
        "thresholds": thresholds,
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
            "# R056 分层双屏障证书结果",
            "",
            "## 材料护照",
            "",
            f"- 验证状态：`{result['verification_status']}`。",
            f"- R055 SHA-256：`{result['source']['sha256']}`。",
            f"- 结果签名：`{result['result_signature']}`。",
            "- 校准集：偶数 prompt；留出集：奇数 prompt。",
            "- 留出证书构造读取目标端次数：0。",
            f"- 每道屏障的有限样本 prompt 覆盖下界：{result['method']['marginal_prompt_coverage_floor']:.4%}。",
            f"- prompt 可交换性假设下的联合 union-bound 覆盖下界：{result['method']['joint_prompt_coverage_union_bound']:.4%}。",
            "",
            "## 冻结阈值",
            "",
            f"- 支持屏障 rank-2/rank-3 gap：{thresholds['support']['radius']} bins。",
            f"- 同支持质量屏障半径：{thresholds['mass']['radius']} counts。",
            f"- 单边界基线半径：{thresholds['boundary_only']['radius']} counts。",
            "",
            "## 留出结果",
            "",
            f"- 精确覆盖 trial：{summary['exact_trials']}/{summary['trials']}。",
            f"- 实际修正：{summary['actual_flips']}，其中支持变化 {summary['support_flips']}，质量迁移 {summary['mass_flips']}。",
            f"- false-safe 修正：{summary['dual_false_safe_flips']}。",
            f"- 双屏障证书密度：{summary['dual_certificate_density']:.4%}。",
            f"- 双屏障负载/完整轨迹：{summary['dual_to_full_ratio']:.4%}。",
            f"- 单边界负载/完整轨迹：{summary['boundary_to_full_ratio']:.4%}。",
            f"- 双屏障负载/单边界负载：{summary['dual_to_boundary_ratio']:.4%}。",
            f"- 双屏障负载/目标特定修正：{summary['dual_to_target_specific_ratio']:.3f} 倍。",
            f"- 预注册判定：`{result['decision']}`。",
            "",
            "## 解释边界",
            "",
            "该分析只证明同一 GPU 上 FP16/BF16 的留出可行性。有限样本覆盖下界依赖 prompt 级可交换性；人工 prompt 因此限制外部有效性。若结果通过，下一步必须扩展 seed，并与 R054、目标特定 SPRC 及完整轨迹同时报告。",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("outputs/R055_qwen_dual_barrier_trace.json"))
    parser.add_argument("--r044", type=Path, default=Path("outputs/R044_qwen_replay_scale.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/R056_dual_barrier_certificate.json"))
    parser.add_argument("--markdown", type=Path, default=Path("docs/reproducibility/R056_DUAL_BARRIER_RESULTS.md"))
    args = parser.parse_args()
    result = analyze(args.source, args.r044)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({"decision": result["decision"], **result["heldout"]["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
