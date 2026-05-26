from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from json import dumps
from typing import Any, Callable, Generic, TypeVar

import aiohttp
from pydantic import TypeAdapter

from .unify_response import UnifyResponse
from ..application_exception import ApplicationRuntimeException, AuthenticationExpiredError
from ..const import Method, TOKEN_EXPIRED_CODE
from ..profile.application_profile import APPLICATION_PROFILE, ApplicationProfile

T = TypeVar("T")
TokenExpiredHandler = Callable[[], None]


class Bluetti(Generic[T], ABC):
    _accessToken: str | None = None
    _httpSession: aiohttp.ClientSession

    @property
    @abstractmethod
    def logger(self) -> logging.Logger:
        """The subclass logger."""

    def __init__(
        self,
        httpSession: aiohttp.ClientSession,
        accessToken: str | None = None,
        application_profile: ApplicationProfile | None = None,
        on_token_expired: TokenExpiredHandler | None = None,
        request_timeout_seconds: float | None = None,
    ) -> None:
        self._httpSession = httpSession
        self._accessToken = accessToken
        self._application_profile = application_profile or APPLICATION_PROFILE
        self._on_token_expired = on_token_expired
        self._request_timeout_seconds = request_timeout_seconds

    async def _request(
        self,
        responseType: Any,
        method: Method,
        path: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> UnifyResponse[T] | str:
        if method == Method.GET:
            body = None

        profile = self._application_profile.ensure_loaded()
        gateway_url = profile["server"]["gateway"]
        headers: dict[str, str] = {}
        if self._accessToken:
            headers["Authorization"] = self._accessToken

        if params:
            params = {key: value for key, value in params.items() if value is not None}
            self.logger.debug("======> Client request parameters: %s", params)
        if body:
            body = {key: value for key, value in body.items() if value is not None}
            self.logger.debug("======> Client request body: %s", dumps(body))
            headers["Content-Type"] = "application/json"

        timeout = None
        if self._request_timeout_seconds is not None:
            timeout = aiohttp.ClientTimeout(total=self._request_timeout_seconds)

        async with self._httpSession.request(
            method,
            f"{gateway_url}{path}",
            headers=headers,
            json=body,
            params=params,
            timeout=timeout,
        ) as response:
            self.logger.debug("<====== Server response status %s from %s", response.status, response.url)
            self.logger.debug("<====== Server response type is: %s", response.content_type)

            if response.status >= 400:
                raise ApplicationRuntimeException(msgCode=response.status, data=await response.text())

            if response.content_type.lower().startswith("application/json"):
                payload = await response.json()
                unify_response = TypeAdapter(UnifyResponse[responseType]).validate_python(payload)
                if unify_response.msgCode == TOKEN_EXPIRED_CODE:
                    self._notify_token_expired()
                    raise AuthenticationExpiredError(
                        msgCode=unify_response.msgCode,
                        data=payload,
                    )
                return unify_response

            return await response.text()

    def _notify_token_expired(self) -> None:
        if self._on_token_expired is not None:
            self._on_token_expired()