from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ..core.application_exception import ApplicationRuntimeException, AuthenticationExpiredError


class BackendAppError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | list[dict[str, Any]] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


class SessionNotConfiguredError(BackendAppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=503,
            code="SESSION_NOT_CONFIGURED",
            message="Configure a BLUETTI session before calling device endpoints.",
        )


class DeviceNotFoundError(BackendAppError):
    def __init__(self, device_sn: str) -> None:
        super().__init__(
            status_code=404,
            code="DEVICE_NOT_FOUND",
            message=f"BLUETTI device {device_sn} was not found.",
            details={"deviceSn": device_sn},
        )


class InvalidCommandError(BackendAppError):
    def __init__(self, device_sn: str, reason: str) -> None:
        super().__init__(
            status_code=400,
            code="INVALID_COMMAND",
            message="The requested device command is invalid for the current device state.",
            details={"deviceSn": device_sn, "reason": reason},
        )


class LiveVerificationPrerequisiteError(BackendAppError):
    def __init__(self, *, missing: list[str]) -> None:
        super().__init__(
            status_code=400,
            code="LIVE_VERIFICATION_PREREQUISITES_MISSING",
            message="Live-account verification prerequisites are not satisfied.",
            details={"missing": missing},
        )


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BackendAppError)
    async def handle_backend_error(request: Request, exc: BackendAppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=_error_content(exc.code, exc.message, exc.details))

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {
                "loc": list(error["loc"]),
                "msg": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_error_content(
                "VALIDATION_ERROR",
                "Request validation failed.",
                details,
            ),
        )

    @app.exception_handler(AuthenticationExpiredError)
    async def handle_authentication_expired(request: Request, exc: AuthenticationExpiredError) -> JSONResponse:
        details = {"upstreamCode": exc.msgCode}
        return JSONResponse(
            status_code=401,
            content=_error_content(
                "AUTHENTICATION_EXPIRED",
                "The BLUETTI session expired. Configure the session again.",
                details,
            ),
        )

    @app.exception_handler(ApplicationRuntimeException)
    async def handle_application_runtime_error(request: Request, exc: ApplicationRuntimeException) -> JSONResponse:
        details = {"upstreamCode": exc.msgCode}
        return JSONResponse(
            status_code=502,
            content=_error_content(
                "BLUETTI_CLOUD_ERROR",
                "The BLUETTI cloud rejected the request.",
                details,
            ),
        )

    @app.exception_handler(asyncio.TimeoutError)
    async def handle_timeout_error(request: Request, exc: asyncio.TimeoutError) -> JSONResponse:
        return JSONResponse(
            status_code=504,
            content=_error_content(
                "BLUETTI_TIMEOUT",
                "The BLUETTI backend request timed out.",
            ),
        )

    @app.exception_handler(aiohttp.ClientError)
    async def handle_client_error(request: Request, exc: aiohttp.ClientError) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content=_error_content(
                "BLUETTI_CONNECTIVITY_ERROR",
                "The BLUETTI backend could not reach the configured cloud endpoint.",
            ),
        )


def _error_content(code: str, message: str, details: dict[str, Any] | list[dict[str, Any]] | None = None) -> dict[str, Any]:
    content: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details is not None:
        content["error"]["details"] = details
    return content