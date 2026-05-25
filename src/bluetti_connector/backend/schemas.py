from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SessionSetupRequest(BaseModel):
    accessToken: str = Field(min_length=1)
    ssoUrl: str | None = None
    gatewayUrl: str | None = None
    wssUrl: str | None = None


class DeviceCommandRequest(BaseModel):
    fnCode: str = Field(min_length=1)
    fnValue: str = Field(min_length=1)


class SessionSnapshot(BaseModel):
    configured: bool
    source: str | None = None
    hasAccessToken: bool
    cloud: dict[str, str]


class DeviceStatePayload(BaseModel):
    fnCode: str
    fnName: str
    fnValue: str | None
    fnType: str | None
    displayValue: str
    sensorInfo: dict[str, Any]


class DevicePayload(BaseModel):
    deviceId: str
    sn: str
    name: str
    model: str | None
    manufacturer: str
    online: bool
    batteryLevel: int
    states: list[DeviceStatePayload]


class DeviceListResponse(BaseModel):
    count: int
    items: list[DevicePayload]


class DeviceRefreshResponse(BaseModel):
    item: DevicePayload


class DeviceCommandResponse(BaseModel):
    accepted: bool
    device: DevicePayload