from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
import secrets
import time
from urllib.parse import urlparse
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
from .errors import DeviceNotFoundError, InvalidCommandError, LiveVerificationPrerequisiteError, SessionNotConfiguredError
from .live_updates import LiveUpdateEvent, LiveUpdatesManager
from .schemas import (
    AuthMode,
    DeviceCommandResponse,
    DeviceListResponse,
    DevicePayload,
    DeviceRefreshResponse,
    DeviceStatePayload,
    LiveAccountVerificationCheck,
    LiveAccountVerificationResponse,
    SessionSnapshot,
    SessionSetupRequest,
)
from .token_store import LocalTokenStore


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
    def __init__(self, settings: Settings, live_updates: LiveUpdatesManager | None = None) -> None:
        self._settings = settings
        self._token_store = LocalTokenStore(settings.token_store)
        self._pending_oauth_flows: dict[str, PendingOAuthFlow] = {}
        self._live_updates = live_updates or LiveUpdatesManager()
        self._session_config = self._load_initial_session_config()
        self._sync_live_updates()

    def get_session_snapshot(self) -> SessionSnapshot:
        live_updates = self._live_updates.snapshot()
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
                liveUpdates=SessionSnapshot.LiveUpdateSnapshot(
                    configured=live_updates.configured,
                    status=live_updates.status,
                    lastError=live_updates.lastError,
                ),
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
            liveUpdates=SessionSnapshot.LiveUpdateSnapshot(
                configured=live_updates.configured,
                status=live_updates.status,
                lastError=live_updates.lastError,
            ),
        )

    def shutdown(self) -> None:
        self._live_updates.shutdown()

    async def stream_live_updates(self) -> AsyncIterator[LiveUpdateEvent]:
        subscriber_id, queue = self._live_updates.subscribe()
        try:
            while True:
                yield await queue.get()
        finally:
            self._live_updates.unsubscribe(subscriber_id)

    async def verify_live_account(self) -> LiveAccountVerificationResponse:
        missing_prerequisites = self._missing_live_prerequisites()
        if missing_prerequisites:
            raise LiveVerificationPrerequisiteError(missing=missing_prerequisites)

        checks: list[LiveAccountVerificationCheck] = []

        auth_check = await self._verify_auth_stage()
        checks.append(auth_check)
        if auth_check.status == "failed":
            return LiveAccountVerificationResponse(ok=False, checks=checks)

        devices_check = await self._verify_devices_stage()
        checks.append(devices_check)
        if devices_check.status == "failed":
            return LiveAccountVerificationResponse(ok=False, checks=checks)

        live_updates_check = self._verify_live_updates_stage()
        checks.append(live_updates_check)
        return LiveAccountVerificationResponse(
            ok=all(check.status == "passed" for check in checks),
            checks=checks,
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

    def _missing_live_prerequisites(self) -> list[str]:
        missing: list[str] = []
        if not self._settings.enable_live_account_verification:
            missing.append("BLUETTI_ENABLE_LIVE_ACCOUNT_VERIFICATION")

        session_config = self._session_config
        if session_config is None:
            missing.append("configured-session")
        else:
            if not (session_config.access_token or session_config.refresh_token):
                missing.append("account-token")

            if not self._is_wss_url(session_config.wss_url):
                missing.append("authenticated-wss-url")
        return missing

    async def _verify_auth_stage(self) -> LiveAccountVerificationCheck:
        return await self._verify_stage(
            stage="auth",
            operation=self._ensure_access_token,
            success_code="AUTH_READY",
            success_message="Backend session authentication is ready for live verification.",
            not_configured_message="Configure a BLUETTI session before running live-account verification.",
            expired_message="Live-account verification could not refresh the BLUETTI session.",
            cloud_error_message="BLUETTI cloud rejected the authentication verification request.",
            timeout_message="Authentication verification timed out while calling BLUETTI cloud.",
            connectivity_message="Authentication verification could not reach BLUETTI cloud.",
        )

    async def _verify_devices_stage(self) -> LiveAccountVerificationCheck:
        return await self._verify_stage(
            stage="devices",
            operation=self.list_devices,
            success_code="DEVICES_QUERIED",
            success_message="Device discovery succeeded for the current live account session.",
            not_configured_message="Configure a BLUETTI session before running device verification.",
            expired_message="Device verification failed because the BLUETTI session expired.",
            cloud_error_message="BLUETTI cloud rejected the device verification request.",
            timeout_message="Device verification timed out while calling BLUETTI cloud.",
            connectivity_message="Device verification could not reach BLUETTI cloud.",
            success_details=lambda payload: {"deviceCount": payload.count},
        )

    async def _verify_stage(
        self,
        *,
        stage: str,
        operation: Callable[[], Awaitable[T]],
        success_code: str,
        success_message: str,
        not_configured_message: str,
        expired_message: str,
        cloud_error_message: str,
        timeout_message: str,
        connectivity_message: str,
        success_details: Callable[[T], dict[str, object]] | None = None,
    ) -> LiveAccountVerificationCheck:
        try:
            result = await operation()
            return LiveAccountVerificationCheck(
                stage=stage,
                status="passed",
                code=success_code,
                message=success_message,
                details=success_details(result) if success_details is not None else None,
            )
        except SessionNotConfiguredError:
            return LiveAccountVerificationCheck(
                stage=stage,
                status="failed",
                code="SESSION_NOT_CONFIGURED",
                message=not_configured_message,
            )
        except AuthenticationExpiredError:
            return LiveAccountVerificationCheck(
                stage=stage,
                status="failed",
                code="AUTHENTICATION_EXPIRED",
                message=expired_message,
            )
        except ApplicationRuntimeException as exc:
            return LiveAccountVerificationCheck(
                stage=stage,
                status="failed",
                code="BLUETTI_CLOUD_ERROR",
                message=cloud_error_message,
                details={"upstreamCode": exc.msgCode},
            )
        except asyncio.TimeoutError:
            return LiveAccountVerificationCheck(
                stage=stage,
                status="failed",
                code="BLUETTI_TIMEOUT",
                message=timeout_message,
            )
        except aiohttp.ClientError:
            return LiveAccountVerificationCheck(
                stage=stage,
                status="failed",
                code="BLUETTI_CONNECTIVITY_ERROR",
                message=connectivity_message,
            )

    def _verify_live_updates_stage(self) -> LiveAccountVerificationCheck:
        snapshot = self._live_updates.snapshot()
        if snapshot.status == "connected":
            return LiveAccountVerificationCheck(
                stage="live-updates",
                status="passed",
                code="LIVE_UPDATES_CONNECTED",
                message="Live updates are connected for the authenticated session.",
                details={"status": "connected"},
            )

        if snapshot.status == "degraded":
            return LiveAccountVerificationCheck(
                stage="live-updates",
                status="failed",
                code="LIVE_UPDATES_DEGRADED",
                message="Live updates are degraded for the authenticated session.",
                details={"status": "degraded", "reason": self._sanitize_text(snapshot.lastError or "unknown")},
            )

        return LiveAccountVerificationCheck(
            stage="live-updates",
            status="failed",
            code="LIVE_UPDATES_UNAVAILABLE",
            message="Live updates are unavailable for the current session.",
            details={"status": "unavailable"},
        )

    def _sanitize_text(self, value: str) -> str:
        sanitized = value
        for secret in self._secret_values():
            if not secret:
                continue
            sanitized = sanitized.replace(secret, "[redacted]")
        return sanitized

    def _secret_values(self) -> list[str]:
        session_config = self._session_config
        values = [
            self._settings.access_token,
            self._settings.refresh_token,
            self._settings.oauth_client_secret,
        ]
        if session_config is not None:
            values.extend(
                [
                    session_config.access_token,
                    session_config.refresh_token,
                ]
            )
        return [value for value in values if value]

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
            device.merge_states(status_device.states)

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
        self._sync_live_updates()

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
        self._sync_live_updates()

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
        self._live_updates.shutdown()

    def _sync_live_updates(self) -> None:
        if self._session_config is None:
            self._live_updates.shutdown()
            return

        self._live_updates.configure(
            access_token=self._session_config.access_token,
            wss_url=self._session_config.wss_url,
        )

    @staticmethod
    def _is_wss_url(value: str | None) -> bool:
        if not value:
            return False
        return urlparse(value).scheme.lower() == "wss"

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

    @asynccontextmanager
    async def _product_client(self) -> AsyncIterator[ProductClient]:
        session_config = self._require_session_config()
        async with aiohttp.ClientSession() as session:
            yield ProductClient(
                httpSession=session,
                accessToken=session_config.access_token,
                application_profile=self._create_profile(),
                request_timeout_seconds=self._settings.request_timeout_seconds,
            )