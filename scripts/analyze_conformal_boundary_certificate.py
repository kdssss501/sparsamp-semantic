"""R054 held-out audit of conformal integer-boundary replay certificates."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from statistics import mean, median
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from sparsamp_semantic.conformal_replay import (  # noqa: E402
    build_reference_only_certificate,
    split_conformal_upper_radius,
    trajectory_correction_radii,
)
from sparsamp_semantic.replay_certificate import (  # noqa: E402
    ReplayContractConfig,
    decision_context,
    manifest_payload_sizes,
)
from sparsamp_semantic.replay_package import canonical_signature  # noqa: E402


SCHEMA = "conformal-boundary-certificate-analysis-v1"
PRIMARY_ALPHA = 0.10
SECONDARY_ALPHAS = (0.20, 0.30, 0.40)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def replay_config(source: dict[str, Any], seed: int) -> ReplayContractConfig:
    config = source["experiment_config"]
    return ReplayContractConfig(
        contract_top_k=int(config["contract_top_k"]),
        logit_quantum=float(config["logit_quantum"]),
        mass_bits=int(config["mass_bits"]),
        temperature=float(config["temperature"]),
        public_seed=seed,
    )


def row_context(source: dict[str, Any], row: dict[str, Any]) -> tuple[bytes, ReplayContractConfig]:
    config = replay_config(source, int(row["seed"]))
    context = decision_context(
        str(source["experiment_config"]["model"]), str(row["prompt"]), config
    )
    return context, config


def row_score(source: dict[str, Any], row: dict[str, Any]) -> int:
    return max(row_correction_radii(source, row), default=0)


def row_correction_radii(source: dict[str, Any], row: dict[str, Any]) -> tuple[int, ...]:
    context, config = row_context(source, row)
    counts = tuple(tuple(int(value) for value in item["counts"]) for item in row["reference_contracts"])
    correction_steps = tuple(int(item["step"]) for item in row["corrections"])
    return trajectory_correction_radii(
        counts,
        correction_steps,
        context=context,
        public_seed=config.public_seed,
    )


def prompt_scores(source: dict[str, Any], rows: list[dict[str, Any]]) -> dict[int, int]:
    grouped: dict[int, list[int]] = {}
    for row in rows:
        grouped.setdefault(int(row["prompt_index"]), []).append(row_score(source, row))
    return {prompt: max(scores) for prompt, scores in grouped.items()}


def split_prompt_rows(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate and return the frozen even/odd prompt-cluster split."""

    expected_prompts = set(range(20))
    expected_seeds = {0, 1, 2}
    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(int(row["prompt_index"]), []).append(row)
    if set(grouped) != expected_prompts:
        raise ValueError("seeded rows must contain prompt indices 0 through 19")
    for prompt_index, prompt_rows in grouped.items():
        seeds = [int(row["seed"]) for row in prompt_rows]
        if len(seeds) != 3 or set(seeds) != expected_seeds:
            raise ValueError(
                f"prompt {prompt_index} must contain exactly seeds 0, 1, and 2"
            )
    calibration = [row for row in rows if int(row["prompt_index"]) % 2 == 0]
    heldout = [row for row in rows if int(row["prompt_index"]) % 2 == 1]
    return calibration, heldout


def evaluate_row(source: dict[str, Any], row: dict[str, Any], radius: int) -> dict[str, Any]:
    context, config = row_context(source, row)
    reference = tuple(int(value) for value in row["reference_token_ids"])
    counts = tuple(tuple(int(value) for value in item["counts"]) for item in row["reference_contracts"])
    certificate = build_reference_only_certificate(
        reference,
        counts,
        context=context,
        public_seed=config.public_seed,
        radius=radius,
    )
    actual_steps = {int(item["step"]) for item in row["corrections"]}
    ambiguous_steps = set(certificate.ambiguous_steps)
    false_safe = sorted(actual_steps - ambiguous_steps)
    sparse_bytes, full_bytes = manifest_payload_sizes(
        certificate.manifest,
        vocabulary_size=int(source["experiment_config"]["vocabulary_size"]),
    )
    correction_radii = row_correction_radii(source, row)
    return {
        "prompt_index": int(row["prompt_index"]),
        "seed": int(row["seed"]),
        "policy": str(row["policy"]),
        "token_count": len(reference),
        "required_radius": max(correction_radii, default=0),
        "correction_radii": list(correction_radii),
        "certificate_radius": radius,
        "actual_correction_count": len(actual_steps),
        "ambiguous_count": len(ambiguous_steps),
        "ambiguous_steps": sorted(ambiguous_steps),
        "false_safe_steps": false_safe,
        "certificate_exact": not false_safe,
        "certificate_payload_bytes": sparse_bytes,
        "target_specific_payload_bytes": int(row["sparse_payload_bytes"]),
        "full_trace_payload_bytes": full_bytes,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    prompt_ids = sorted({int(row["prompt_index"]) for row in rows})
    prompt_exact = {
        prompt: all(
            bool(row["certificate_exact"])
            for row in rows
            if int(row["prompt_index"]) == prompt
        )
        for prompt in prompt_ids
    }
    tokens = sum(int(row["token_count"]) for row in rows)
    ambiguous = sum(int(row["ambiguous_count"]) for row in rows)
    actual = sum(int(row["actual_correction_count"]) for row in rows)
    false_safe = sum(len(row["false_safe_steps"]) for row in rows)
    correction_radii = [
        int(radius) for row in rows for radius in row["correction_radii"]
    ]
    certificate_bytes = sum(int(row["certificate_payload_bytes"]) for row in rows)
    target_bytes = sum(int(row["target_specific_payload_bytes"]) for row in rows)
    full_bytes = sum(int(row["full_trace_payload_bytes"]) for row in rows)
    return {
        "trials": len(rows),
        "prompts": len(prompt_ids),
        "exact_trials": sum(bool(row["certificate_exact"]) for row in rows),
        "exact_prompts": sum(prompt_exact.values()),
        "prompt_exact": prompt_exact,
        "tokens": tokens,
        "actual_corrections": actual,
        "ambiguous_steps": ambiguous,
        "false_safe_corrections": false_safe,
        "actual_correction_density": actual / tokens,
        "certificate_density": ambiguous / tokens,
        "certificate_payload_bytes": certificate_bytes,
        "target_specific_payload_bytes": target_bytes,
        "full_trace_payload_bytes": full_bytes,
        "certificate_to_full_ratio": certificate_bytes / full_bytes,
        "certificate_to_target_specific_ratio": (
            certificate_bytes / target_bytes if target_bytes else None
        ),
        "mean_required_radius": mean(int(row["required_radius"]) for row in rows),
        "max_required_radius": max(int(row["required_radius"]) for row in rows),
        "correction_radius_min": min(correction_radii) if correction_radii else None,
        "correction_radius_median": median(correction_radii) if correction_radii else None,
        "correction_radius_mean": mean(correction_radii) if correction_radii else None,
        "correction_radius_max": max(correction_radii) if correction_radii else None,
    }


def evaluate_radius(
    source: dict[str, Any], rows: list[dict[str, Any]], radius: int
) -> dict[str, Any]:
    evaluated = [evaluate_row(source, row, radius) for row in rows]
    return {"radius": radius, "summary": summarize(evaluated), "rows": evaluated}


def decision(summary: dict[str, Any]) -> str:
    prompt_coverage = int(summary["exact_prompts"])
    ratio = float(summary["certificate_to_full_ratio"])
    expansion = summary["certificate_to_target_specific_ratio"]
    if prompt_coverage == 10 and ratio < 0.5 and expansion is not None and expansion <= 2.0:
        return "strong_go"
    if prompt_coverage >= 9 and ratio < 0.5:
        return "pilot_go"
    return "no_go"


def analyze(source_path: Path, *, alpha: float = PRIMARY_ALPHA) -> dict[str, Any]:
    source = json.loads(source_path.read_text(encoding="utf-8"))
    if source.get("phase") != "completed":
        raise ValueError("source replay report must be completed")
    rows = [row for row in source["rows"] if str(row["policy"]) == "seeded"]
    calibration, heldout = split_prompt_rows(rows)

    calibration_by_prompt = prompt_scores(source, calibration)
    conformal = split_conformal_upper_radius(
        list(calibration_by_prompt.values()), alpha=alpha
    )
    if conformal.radius is None:
        raise ValueError("primary alpha has no finite split-conformal radius")
    primary = evaluate_radius(source, heldout, conformal.radius)

    pareto: list[dict[str, Any]] = []
    for candidate_alpha in (alpha, *SECONDARY_ALPHAS):
        calibrated = split_conformal_upper_radius(
            list(calibration_by_prompt.values()), alpha=candidate_alpha
        )
        if calibrated.radius is None:
            pareto.append(
                {
                    "alpha": candidate_alpha,
                    "order_rank": calibrated.order_rank,
                    "radius": None,
                    "finite": False,
                }
            )
            continue
        evaluated = evaluate_radius(source, heldout, calibrated.radius)
        pareto.append(
            {
                "alpha": candidate_alpha,
                "order_rank": calibrated.order_rank,
                "radius": calibrated.radius,
                "finite": True,
                "summary": evaluated["summary"],
            }
        )

    result = {
        "schema": SCHEMA,
        "verification_status": "ANALYZED",
        "source": {
            "path": str(source_path),
            "sha256": file_sha256(source_path),
            "result_signature": source.get("result_signature"),
        },
        "method": {
            "name": "conformal contract-reachability certificate",
            "construction_target_passes_per_heldout_trajectory": 0,
            "calibration_split": "even prompt indices",
            "heldout_split": "odd prompt indices",
            "cluster_unit": "prompt with three public seeds",
            "alpha": alpha,
            "integer_mass_total": 1 << int(source["experiment_config"]["mass_bits"]),
        },
        "calibration": {
            "prompt_scores": calibration_by_prompt,
            "order_rank": conformal.order_rank,
            "radius": conformal.radius,
        },
        "primary": primary,
        "pareto": pareto,
    }
    result["decision"] = decision(primary["summary"])
    result["result_signature"] = canonical_signature(result)
    return result


def render_markdown(result: dict[str, Any]) -> str:
    summary = result["primary"]["summary"]
    calibration = result["calibration"]
    lines = [
        "# R054 共形边界证书结果",
        "",
        "## 材料护照",
        "",
        f"- 验证状态：`{result['verification_status']}`。",
        f"- 源文件 SHA-256：`{result['source']['sha256']}`。",
        f"- 结果签名：`{result['result_signature']}`。",
        "- 校准集为偶数 prompt 索引；留出评估集为奇数 prompt 索引。",
        "- 每条留出轨迹构造证书时读取目标端的次数：0。",
        "",
        "## 主结果",
        "",
        f"- prompt 级共形显著性水平：{result['method']['alpha']:.2f}。",
        f"- 校准顺序统计量：10 个 prompt 中第 {calibration['order_rank']} 个。",
        f"- 校准整数边界半径：{calibration['radius']} / {result['method']['integer_mass_total']}。",
        f"- 留出 prompt 覆盖率：{summary['exact_prompts']}/{summary['prompts']}。",
        f"- 留出轨迹覆盖率：{summary['exact_trials']}/{summary['trials']}。",
        f"- 错误安全判断的修正数：{summary['false_safe_corrections']}。",
        f"- 仅参考端证书密度：{summary['certificate_density']:.4%}。",
        f"- 实际目标特定修正密度：{summary['actual_correction_density']:.4%}。",
        f"- 证书负载相对完整轨迹：{summary['certificate_to_full_ratio']:.4%}。",
        f"- 证书负载相对目标特定 SPRC：{summary['certificate_to_target_specific_ratio']:.3f} 倍。",
        f"- 预注册判定：`{result['decision']}`。",
        "",
        "## 原始半径分布",
        "",
        f"- 44 个实际修正位置的最小半径：{summary['correction_radius_min']}。",
        f"- 中位半径：{summary['correction_radius_median']}。",
        f"- 平均半径：{summary['correction_radius_mean']:.2f}。",
        f"- 最大半径：{summary['correction_radius_max']}。",
        "",
        "## 结论边界",
        "",
        "观察：跨精度修正并未稳定集中在公开整数 CDF 边界附近。覆盖大部分修正需要过大的半径，使稀疏证书比完整轨迹更贵。",
        "",
        "解释：单一参考端边界裕量没有刻画 FP16/BF16 之间候选支持变化或整数质量整体迁移；R054 因而否定了边界裕量足以形成低成本证书这一机制假设。",
        "",
        "含义：该结果不能支持 CCRC 方法主张，但能支持一个受限负结论。它不否定其他包含支持稳定性或质量迁移上界的合同证书。",
        "",
        "下一步：冻结 R054，不调整 split 或主 alpha。R055 应逐步记录 BF16 候选支持与整数 counts，以区分支持变化和质量迁移，并设置可断点保存。",
        "",
        "每条留出轨迹的证书只由 FP16 参考合同和校准集半径构造；保存的 BF16 修正仅用于事后评估。名义共形陈述依赖 prompt 级可交换性，人工 prompt 与单一物理 GPU 限制了外部有效性。本结果不构成跨硬件认证。",
        "",
        "## 固定次要 Pareto 点",
        "",
    ]
    for item in result["pareto"]:
        if not item["finite"]:
            lines.append(f"- alpha={item['alpha']:.2f}：不存在有限半径。")
            continue
        item_summary = item["summary"]
        lines.append(
            f"- alpha={item['alpha']:.2f}：半径={item['radius']}，"
            f"prompt 覆盖={item_summary['exact_prompts']}/{item_summary['prompts']}，"
            f"负载/完整轨迹={item_summary['certificate_to_full_ratio']:.4%}。"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", type=Path, default=Path("outputs/R044_qwen_replay_scale.json")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/R054_conformal_boundary_certificate.json")
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=Path("docs/reproducibility/R054_CONFORMAL_BOUNDARY_RESULTS.md"),
    )
    parser.add_argument("--alpha", type=float, default=PRIMARY_ALPHA)
    args = parser.parse_args()
    result = analyze(args.source, alpha=args.alpha)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({"decision": result["decision"], **result["primary"]["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
