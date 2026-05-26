from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from bluetti_connector.backend.live_updates import LiveUpdatesSnapshot
from bluetti_connector.backend.schemas import SessionSetupRequest
from bluetti_connector.backend.service import BackendService
from bluetti_connector.config import Settings


class RecordingLiveUpdatesManager:
    def __init__(self) -> None:
        self.calls: list[tuple[str | None, str | None]] = []
        self._snapshot = LiveUpdatesSnapshot(configured=False, status="disabled", lastError=None)

    def configure(self, *, access_token: str | None, wss_url: str | None) -> None:
        self.calls.append((access_token, wss_url))
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


def test_session_snapshot_prefers_stored_token_state(tmp_path: Path) -> None:
    token_store = tmp_path / "tokens.json"
    token_store.write_text(
        json.dumps(
            {
                "accessToken": "stored-access-token",
                "refreshToken": "stored-refresh-token",
                "gatewayUrl": "https://stored-gateway.example",
                "ssoUrl": "https://stored-sso.example",
                "wssUrl": "wss://stored-wss.example/ws",
                "authMode": "token",
                "updatedAt": "2026-05-26T00:00:00+00:00",
            }
        )
    )
    settings = _make_settings(
        tmp_path,
        access_token="settings-access-token",
        refresh_token="settings-refresh-token",
    )

    live_updates = RecordingLiveUpdatesManager()
    service = BackendService(settings, live_updates=live_updates)

    snapshot = service.get_session_snapshot()

    assert snapshot.configured is True
    assert snapshot.source == "store"
    assert snapshot.authMode == "token"
    assert snapshot.usesStoredSession is True
    assert snapshot.hasAccessToken is True
    assert snapshot.hasRefreshToken is True
    assert snapshot.cloud["gatewayUrl"] == "https://stored-gateway.example"
    assert snapshot.liveUpdates.status == "connected"
    assert live_updates.calls == [("stored-access-token", "wss://stored-wss.example/ws")]


def test_configure_session_persists_token_request_state(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    live_updates = RecordingLiveUpdatesManager()
    service = BackendService(settings, live_updates=live_updates)

    snapshot = service.configure_session(
        SessionSetupRequest(
            accessToken="request-access-token",
            refreshToken="request-refresh-token",
            gatewayUrl="https://request-gateway.example",
            ssoUrl="https://request-sso.example",
            wssUrl="wss://request-wss.example/ws",
        )
    )

    persisted = json.loads((tmp_path / "tokens.json").read_text())
    assert snapshot.source == "request"
    assert snapshot.authMode == "token"
    assert snapshot.usesStoredSession is False
    assert snapshot.hasAccessToken is True
    assert snapshot.hasRefreshToken is True
    assert snapshot.liveUpdates.status == "connected"
    assert persisted["accessToken"] == "request-access-token"
    assert persisted["refreshToken"] == "request-refresh-token"
    assert persisted["gatewayUrl"] == "https://request-gateway.example"
    assert live_updates.calls[-1] == ("request-access-token", "wss://request-wss.example/ws")


def test_configure_session_with_refresh_only_request_persists_token_store(tmp_path: Path) -> None:
    token_store = tmp_path / "tokens.json"
    settings = _make_settings(tmp_path)
    live_updates = RecordingLiveUpdatesManager()
    service = BackendService(settings, live_updates=live_updates)

    snapshot = service.configure_session(
        SessionSetupRequest(
            refreshToken="refresh-only-token",
        )
    )

    persisted = json.loads(token_store.read_text())
    assert snapshot.source == "request"
    assert snapshot.authMode == "token"
    assert snapshot.hasAccessToken is False
    assert snapshot.hasRefreshToken is True
    assert snapshot.usesStoredSession is False
    assert snapshot.liveUpdates.status == "disabled"
    assert persisted["refreshToken"] == "refresh-only-token"
    assert live_updates.calls[-1] == (None, settings.cloud_wss_url)


def test_session_setup_request_rejects_missing_auth_inputs() -> None:
    with pytest.raises(ValidationError):
        SessionSetupRequest()