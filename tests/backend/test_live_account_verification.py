from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from bluetti_connector.backend.app import create_app
from bluetti_connector.backend.errors import LiveVerificationPrerequisiteError
from bluetti_connector.backend.live_updates import LiveUpdatesSnapshot
from bluetti_connector.backend.schemas import DeviceListResponse
from bluetti_connector.backend.service import BackendService
from bluetti_connector.config import Settings


class StubLiveUpdatesManager:
    def __init__(self, snapshot: LiveUpdatesSnapshot | None = None) -> None:
        self._snapshot = snapshot or LiveUpdatesSnapshot(configured=True, status="connected", lastError=None)

    def configure(self, *, access_token: str | None, wss_url: str | None) -> None:
        if access_token and wss_url and wss_url.startswith("wss://"):
            self._snapshot = LiveUpdatesSnapshot(configured=True, status="connected", lastError=None)
            return
        self._snapshot = LiveUpdatesSnapshot(configured=False, status="disabled", lastError=None)

    def snapshot(self) -> LiveUpdatesSnapshot:
        return self._snapshot

    def shutdown(self) -> None:
        self._snapshot = LiveUpdatesSnapshot(configured=False, status="disabled", lastError=None)


def _make_settings(tmp_path: Path, **overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "token_store_path": str(tmp_path / "tokens.json"),
        "dev_reload": False,
    }
    defaults.update(overrides)
    return Settings(**defaults)


@pytest.mark.asyncio
async def test_live_verification_fails_fast_on_prerequisites_without_cloud_calls(tmp_path: Path) -> None:
    settings = _make_settings(
        tmp_path,
        enable_live_account_verification=False,
        access_token="live-access-token",
        refresh_token="live-refresh-token",
        cloud_wss_url="wss://gw.example/ws",
    )
    service = BackendService(settings, live_updates=StubLiveUpdatesManager())

    auth_attempted = False
    devices_attempted = False

    async def fake_ensure_access_token() -> None:
        nonlocal auth_attempted
        auth_attempted = True

    async def fake_list_devices() -> DeviceListResponse:
        nonlocal devices_attempted
        devices_attempted = True
        return DeviceListResponse(count=0, items=[])

    service._ensure_access_token = fake_ensure_access_token  # type: ignore[method-assign]
    service.list_devices = fake_list_devices  # type: ignore[method-assign]

    with pytest.raises(LiveVerificationPrerequisiteError) as error_info:
        await service.verify_live_account()

    assert error_info.value.code == "LIVE_VERIFICATION_PREREQUISITES_MISSING"
    assert error_info.value.details == {
        "missing": ["BLUETTI_ENABLE_LIVE_ACCOUNT_VERIFICATION"],
    }
    assert auth_attempted is False
    assert devices_attempted is False


@pytest.mark.asyncio
async def test_live_verification_endpoint_reports_sanitized_staged_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BLUETTI_ENABLE_LIVE_ACCOUNT_VERIFICATION", "true")
    monkeypatch.setenv("BLUETTI_ACCESS_TOKEN", "live-access-token")
    monkeypatch.setenv("BLUETTI_REFRESH_TOKEN", "live-refresh-token")
    monkeypatch.setenv("BLUETTI_CLOUD_WSS_URL", "wss://gw.example/ws")

    app = create_app()
    service = app.state.backend_service

    async def fake_ensure_access_token() -> None:
        return None

    async def fake_list_devices() -> DeviceListResponse:
        return DeviceListResponse(count=1, items=[])

    service._ensure_access_token = fake_ensure_access_token  # type: ignore[method-assign]
    service.list_devices = fake_list_devices  # type: ignore[method-assign]
    service._live_updates._handle_error(Exception("live-refresh-token verification failed"))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/verification/live-account")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert [check["stage"] for check in payload["checks"]] == ["auth", "devices", "live-updates"]
    assert payload["checks"][2]["code"] == "LIVE_UPDATES_DEGRADED"
    text_payload = json.dumps(payload)
    assert "live-refresh-token" not in text_payload
    assert "live-access-token" not in text_payload


@pytest.mark.asyncio
async def test_live_verification_endpoint_reports_prerequisite_error() -> None:
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/verification/live-account")

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "LIVE_VERIFICATION_PREREQUISITES_MISSING",
            "message": "Live-account verification prerequisites are not satisfied.",
            "details": {
                "missing": [
                    "BLUETTI_ENABLE_LIVE_ACCOUNT_VERIFICATION",
                    "configured-session",
                ]
            },
        }
    }