"""FastAPI application factory for the local SparSamp research workbench."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import Body, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .operations import OperationManager
from .repository import ExperimentRepository
from .schemas import (
    DecodeOperationRequest,
    EncodeOperationRequest,
    NativeOperationRequest,
    OperationCreateRequest,
)
from .service import ResearchService, project_root


def create_app(
    output_root: Path | None = None,
    web_dist: Path | None = None,
    service: ResearchService | None = None,
) -> FastAPI:
    """Create an isolated app instance suitable for production or contract tests."""

    root = project_root()
    repository = ExperimentRepository(output_root or root / "outputs")
    research = service or ResearchService(repository)
    operations = OperationManager(max_workers=1)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        operations.shutdown()

    app = FastAPI(
        title="SparSamp Research Workbench API",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.operations = operations
    app.state.repository = repository
    app.state.research = research
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Request-ID"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        return _error_response(
            request,
            422,
            "VALIDATION_ERROR",
            "请求参数不合法",
            {"errors": error.errors()},
        )

    @app.get("/api/v1/system/status")
    def system_status() -> dict[str, Any]:
        import torch

        model_path = root / "models" / "qwen2.5-1.5b-instruct"
        cuda_available = torch.cuda.is_available()
        gpu = None
        if cuda_available:
            free_bytes, total_bytes = torch.cuda.mem_get_info()
            gpu = {
                "name": torch.cuda.get_device_name(0),
                "free_vram_bytes": free_bytes,
                "total_vram_bytes": total_bytes,
            }
        return {
            "data": {
                "torch_version": torch.__version__,
                "cuda_available": cuda_available,
                "gpu": gpu,
                "model": {
                    "path": str(model_path),
                    "available": (model_path / "model.safetensors").is_file(),
                },
                "operation_count": len(operations.list(limit=100)),
            }
        }

    @app.post("/api/v1/operations", status_code=202)
    def create_operation(
        response: Response,
        request: OperationCreateRequest = Body(discriminator="kind"),
    ) -> dict[str, Any]:
        if isinstance(request, EncodeOperationRequest):
            operation = operations.submit(
                request.kind,
                lambda operation_id, progress: research.encode(operation_id, request, progress),
            )
        elif isinstance(request, DecodeOperationRequest):
            operation = operations.submit(
                request.kind,
                lambda operation_id, progress: research.decode(operation_id, request, progress),
            )
        elif isinstance(request, NativeOperationRequest):
            operation = operations.submit(
                request.kind,
                lambda operation_id, progress: research.native(operation_id, request, progress),
            )
        else:  # pragma: no cover - Pydantic's discriminator makes this unreachable.
            raise HTTPException(status_code=422, detail="unsupported operation kind")
        response.headers["Location"] = f"/api/v1/operations/{operation['id']}"
        return {"data": operation}

    @app.get("/api/v1/operations")
    def list_operations(limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
        return {"data": operations.list(limit=limit)}

    @app.get("/api/v1/operations/{operation_id}", response_model=None)
    def get_operation(operation_id: str, request: Request) -> dict[str, Any] | JSONResponse:
        try:
            return {"data": operations.get(operation_id)}
        except KeyError:
            return _error_response(
                request, 404, "OPERATION_NOT_FOUND", "找不到该任务", {"id": operation_id}
            )

    @app.get("/api/v1/artifacts", response_model=None)
    def list_artifacts(
        request: Request,
        limit: int = Query(default=20, ge=1, le=100),
        cursor: str | None = None,
    ) -> dict[str, Any] | JSONResponse:
        try:
            return repository.list_artifacts(limit, cursor)
        except ValueError as error:
            return _error_response(request, 400, "INVALID_CURSOR", str(error))

    @app.get("/api/v1/artifacts/{artifact_id:path}", response_model=None)
    def get_artifact(artifact_id: str, request: Request) -> dict[str, Any] | JSONResponse:
        try:
            return {"data": repository.read(artifact_id)}
        except (FileNotFoundError, ValueError):
            return _error_response(
                request, 404, "ARTIFACT_NOT_FOUND", "找不到该实验记录", {"id": artifact_id}
            )

    @app.get("/api/v1/grid-results", response_model=None)
    def list_grid_results(
        request: Request,
        limit: int = Query(default=100, ge=1, le=500),
        cursor: str | None = None,
    ) -> dict[str, Any] | JSONResponse:
        try:
            return repository.list_grid_rows(limit, cursor)
        except ValueError as error:
            return _error_response(request, 400, "INVALID_CURSOR", str(error))

    static_root = web_dist or root / "web" / "dist"
    if static_root.is_dir():
        app.mount("/", StaticFiles(directory=static_root, html=True), name="web")
    return app


def _error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )
