from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
import secrets
import time
from typing import TypeVar
from urllib.parse import urlencode

import aiohttp

from ..config import Settings
from ..core import (
    ApplicationProfile,
    ApplicationRuntimeException,
    AuthenticationExpiredError,
    BluettiData,
    BluettiDevice,
    ProductClient,
)
from .auth import build_authorize_url, exchange_authorization_code, refresh_access_token
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


@dataclass(frozen=True)
class PendingOAuthFlow:
    state_token: str
    redirect_uri: str
    sso_url: str
    gateway_url: str
    wss_url: str
    expires_at: float


class BackendService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._token_store = LocalTokenStore(settings.token_store)
        self._pending_oauth_flows: dict[str, PendingOAuthFlow] = {}
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
        self._set_session_config(
            access_token=payload.accessToken,
            refresh_token=payload.refreshToken,
            sso_url=payload.ssoUrl or self._settings.cloud_sso_url,
            gateway_url=payload.gatewayUrl or self._settings.cloud_gateway_url,
            wss_url=payload.wssUrl or self._settings.cloud_wss_url,
            source="request",
        )
        return self.get_session_snapshot()

    def begin_browser_oauth(self, *, redirect_uri: str) -> str:
        self._prune_pending_oauth_flows()
        state_token = secrets.token_urlsafe(32)
        sso_url = self._settings.cloud_sso_url
        gateway_url = self._settings.cloud_gateway_url
        wss_url = self._settings.cloud_wss_url
        self._pending_oauth_flows[state_token] = PendingOAuthFlow(
            state_token=state_token,
            redirect_uri=redirect_uri,
            sso_url=sso_url,
            gateway_url=gateway_url,
            wss_url=wss_url,
            expires_at=time.time() + self._settings.oauth_state_ttl_seconds,
        )
        return build_authorize_url(
            sso_url=sso_url,
            client_id=self._settings.oauth_client_id,
            redirect_uri=redirect_uri,
            state=state_token,
        )

    async def complete_browser_oauth_callback(
        self,
        *,
        state_token: str | None,
        code: str | None,
        error: str | None,
    ) -> str:
        self._prune_pending_oauth_flows()
        pending_flow = self._consume_pending_oauth_flow(state_token)
        if pending_flow is None:
            return self._oauth_redirect_location(reason="invalid_state")

        if error:
            return self._oauth_redirect_location(reason=self._sanitize_oauth_error(error))
        if not code:
            return self._oauth_redirect_location(reason="missing_code")

        try:
            granted_state = await exchange_authorization_code(
                sso_url=pending_flow.sso_url,
                code=code,
                redirect_uri=pending_flow.redirect_uri,
                client_id=self._settings.oauth_client_id,
                client_secret=self._settings.oauth_client_secret,
                request_timeout_seconds=self._settings.request_timeout_seconds,
            )
        except (ApplicationRuntimeException, AuthenticationExpiredError):
            return self._oauth_redirect_location(reason="exchange_failed")

        self._set_session_config(
            access_token=granted_state.access_token,
            refresh_token=granted_state.refresh_token,
            sso_url=pending_flow.sso_url,
            gateway_url=pending_flow.gateway_url,
            wss_url=pending_flow.wss_url,
            source="oauth",
        )
        return self._oauth_redirect_location(reason=None)

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
        products_response, status_response = await asyncio.gather(
            client.get_user_products(),
            client.get_device_status(device_sn),
        )

        status_products = list(status_response.data or [])
        if status_products and status_products[0].isBindByCurUser == "0":
            bind_result = await client.bind_devices({"bindSnList": [device_sn]})
            if not bind_result.is_ok():
                raise ApplicationRuntimeException(msgCode=bind_result.msgCode, data=bind_result.data)
            status_response = await client.get_device_status(device_sn)

        product_device = BluettiData(products_response.data or []).get_device_by_sn(device_sn)
        status_device = BluettiData(status_response.data or []).get_device_by_sn(device_sn)

        device = product_device or status_device
        if device is None:
            raise DeviceNotFoundError(device_sn)

        if status_device is not None and device is not status_device:
            device.on_line = status_device.on_line or device.on_line
            device.name = status_device.name or device.name
            device.model = status_device.model or device.model
            device._merge_states(
                [
                    {
                        "fnCode": state.fn_code,
                        "fnName": state.fn_name,
                        "fnValue": state.fn_value,
                        "fnType": state.fn_type,
                        "supportModeValues": state.support_mode_values,
                        "sensorInfo": state.sensor_info,
                    }
                    for state in status_device.states
                ]
            )

        device.api_client = client
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

    def _set_session_config(
        self,
        *,
        access_token: str | None,
        refresh_token: str | None,
        sso_url: str,
        gateway_url: str,
        wss_url: str,
        source: str,
        uses_stored_session: bool = False,
    ) -> None:
        self._session_config = SessionConfig(
            access_token=access_token,
            refresh_token=refresh_token,
            sso_url=sso_url,
            gateway_url=gateway_url,
            wss_url=wss_url,
            source=source,
            auth_mode=self._resolve_auth_mode(
                access_token=access_token,
                refresh_token=refresh_token,
            ),
            uses_stored_session=uses_stored_session,
        )
        self._persist_session_state(self._session_config)

    def _prune_pending_oauth_flows(self) -> None:
        now = time.time()
        self._pending_oauth_flows = {
            key: flow for key, flow in self._pending_oauth_flows.items() if flow.expires_at > now
        }

    def _consume_pending_oauth_flow(self, state_token: str | None) -> PendingOAuthFlow | None:
        if not state_token:
            return None
        return self._pending_oauth_flows.pop(state_token, None)

    def _oauth_redirect_location(self, *, reason: str | None) -> str:
        if reason is None:
            return "/?oauth=success"
        return f"/?{urlencode({'oauth': 'error', 'oauth_reason': reason})}"

    def _sanitize_oauth_error(self, error: str) -> str:
        if error == "access_denied":
            return "access_denied"
        return "oauth_failed"

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
            states=[self._serialize_state(state) for state in device.states],
        )

    def _serialize_state(self, state) -> DeviceStatePayload:
        control_kind = state.control_kind()
        control = None
        if control_kind is not None:
            control = DeviceStatePayload.ControlPayload(
                kind=control_kind,
                allowedValues=[
                    DeviceStatePayload.ControlOption(
                        value=option["value"],
                        label=option["label"],
                    )
                    for option in state.allowed_values()
                ],
            )

        return DeviceStatePayload(
            fnCode=state.fn_code,
            fnName=state.fn_name,
            fnValue=state.fn_value,
            fnType=state.fn_type,
            displayValue=state.get_name_for_value(),
            sensorInfo=state.sensor_info,
            control=control,
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