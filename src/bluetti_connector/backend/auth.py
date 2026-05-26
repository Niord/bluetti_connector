from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import aiohttp
from pydantic import BaseModel, Field, ValidationError

from ..core import ApplicationRuntimeException, AuthenticationExpiredError


_AUTH_ERROR_CODES = frozenset({"invalid_grant", "invalid_token", "unauthorized_client"})


class TokenGrantResponse(BaseModel):
    access_token: str = Field(min_length=1)
    refresh_token: str | None = Field(default=None, min_length=1)


@dataclass(frozen=True)
class TokenGrantState:
    access_token: str
    refresh_token: str | None = None


def build_authorize_url(
    *,
    sso_url: str,
    client_id: str,
    redirect_uri: str,
    state: str,
) -> str:
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
        }
    )
    return f"{sso_url.rstrip('/')}/oauth2/grant?{query}"


async def exchange_authorization_code(
    *,
    sso_url: str,
    code: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str,
    request_timeout_seconds: float | None,
) -> TokenGrantState:
    status_code, payload = await _request_token_payload(
        sso_url=sso_url,
        request_timeout_seconds=request_timeout_seconds,
        grant_payload={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        },
    )

    if status_code >= 400:
        raise ApplicationRuntimeException(msgCode=status_code, data=payload)

    return _parse_token_grant_payload(status_code, payload, "The BLUETTI OAuth callback response was invalid.")


async def refresh_access_token(
    *,
    sso_url: str,
    refresh_token: str,
    client_id: str,
    client_secret: str,
    request_timeout_seconds: float | None,
) -> TokenGrantState:
    status_code, payload = await _request_token_payload(
        sso_url=sso_url,
        request_timeout_seconds=request_timeout_seconds,
        grant_payload={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        },
    )

    if status_code >= 400:
        _raise_refresh_error(status_code, payload)

    return _parse_token_grant_payload(status_code, payload, "The BLUETTI token refresh response was invalid.")


async def _request_token_payload(
    *,
    sso_url: str,
    request_timeout_seconds: float | None,
    grant_payload: dict[str, str],
) -> tuple[int, dict[str, Any] | str]:
    timeout = None
    if request_timeout_seconds is not None:
        timeout = aiohttp.ClientTimeout(total=request_timeout_seconds)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            f"{sso_url.rstrip('/')}/oauth2/token",
            data=grant_payload,
            headers={"Accept": "application/json"},
        ) as response:
            return response.status, await _read_response_payload(response)


def _parse_token_grant_payload(
    status_code: int,
    payload: dict[str, Any] | str,
    error_message: str,
) -> TokenGrantState:
    try:
        token_payload = TokenGrantResponse.model_validate(payload)
    except ValidationError as exc:
        raise ApplicationRuntimeException(
            msgCode=status_code,
            data=payload,
            errMessage=error_message,
        ) from exc

    return TokenGrantState(
        access_token=token_payload.access_token,
        refresh_token=token_payload.refresh_token,
    )


async def _read_response_payload(response: aiohttp.ClientResponse) -> dict[str, Any] | str:
    if response.content_type.lower().startswith("application/json"):
        return await response.json()
    return await response.text()


def _raise_refresh_error(status_code: int, payload: dict[str, Any] | str) -> None:
    if isinstance(payload, dict) and payload.get("error") in _AUTH_ERROR_CODES:
        raise AuthenticationExpiredError(msgCode=status_code, data=payload)
    raise ApplicationRuntimeException(msgCode=status_code, data=payload)