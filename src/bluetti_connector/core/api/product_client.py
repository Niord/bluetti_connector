from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .bluetti import Bluetti, TokenExpiredHandler
from .unify_response import UnifyResponse
from ..const import Method
from ..model.product import UserProduct
from ..profile.application_profile import ApplicationProfile


class ProductClient(Bluetti):
    """Standalone BLUETTI products client."""

    __LOGGER__: logging.Logger | None = None

    def __init__(
        self,
        httpSession: aiohttp.ClientSession,
        accessToken: str | None,
        application_profile: ApplicationProfile | None = None,
        on_token_expired: TokenExpiredHandler | None = None,
        request_timeout_seconds: float | None = None,
    ) -> None:
        super().__init__(
            httpSession=httpSession,
            accessToken=accessToken,
            application_profile=application_profile,
            on_token_expired=on_token_expired,
            request_timeout_seconds=request_timeout_seconds,
        )

    @property
    def logger(self) -> logging.Logger:
        if self.__LOGGER__ is None:
            self.__LOGGER__ = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        return self.__LOGGER__

    async def get_user_products(self) -> UnifyResponse[list[UserProduct]]:
        return await self._request(
            list[UserProduct],
            Method.GET,
            "/api/bluiotdata/ha/v1/devices",
        )

    async def get_device_status(self, sns: str | None = None) -> UnifyResponse[list[UserProduct]]:
        return await self._request(
            list[UserProduct],
            Method.GET,
            "/api/bluiotdata/ha/v1/deviceStates",
            params={"sns": sns},
        )

    async def control_device(self, payload: dict[str, Any] | None = None) -> UnifyResponse[dict[str, Any]]:
        return await self._request(
            dict[str, Any],
            method=Method.POST,
            path="/api/bluiotdata/ha/v1/fulfillment",
            body=payload,
        )

    async def bind_devices(self, payload: dict[str, Any] | None = None) -> UnifyResponse[dict[str, Any]]:
        return await self._request(
            dict[str, Any],
            method=Method.POST,
            path="/api/bluiotdata/ha/v1/bindDevices",
            body=payload,
        )