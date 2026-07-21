from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.generate_native_quality_baseline import build_report, experiment_config, load_rows


def args() -> SimpleNamespace:
    return SimpleNamespace(
        run_label="test",
        model=Path("model"),
        device="cpu",
        dtype="float32",
        seed=0,
        top_k=16,
        temperature=1.2,
        tokens=8,
        sentence_stop_min_tokens=4,
        system_prompt="system",
        prompts_file=Path("prompts.json"),
        prompt_values=("one", "two"),
    )


def test_report_is_partial_until_every_prompt_completes() -> None:
    config = experiment_config(args())
    partial = build_report(config, [{"prompt_index": 0, "completed": True}], {})
    assert partial["phase"] == "partial"
    complete = build_report(
        config,
        [
            {"prompt_index": 0, "completed": True},
            {"prompt_index": 1, "completed": True},
        ],
        {},
    )
    assert complete["phase"] == "completed"


def test_checkpoint_rejects_configuration_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "checkpoint.json"
    path.write_text('{"experiment_config": {}, "rows": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="configuration mismatch"):
        load_rows(path, experiment_config(args()))
