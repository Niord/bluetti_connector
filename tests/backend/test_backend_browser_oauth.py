from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from aiohttp import web
from httpx import ASGITransport, AsyncClient

from bluetti_connector.backend.app import create_app


@pytest.fixture
async def fake_oauth_gateway() -> AsyncIterator[tuple[str, dict[str, Any]]]:
    state = {"token_requests": []}

    async def token_handler(request: web.Request) -> web.Response:
        payload = dict(await request.post())
        state["token_requests"].append(payload)

        if payload.get("grant_type") != "authorization_code":
            return web.json_response({"error": "unsupported_grant_type"}, status=400)
        if payload.get("code") != "valid-browser-code":
            return web.json_response({"error": "invalid_grant"}, status=400)

        return web.json_response(
            {
                "access_token": "browser-access-token",
                "refresh_token": "browser-refresh-token",
                "expires_in": 3600,
                "created_at": 1716681600,
                "token_type": "Bearer",
            }
        )

    app = web.Application()
    app.router.add_post("/sso/oauth2/token", token_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    sockets = site._server.sockets
    port = sockets[0].getsockname()[1]

    try:
        yield f"http://127.0.0.1:{port}", state
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_browser_oauth_start_redirects_to_authorize_url(
    fake_oauth_gateway: tuple[str, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_url, _ = fake_oauth_gateway
    monkeypatch.setenv("BLUETTI_CLOUD_SSO_URL", f"{base_url}/sso")
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/session/oauth/start", follow_redirects=False)

    assert response.status_code == 307
    location = response.headers["location"]
    parsed = urlparse(location)
    params = parse_qs(parsed.query)

    assert parsed.path == "/sso/oauth2/grant"
    assert params["response_type"] == ["code"]
    assert params["client_id"] == ["HomeAssistant"]
    assert params["redirect_uri"] == ["http://testserver/api/session/oauth/callback"]
    assert len(params["state"][0]) > 20


@pytest.mark.asyncio
async def test_browser_oauth_start_uses_configured_cloud_urls_not_stale_session_urls(
    fake_oauth_gateway: tuple[str, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_url, _ = fake_oauth_gateway
    monkeypatch.setenv("BLUETTI_CLOUD_SSO_URL", f"{base_url}/sso")
    monkeypatch.setenv("BLUETTI_CLOUD_GATEWAY_URL", "https://gw.live-bluetti.example")
    monkeypatch.setenv("BLUETTI_CLOUD_WSS_URL", "wss://gw.live-bluetti.example/ws")
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        session_response = await client.post(
            "/api/session",
            json={
                "accessToken": "stale-session-token",
                "ssoUrl": "http://127.0.0.1:59999/sso",
                "gatewayUrl": "http://127.0.0.1:59999",
                "wssUrl": "ws://127.0.0.1:59999/ws",
            },
        )
        assert session_response.status_code == 200

        response = await client.get("/api/session/oauth/start", follow_redirects=False)

    assert response.status_code == 307
    location = response.headers["location"]
    parsed = urlparse(location)
    assert parsed.path == "/sso/oauth2/grant"
    assert parsed.netloc == urlparse(base_url).netloc


@pytest.mark.asyncio
async def test_browser_oauth_callback_exchanges_code_and_configures_session(
    fake_oauth_gateway: tuple[str, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    base_url, oauth_state = fake_oauth_gateway
    monkeypatch.setenv("BLUETTI_CLOUD_SSO_URL", f"{base_url}/sso")
    monkeypatch.setenv("BLUETTI_CLOUD_GATEWAY_URL", "https://gw.browser-oauth.example")
    monkeypatch.setenv("BLUETTI_CLOUD_WSS_URL", "wss://gw.browser-oauth.example/ws")
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        start_response = await client.get("/api/session/oauth/start", follow_redirects=False)
        state_token = parse_qs(urlparse(start_response.headers["location"]).query)["state"][0]

        callback_response = await client.get(
            "/api/session/oauth/callback",
            params={"state": state_token, "code": "valid-browser-code"},
            follow_redirects=False,
        )
        assert callback_response.status_code == 303
        assert callback_response.headers["location"] == "/?oauth=success"

        session_response = await client.get("/api/session")

    assert session_response.status_code == 200
    assert session_response.json()["configured"] is True
    assert session_response.json()["source"] == "oauth"
    assert session_response.json()["hasAccessToken"] is True
    assert session_response.json()["hasRefreshToken"] is True
    assert oauth_state["token_requests"][0]["redirect_uri"] == "http://testserver/api/session/oauth/callback"

    persisted = json.loads((tmp_path / "tokens.json").read_text())
    assert persisted["accessToken"] == "browser-access-token"
    assert persisted["refreshToken"] == "browser-refresh-token"


@pytest.mark.asyncio
async def test_browser_oauth_callback_rejects_invalid_state() -> None:
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        callback_response = await client.get(
            "/api/session/oauth/callback",
            params={"state": "missing-state", "code": "valid-browser-code"},
            follow_redirects=False,
        )
        session_response = await client.get("/api/session")

    assert callback_response.status_code == 303
    assert callback_response.headers["location"] == "/?oauth=error&oauth_reason=invalid_state"
    assert session_response.status_code == 200
    assert session_response.json()["configured"] is False