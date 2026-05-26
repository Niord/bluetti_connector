from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from typing import TypeVar

import aiohttp

from ..config import Settings
from ..core import ApplicationProfile, AuthenticationExpiredError, BluettiData, BluettiDevice, ProductClient
from .auth import refresh_access_token
from .errors import DeviceNotFoundError, InvalidCommandError, SessionNotConfiguredError
from .schemas import (
    AuthMode,
    DeviceCommandResponse,
    DeviceListResponse,
    DevicePayload,
    DeviceRefreshResponse,
    DeviceStatePayload,
    SessionSnapshot,
    SessionSetupRequest,
)
from .token_store import LocalTokenStore, StoredSessionState


T = TypeVar("T")


@dataclass
class SessionConfig:
    access_token: str | None
    refresh_token: str | None
    sso_url: str
    gateway_url: str
    wss_url: str
    source: str
    auth_mode: AuthMode
    uses_stored_session: bool = False


class BackendService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._token_store = LocalTokenStore(settings.token_store)
        self._session_config = self._load_initial_session_config()

    def get_session_snapshot(self) -> SessionSnapshot:
        if self._session_config is None:
            return SessionSnapshot(
                configured=False,
                source=None,
                authMode=None,
                usesStoredSession=False,
                hasAccessToken=False,
                hasRefreshToken=False,
                cloud={
                    "ssoUrl": self._settings.cloud_sso_url,
                    "gatewayUrl": self._settings.cloud_gateway_url,
                    "wssUrl": self._settings.cloud_wss_url,
                },
            )

        return SessionSnapshot(
            configured=True,
            source=self._session_config.source,
            authMode=self._session_config.auth_mode,
            usesStoredSession=self._session_config.uses_stored_session,
            hasAccessToken=bool(self._session_config.access_token),
            hasRefreshToken=bool(self._session_config.refresh_token),
            cloud={
                "ssoUrl": self._session_config.sso_url,
                "gatewayUrl": self._session_config.gateway_url,
                "wssUrl": self._session_config.wss_url,
            },
        )

    def configure_session(self, payload: SessionSetupRequest) -> SessionSnapshot:
        self._session_config = SessionConfig(
            access_token=payload.accessToken,
            refresh_token=payload.refreshToken,
            sso_url=payload.ssoUrl or self._settings.cloud_sso_url,
            gateway_url=payload.gatewayUrl or self._settings.cloud_gateway_url,
            wss_url=payload.wssUrl or self._settings.cloud_wss_url,
            source="request",
            auth_mode=self._resolve_auth_mode(
                access_token=payload.accessToken,
                refresh_token=payload.refreshToken,
            ),
        )
        self._persist_session_state(self._session_config)
        return self.get_session_snapshot()

    def _load_initial_session_config(self) -> SessionConfig | None:
        stored_state = self._token_store.load()
        if stored_state is not None:
            return SessionConfig(
                access_token=stored_state.accessToken,
                refresh_token=stored_state.refreshToken,
                sso_url=stored_state.ssoUrl or self._settings.cloud_sso_url,
                gateway_url=stored_state.gatewayUrl or self._settings.cloud_gateway_url,
                wss_url=stored_state.wssUrl or self._settings.cloud_wss_url,
                source="store",
                auth_mode=stored_state.authMode,
                uses_stored_session=True,
            )

        return self._settings_session_config()

    def _settings_session_config(self) -> SessionConfig | None:
        if self._settings.access_token or self._settings.refresh_token:
            return SessionConfig(
                access_token=self._settings.access_token or None,
                refresh_token=self._settings.refresh_token or None,
                sso_url=self._settings.cloud_sso_url,
                gateway_url=self._settings.cloud_gateway_url,
                wss_url=self._settings.cloud_wss_url,
                source="settings",
                auth_mode="token",
            )

        return None

    async def list_devices(self) -> DeviceListResponse:
        return await self._run_with_auth_recovery(self._list_devices_with_client)

    async def refresh_device(self, device_sn: str) -> DeviceRefreshResponse:
        return await self._run_with_auth_recovery(lambda client: self._refresh_device_with_client(client, device_sn))

    async def execute_command(self, device_sn: str, fn_code: str, fn_value: str) -> DeviceCommandResponse:
        return await self._run_with_auth_recovery(
            lambda client: self._execute_command_with_client(client, device_sn, fn_code, fn_value)
        )

    async def _list_devices_with_client(self, client: ProductClient) -> DeviceListResponse:
        products = await client.get_user_products()
        devices = BluettiData(products.data or [])
        return DeviceListResponse(count=len(devices.devices), items=[self._serialize_device(device) for device in devices.devices])

    async def _refresh_device_with_client(self, client: ProductClient, device_sn: str) -> DeviceRefreshResponse:
        device = await self._load_device(client, device_sn)
        return DeviceRefreshResponse(item=self._serialize_device(device))

    async def _execute_command_with_client(
        self,
        client: ProductClient,
        device_sn: str,
        fn_code: str,
        fn_value: str,
    ) -> DeviceCommandResponse:
        device = await self._load_device(client, device_sn)
        try:
            await device.set_state_value(fn_code, fn_value)
        except ValueError as exc:
            raise InvalidCommandError(device_sn, str(exc)) from exc
        return DeviceCommandResponse(accepted=True, device=self._serialize_device(device))

    async def _load_device(self, client: ProductClient, device_sn: str) -> BluettiDevice:
        status = await client.get_device_status(device_sn)
        devices = BluettiData(status.data or [])
        devices.attach_api_client(client)
        device = devices.get_device_by_sn(device_sn)
        if device is None:
            raise DeviceNotFoundError(device_sn)
        return device

    def _create_profile(self) -> ApplicationProfile:
        session_config = self._require_session_config()
        profile = ApplicationProfile(active="runtime")
        profile.config = {
            "server": {
                "sso": session_config.sso_url,
                "gateway": session_config.gateway_url,
                "wss": session_config.wss_url,
            }
        }
        return profile

    def _require_session_config(self) -> SessionConfig:
        if self._session_config is None:
            raise SessionNotConfiguredError()
        return self._session_config

    async def _run_with_auth_recovery(self, operation: Callable[[ProductClient], Awaitable[T]]) -> T:
        await self._ensure_access_token()
        refresh_attempted = False

        while True:
            try:
                async with self._product_client() as client:
                    return await operation(client)
            except AuthenticationExpiredError:
                session_config = self._require_session_config()
                if refresh_attempted or not session_config.refresh_token:
                    self._invalidate_session()
                    raise

                await self._refresh_session_tokens()
                refresh_attempted = True

    async def _ensure_access_token(self) -> None:
        session_config = self._require_session_config()
        if session_config.access_token:
            return
        if not session_config.refresh_token:
            self._invalidate_session()
            raise AuthenticationExpiredError(msgCode=0)
        await self._refresh_session_tokens()

    async def _refresh_session_tokens(self) -> None:
        session_config = self._require_session_config()
        if not session_config.refresh_token:
            self._invalidate_session()
            raise AuthenticationExpiredError(msgCode=0)

        try:
            refreshed_state = await refresh_access_token(
                sso_url=session_config.sso_url,
                refresh_token=session_config.refresh_token,
                client_id=self._settings.oauth_client_id,
                client_secret=self._settings.oauth_client_secret,
                request_timeout_seconds=self._settings.request_timeout_seconds,
            )
        except AuthenticationExpiredError:
            self._invalidate_session()
            raise

        self._session_config = replace(
            session_config,
            access_token=refreshed_state.access_token,
            refresh_token=refreshed_state.refresh_token or session_config.refresh_token,
        )
        self._persist_session_state(self._session_config)

    def _invalidate_session(self) -> None:
        self._session_config = None
        self._token_store.clear()

    def _persist_session_state(self, session_config: SessionConfig) -> None:
        self._token_store.save(
            access_token=session_config.access_token,
            refresh_token=session_config.refresh_token,
            gateway_url=session_config.gateway_url,
            sso_url=session_config.sso_url,
            wss_url=session_config.wss_url,
            auth_mode=session_config.auth_mode,
        )

    def _resolve_auth_mode(
        self,
        *,
        access_token: str | None,
        refresh_token: str | None,
    ) -> AuthMode:
        if access_token or refresh_token:
            return "token"
        raise SessionNotConfiguredError()

    def _serialize_device(self, device: BluettiDevice) -> DevicePayload:
        return DevicePayload(
            deviceId=device.device_id,
            sn=device.sn,
            name=device.name,
            model=device.model,
            manufacturer=device.manufacturer,
            online=device.online,
            batteryLevel=device.battery_level,
            states=[
                DeviceStatePayload(
                    fnCode=state.fn_code,
                    fnName=state.fn_name,
                    fnValue=state.fn_value,
                    fnType=state.fn_type,
                    displayValue=state.get_name_for_value(),
                    sensorInfo=state.sensor_info,
                )
                for state in device.states
            ],
        )

    def _product_client(self):
        return _ProductClientContext(self)


class _ProductClientContext:
    def __init__(self, service: BackendService) -> None:
        self._service = service
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> ProductClient:
        session_config = self._service._require_session_config()
        self._session = aiohttp.ClientSession()
        return ProductClient(
            httpSession=self._session,
            accessToken=session_config.access_token,
            application_profile=self._service._create_profile(),
            request_timeout_seconds=self._service._settings.request_timeout_seconds,
        )

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._session is not None:
            await self._session.close()