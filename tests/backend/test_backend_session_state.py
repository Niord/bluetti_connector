from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from bluetti_connector.backend.schemas import SessionSetupRequest
from bluetti_connector.backend.service import BackendService
from bluetti_connector.config import Settings


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

    service = BackendService(settings)

    snapshot = service.get_session_snapshot()

    assert snapshot.configured is True
    assert snapshot.source == "store"
    assert snapshot.authMode == "token"
    assert snapshot.usesStoredSession is True
    assert snapshot.hasAccessToken is True
    assert snapshot.hasRefreshToken is True
    assert snapshot.cloud["gatewayUrl"] == "https://stored-gateway.example"


def test_configure_session_persists_token_request_state(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    service = BackendService(settings)

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
    assert persisted["accessToken"] == "request-access-token"
    assert persisted["refreshToken"] == "request-refresh-token"
    assert persisted["gatewayUrl"] == "https://request-gateway.example"


def test_configure_session_with_refresh_only_request_persists_token_store(tmp_path: Path) -> None:
    token_store = tmp_path / "tokens.json"
    settings = _make_settings(tmp_path)
    service = BackendService(settings)

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
    assert persisted["refreshToken"] == "refresh-only-token"


def test_session_setup_request_rejects_missing_auth_inputs() -> None:
    with pytest.raises(ValidationError):
        SessionSetupRequest()