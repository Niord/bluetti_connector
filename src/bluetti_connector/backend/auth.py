from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aiohttp
from pydantic import BaseModel, Field, ValidationError

from ..core import ApplicationRuntimeException, AuthenticationExpiredError


_AUTH_ERROR_CODES = frozenset({"invalid_grant", "invalid_token", "unauthorized_client"})


class TokenRefreshResponse(BaseModel):
    access_token: str = Field(min_length=1)
    refresh_token: str | None = Field(default=None, min_length=1)


@dataclass(frozen=True)
class RefreshedTokenState:
    access_token: str
    refresh_token: str | None = None


async def refresh_access_token(
    *,
    sso_url: str,
    refresh_token: str,
    client_id: str,
    client_secret: str,
    request_timeout_seconds: float | None,
) -> RefreshedTokenState:
    timeout = None
    if request_timeout_seconds is not None:
        timeout = aiohttp.ClientTimeout(total=request_timeout_seconds)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            f"{sso_url.rstrip('/')}/oauth2/token",
            data={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
            },
            headers={"Accept": "application/json"},
        ) as response:
            status_code = response.status
            payload = await _read_response_payload(response)

    if status_code >= 400:
        _raise_refresh_error(status_code, payload)

    try:
        token_payload = TokenRefreshResponse.model_validate(payload)
    except ValidationError as exc:
        raise ApplicationRuntimeException(
            msgCode=status_code,
            data=payload,
            errMessage="The BLUETTI token refresh response was invalid.",
        ) from exc

    return RefreshedTokenState(
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