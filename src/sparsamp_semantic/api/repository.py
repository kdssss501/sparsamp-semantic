"""Read and write sanitized experiment artifacts below the workspace output root."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ExperimentRepository:
    """Persist reproducible artifacts without ever storing a secret key."""

    def __init__(self, output_root: Path) -> None:
        self.output_root = output_root.resolve()
        self.output_root.mkdir(parents=True, exist_ok=True)

    def write(self, artifact_id: str, data: dict[str, Any]) -> str:
        path = self._resolve(f"web/{artifact_id}.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path.relative_to(self.output_root).as_posix()

    def read(self, artifact_id: str) -> dict[str, Any]:
        path = self._resolve(artifact_id)
        if path.suffix.lower() != ".json" or not path.is_file():
            raise FileNotFoundError(artifact_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def list_artifacts(self, limit: int, cursor: str | None = None) -> dict[str, Any]:
        paths = sorted(
            self.output_root.rglob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True
        )
        offset = self._cursor_offset(cursor)
        page_paths = paths[offset : offset + limit]
        data: list[dict[str, Any]] = []
        for path in page_paths:
            try:
                artifact = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            data.append(self._summary(path, artifact))
        next_offset = offset + len(page_paths)
        return {
            "data": data,
            "page": {
                "limit": limit,
                "next_cursor": str(next_offset) if next_offset < len(paths) else None,
            },
        }

    def list_grid_rows(self, limit: int, cursor: str | None = None) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        for path in sorted(self.output_root.rglob("*.jsonl")):
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            for index, line in enumerate(lines):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                row["source"] = path.relative_to(self.output_root).as_posix()
                row["row_index"] = index
                rows.append(row)
        rows.sort(key=lambda row: float(row.get("timestamp", 0)), reverse=True)
        offset = self._cursor_offset(cursor)
        page_rows = rows[offset : offset + limit]
        next_offset = offset + len(page_rows)
        return {
            "data": page_rows,
            "page": {
                "limit": limit,
                "next_cursor": str(next_offset) if next_offset < len(rows) else None,
            },
        }

    def _summary(self, path: Path, artifact: dict[str, Any]) -> dict[str, Any]:
        metrics = artifact.get("metrics", {})
        codec = artifact.get("codec", {})
        provider = artifact.get("provider", {})
        return {
            "id": path.relative_to(self.output_root).as_posix(),
            "prompt": artifact.get("prompt", ""),
            "cover_preview": artifact.get("cover_text", "")[:180],
            "created_at": path.stat().st_mtime,
            "model": provider.get("model_name", provider.get("model", "unknown")),
            "block_size": codec.get("block_size"),
            "token_ambiguity": artifact.get("token_ambiguity"),
            "metrics": metrics,
        }

    def _resolve(self, artifact_id: str) -> Path:
        path = (self.output_root / artifact_id).resolve()
        if path != self.output_root and self.output_root not in path.parents:
            raise ValueError("artifact path escapes the output root")
        return path

    @staticmethod
    def _cursor_offset(cursor: str | None) -> int:
        if cursor is None:
            return 0
        try:
            offset = int(cursor)
        except ValueError as error:
            raise ValueError("cursor must be a non-negative integer") from error
        if offset < 0:
            raise ValueError("cursor must be a non-negative integer")
        return offset
