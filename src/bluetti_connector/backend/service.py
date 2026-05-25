from __future__ import annotations

from dataclasses import dataclass

import aiohttp

from ..config import Settings
from ..core import ApplicationProfile, BluettiData, BluettiDevice, ProductClient
from .errors import DeviceNotFoundError, InvalidCommandError, SessionNotConfiguredError
from .schemas import (
    DeviceCommandResponse,
    DeviceListResponse,
    DevicePayload,
    DeviceRefreshResponse,
    DeviceStatePayload,
    SessionSnapshot,
    SessionSetupRequest,
)


@dataclass
class SessionConfig:
    access_token: str
    sso_url: str
    gateway_url: str
    wss_url: str
    source: str


class BackendService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._session_config: SessionConfig | None = None
        if settings.access_token:
            self._session_config = SessionConfig(
                access_token=settings.access_token,
                sso_url=settings.cloud_sso_url,
                gateway_url=settings.cloud_gateway_url,
                wss_url=settings.cloud_wss_url,
                source="settings",
            )

    def get_session_snapshot(self) -> SessionSnapshot:
        if self._session_config is None:
            return SessionSnapshot(
                configured=False,
                source=None,
                hasAccessToken=False,
                cloud={
                    "ssoUrl": self._settings.cloud_sso_url,
                    "gatewayUrl": self._settings.cloud_gateway_url,
                    "wssUrl": self._settings.cloud_wss_url,
                },
            )

        return SessionSnapshot(
            configured=True,
            source=self._session_config.source,
            hasAccessToken=bool(self._session_config.access_token),
            cloud={
                "ssoUrl": self._session_config.sso_url,
                "gatewayUrl": self._session_config.gateway_url,
                "wssUrl": self._session_config.wss_url,
            },
        )

    def configure_session(self, payload: SessionSetupRequest) -> SessionSnapshot:
        self._session_config = SessionConfig(
            access_token=payload.accessToken,
            sso_url=payload.ssoUrl or self._settings.cloud_sso_url,
            gateway_url=payload.gatewayUrl or self._settings.cloud_gateway_url,
            wss_url=payload.wssUrl or self._settings.cloud_wss_url,
            source="request",
        )
        return self.get_session_snapshot()

    async def list_devices(self) -> DeviceListResponse:
        async with self._product_client() as client:
            products = await client.get_user_products()
            devices = BluettiData(products.data or [])
            return DeviceListResponse(count=len(devices.devices), items=[self._serialize_device(device) for device in devices.devices])

    async def refresh_device(self, device_sn: str) -> DeviceRefreshResponse:
        async with self._product_client() as client:
            device = await self._load_device(client, device_sn)
            return DeviceRefreshResponse(item=self._serialize_device(device))

    async def execute_command(self, device_sn: str, fn_code: str, fn_value: str) -> DeviceCommandResponse:
        async with self._product_client() as client:
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