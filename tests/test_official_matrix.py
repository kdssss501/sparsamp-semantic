import json
from pathlib import Path

import pytest

from scripts.run_official_matrix import build_report, load_rows, summarize, trial_plan


def completed_row(block_size: int, top_p: float, context_index: int) -> dict:
    return {
        "block_size": block_size,
        "top_p": top_p,
        "context_index": context_index,
        "paper_suites": [],
        "status": "completed",
        "token_count": 100,
        "encoded_bits": 400,
        "entropy_bits": 500.0,
        "decode_success": True,
        "hardware_inconsistency": False,
        "token_ambiguity": False,
        "generation_seconds": 2.0,
        "sampling_seconds": 0.1,
        "model_seconds": 1.9,
        "decode_seconds": 1.0,
    }


def test_trial_plan_deduplicates_shared_block64_top_p1() -> None:
    plan = trial_plan((2, 64), (0.8, 1.0), (3, 4))
    assert len(plan) == 6
    shared = [row for row in plan if row["block_size"] == 64 and row["top_p"] == 1.0]
    assert len(shared) == 2
    assert shared[0]["paper_suites"] == ["paper_table2", "paper_tables3_4"]


def test_summary_uses_matching_aggregate_denominators() -> None:
    result = summarize([completed_row(64, 1.0, 0), completed_row(64, 1.0, 1)])[0]
    assert result["decoding_accuracy"] == 1.0
    assert result["embedding_rate"] == 4.0
    assert result["utilization"] == 0.8
    assert result["sampling_atst_s_token"] == pytest.approx(0.001)
    assert result["sampling_to_inference_ratio"] == pytest.approx(0.1 / 1.9)
    assert result["generation_speed_tokens_s"] == 50.0


def test_report_and_checkpoint_require_exact_configuration(tmp_path: Path) -> None:
    config = {"name": "official"}
    row = completed_row(64, 1.0, 0)
    report = build_report(config, [row], 1, {})
    assert report["phase"] == "completed"
    path = tmp_path / "checkpoint.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    assert load_rows(path, config) == [row]
    with pytest.raises(ValueError, match="configuration mismatch"):
        load_rows(path, {"name": "changed"})
