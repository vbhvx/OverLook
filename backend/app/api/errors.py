# backend/app/api/errors.py
"""
One error envelope for every failure:

    {"error": "<machine code>", "message": "<human text>", "requestId": "...", "details"?: [...]}

The request ID matches the X-Request-ID response header and the server logs.
Unhandled exceptions are turned into a 500 envelope by RequestContextMiddleware.
"""
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.core.logging import request_id_ctx

_CODES = {
    400: "bad_request",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    503: "unavailable",
}


def error_body(status_code: int, message: str, details: Optional[Any] = None) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "error": _CODES.get(status_code, "error"),
        "message": message,
        "requestId": request_id_ctx.get(),
    }
    if details is not None:
        body["details"] = details
    return body


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.status_code, str(exc.detail)),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        # Strip the echoed input so we never reflect request payloads back.
        details = [{k: v for k, v in e.items() if k in ("loc", "msg", "type")} for e in exc.errors()]
        return JSONResponse(
            status_code=422,
            content=error_body(422, "Request validation failed", details),
        )
