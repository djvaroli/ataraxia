"""One error shape for every failed request."""

import logging
from collections.abc import Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from ataraxia.api.schemas import ErrorBody, ErrorCode, ErrorDetail, FieldError
from ataraxia.application.errors import ConflictError, LimitReachedError, NotFoundError
from ataraxia.domain.errors import InvalidInputError

logger = logging.getLogger(__name__)

_STATUS_CODES: dict[int, ErrorCode] = {
    401: "unauthenticated",
    403: "forbidden",
    404: "not_found",
    405: "not_found",
    409: "conflict",
    422: "validation_failed",
}


class ApiError(Exception):
    def __init__(
        self,
        status: int,
        code: ErrorCode,
        message: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code: ErrorCode = code
        self.message = message
        self.headers = headers


def error_response(
    status: int,
    code: ErrorCode,
    message: str,
    fields: list[FieldError] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    body = ErrorBody(error=ErrorDetail(code=code, message=message, fields=fields or []))
    return JSONResponse(body.model_dump(mode="json"), status_code=status, headers=headers)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    def api_error(_: Request, error: ApiError) -> JSONResponse:
        return error_response(error.status, error.code, error.message, headers=error.headers)

    @app.exception_handler(RequestValidationError)
    def validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
        fields = [
            FieldError(field=_field_name(issue.get("loc", ())), message=str(issue.get("msg", "")))
            for issue in error.errors()
        ]
        return error_response(422, "validation_failed", "The request is not valid.", fields)

    @app.exception_handler(InvalidInputError)
    def invalid_input(_: Request, error: InvalidInputError) -> JSONResponse:
        fields = [FieldError(field=error.field, message=str(error))]
        return error_response(422, "validation_failed", str(error), fields)

    @app.exception_handler(NotFoundError)
    def not_found(_: Request, error: NotFoundError) -> JSONResponse:
        return error_response(404, "not_found", str(error))

    @app.exception_handler(ConflictError)
    def conflict(_: Request, error: ConflictError) -> JSONResponse:
        return error_response(409, "conflict", str(error))

    @app.exception_handler(LimitReachedError)
    def limit(_: Request, error: LimitReachedError) -> JSONResponse:
        return error_response(429, error.code, str(error))

    @app.exception_handler(HTTPException)
    def http_error(_: Request, error: HTTPException) -> JSONResponse:
        code = _STATUS_CODES.get(error.status_code, "unavailable")
        message = error.detail if isinstance(error.detail, str) else "The request failed."
        return error_response(error.status_code, code, message, headers=error.headers)

    @app.exception_handler(Exception)
    def unexpected(request: Request, error: Exception) -> JSONResponse:
        # Only the type and path: messages can contain stored content.
        logger.error("Unhandled %s on %s", type(error).__name__, request.url.path)
        return error_response(500, "unavailable", "Something went wrong. Try again.")


def _field_name(location: object) -> str:
    """`body.topic` becomes `topic`; query parameters keep their name."""
    parts = [str(part) for part in location] if isinstance(location, tuple | list) else []
    if parts and parts[0] in ("body", "query", "path", "header"):
        parts = parts[1:]
    return ".".join(parts) or "request"
