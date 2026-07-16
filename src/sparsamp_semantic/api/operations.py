"""Thread-safe long-running operation resources for single-GPU execution."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime
from threading import Lock
from typing import Any, Callable
from uuid import uuid4


OperationTask = Callable[[str, Callable[[int, str], None]], dict[str, Any]]


class OperationManager:
    """Serialize expensive model work and expose immutable operation snapshots."""

    def __init__(self, max_workers: int = 1) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="gpu-job")
        self._lock = Lock()
        self._operations: dict[str, dict[str, Any]] = {}

    def submit(self, kind: str, task: OperationTask) -> dict[str, Any]:
        operation_id = uuid4().hex
        now = datetime.now(UTC).isoformat()
        operation = {
            "id": operation_id,
            "kind": kind,
            "status": "queued",
            "progress": 0,
            "stage": "等待 GPU",
            "created_at": now,
            "started_at": None,
            "finished_at": None,
            "result": None,
            "error": None,
        }
        with self._lock:
            self._operations[operation_id] = operation
        self._executor.submit(self._run, operation_id, task)
        return self.get(operation_id)

    def _run(self, operation_id: str, task: OperationTask) -> None:
        self._update(
            operation_id,
            status="running",
            progress=5,
            stage="准备模型",
            started_at=datetime.now(UTC).isoformat(),
        )
        try:
            result = task(
                operation_id,
                lambda progress, stage: self._update(operation_id, progress=progress, stage=stage),
            )
        except Exception as error:  # The operation resource carries worker failures to the UI.
            self._update(
                operation_id,
                status="failed",
                progress=100,
                stage="失败",
                finished_at=datetime.now(UTC).isoformat(),
                error={"code": "OPERATION_FAILED", "message": str(error)},
            )
            return
        self._update(
            operation_id,
            status="succeeded",
            progress=100,
            stage="完成",
            finished_at=datetime.now(UTC).isoformat(),
            result=result,
        )

    def _update(self, operation_id: str, **changes: Any) -> None:
        with self._lock:
            self._operations[operation_id].update(changes)

    def get(self, operation_id: str) -> dict[str, Any]:
        with self._lock:
            if operation_id not in self._operations:
                raise KeyError(operation_id)
            return deepcopy(self._operations[operation_id])

    def list(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            values = list(self._operations.values())[-limit:]
            return deepcopy(list(reversed(values)))

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
