"""Unified API error response schema and exception mapping."""

from __future__ import annotations

from fade_domain.types import ErrorCode
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorDetail(BaseModel):
    """Single error detail entry."""

    field: str | None = None
    message: str
    code: str | None = None


class ErrorResponse(BaseModel):
    """Stable error response envelope."""

    error: ErrorCode
    message: str
    correlation_id: str
    details: list[ErrorDetail] = Field(default_factory=list)


def _get_correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", "unknown")


def build_error_response(
    *,
    request: Request,
    error: ErrorCode,
    message: str,
    status_code: int,
    details: list[ErrorDetail] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        error=error,
        message=message,
        correlation_id=_get_correlation_id(request),
        details=details or [],
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    code_map: dict[int, ErrorCode] = {
        400: ErrorCode.VALIDATION_ERROR,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        409: ErrorCode.CONFLICT,
        503: ErrorCode.SERVICE_UNAVAILABLE,
    }
    error_code = code_map.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return build_error_response(
        request=request,
        error=error_code,
        message=detail,
        status_code=exc.status_code,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    details = [
        ErrorDetail(
            field=".".join(str(loc) for loc in err.get("loc", [])),
            message=str(err.get("msg", "")),
            code=str(err.get("type", "")),
        )
        for err in exc.errors()
    ]
    return build_error_response(
        request=request,
        error=ErrorCode.VALIDATION_ERROR,
        message="Request validation failed",
        status_code=422,
        details=details,
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    _ = exc
    return build_error_response(
        request=request,
        error=ErrorCode.INTERNAL_ERROR,
        message="An unexpected error occurred",
        status_code=500,
    )
