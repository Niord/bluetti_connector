from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


AuthMode = Literal["token", "credentials"]
DeviceControlKind = Literal["switch", "select"]
LiveUpdateStatus = Literal["disabled", "connecting", "connected", "degraded"]


class SessionSetupRequest(BaseModel):
    accessToken: str | None = Field(default=None, min_length=1)
    refreshToken: str | None = Field(default=None, min_length=1)
    ssoUrl: str | None = None
    gatewayUrl: str | None = None
    wssUrl: str | None = None

    @model_validator(mode="after")
    def validate_auth_fields(self) -> "SessionSetupRequest":
        has_token_input = bool(self.accessToken or self.refreshToken)

        if not has_token_input:
            raise ValueError("Provide an access token or refresh token.")

        return self


class DeviceCommandRequest(BaseModel):
    fnCode: str = Field(min_length=1)
    fnValue: str = Field(min_length=1)


class SessionSnapshot(BaseModel):
    class LiveUpdateSnapshot(BaseModel):
        configured: bool
        status: LiveUpdateStatus
        lastError: str | None = None

    configured: bool
    source: str | None = None
    authMode: AuthMode | None = None
    usesStoredSession: bool = False
    hasAccessToken: bool
    hasRefreshToken: bool = False
    cloud: dict[str, str]
    liveUpdates: LiveUpdateSnapshot


class DeviceStatePayload(BaseModel):
    class ControlOption(BaseModel):
        value: str
        label: str

    class ControlPayload(BaseModel):
        kind: DeviceControlKind
        allowedValues: list["DeviceStatePayload.ControlOption"]

    fnCode: str
    fnName: str
    fnValue: str | None
    fnType: str | None
    displayValue: str
    sensorInfo: dict[str, Any]
    control: ControlPayload | None = None


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