from __future__ import annotations

from collections.abc import AsyncIterator
from copy import deepcopy
import json
from typing import Any

import pytest
from aiohttp import web
from httpx import ASGITransport, AsyncClient

from bluetti_connector.backend.app import create_app


DEVICE_SN = "AC200L-TEST-001"
CONTROL_CODE = "AC_OUTPUT_ON"


@pytest.fixture
async def fake_bluetti_gateway() -> AsyncIterator[tuple[str, dict[str, Any]]]:
    state = {
        "device": {
            "sn": DEVICE_SN,
            "online": "0",
            "model": "AC200L",
            "name": "Workshop Battery",
            "isBindByCurUser": "1",
            "stateList": [
                {
                    "fnCode": CONTROL_CODE,
                    "fnName": "AC Output",
                    "fnValue": "0",
                    "fnType": "switch",
                    "supportModeValues": [],
                },
                {
                    "fnCode": "SOC",
                    "fnName": "Battery SOC",
                    "fnValue": "55",
                    "fnType": "number",
                    "supportModeValues": [],
                },
            ],
        },
        "status_device": None,
        "last_control": None,
        "bind_requests": [],
        "active_access_token": "test-access-token",
        "active_refresh_token": "test-refresh-token",
        "refresh_requests": [],
    }

    def token_expired_response() -> web.Response:
        return web.json_response(
            {
                "msgId": "auth-expired",
                "msgCode": 805,
                "data": None,
            }
        )

    def is_authorized(request: web.Request) -> bool:
        return request.headers.get("Authorization") == state["active_access_token"]

    async def devices_handler(request: web.Request) -> web.Response:
        if not is_authorized(request):
            return token_expired_response()
        return web.json_response(
            {
                "msgId": "devices",
                "msgCode": 0,
                "data": [deepcopy(state["device"])],
            }
        )

    async def device_states_handler(request: web.Request) -> web.Response:
        if not is_authorized(request):
            return token_expired_response()
        sns = request.query.get("sns")
        source_device = state["status_device"] or state["device"]
        devices = [deepcopy(source_device)]
        if sns:
            devices = [device for device in devices if device["sn"] == sns]
        return web.json_response(
            {
                "msgId": "deviceStates",
                "msgCode": 0,
                "data": devices,
            }
        )

    async def control_handler(request: web.Request) -> web.Response:
        if not is_authorized(request):
            return token_expired_response()
        source_device = state["status_device"] or state["device"]
        if source_device.get("isBindByCurUser") == "0":
            return web.json_response(
                {
                    "msgId": "fulfillment",
                    "msgCode": 403,
                    "data": {"reason": "device not bound"},
                }
            )
        payload = await request.json()
        state["last_control"] = payload
        for item in state["device"]["stateList"]:
            if item["fnCode"] == payload["fnCode"]:
                item["fnValue"] = payload["fnValue"]
                break
        return web.json_response(
            {
                "msgId": "fulfillment",
                "msgCode": 0,
                "data": {"accepted": True, "sn": payload["sn"]},
            }
        )

    async def token_handler(request: web.Request) -> web.Response:
        payload = dict(await request.post())
        state["refresh_requests"].append(payload)

        if payload.get("grant_type") != "refresh_token":
            return web.json_response({"error": "unsupported_grant_type"}, status=400)
        if payload.get("client_id") != "HomeAssistant" or payload.get("client_secret") != "SG9tZUFzc2lzdGFudA==":
            return web.json_response({"error": "unauthorized_client"}, status=401)
        if payload.get("refresh_token") != state["active_refresh_token"]:
            return web.json_response({"error": "invalid_grant"}, status=400)

        refresh_number = len(state["refresh_requests"])
        state["active_access_token"] = f"refreshed-access-token-{refresh_number}"
        state["active_refresh_token"] = f"refreshed-refresh-token-{refresh_number}"
        return web.json_response(
            {
                "access_token": state["active_access_token"],
                "refresh_token": state["active_refresh_token"],
                "expires_in": 3600,
                "created_at": 1716681600,
                "token_type": "Bearer",
            }
        )

    async def bind_devices_handler(request: web.Request) -> web.Response:
        if not is_authorized(request):
            return token_expired_response()
        payload = await request.json()
        state["bind_requests"].append(payload)

        bind_sn_list = payload.get("bindSnList") or []
        if DEVICE_SN in bind_sn_list:
            if state["status_device"] is None:
                state["status_device"] = deepcopy(state["device"])
            state["status_device"]["isBindByCurUser"] = "1"
            if not state["status_device"].get("stateList"):
                state["status_device"]["stateList"] = deepcopy(state["device"]["stateList"])

        return web.json_response(
            {
                "msgId": "bindDevices",
                "msgCode": 0,
                "data": {"accepted": True, "bindSnList": bind_sn_list},
            }
        )

    app = web.Application()
    app.router.add_get("/api/bluiotdata/ha/v1/devices", devices_handler)
    app.router.add_get("/api/bluiotdata/ha/v1/deviceStates", device_states_handler)
    app.router.add_post("/api/bluiotdata/ha/v1/fulfillment", control_handler)
    app.router.add_post("/api/bluiotdata/ha/v1/bindDevices", bind_devices_handler)
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
async def test_backend_smoke_flow(fake_bluetti_gateway: tuple[str, dict[str, Any]]) -> None:
    base_url, state = fake_bluetti_gateway
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        session_response = await client.post(
            "/api/session",
            json={
                "accessToken": "test-access-token",
                "ssoUrl": f"{base_url}/sso",
                "gatewayUrl": base_url,
                "wssUrl": "ws://127.0.0.1/unused",
            },
        )
        assert session_response.status_code == 200
        assert session_response.json()["configured"] is True

        devices_response = await client.get("/api/devices")
        assert devices_response.status_code == 200
        devices_payload = devices_response.json()
        assert devices_payload["count"] == 1
        assert devices_payload["items"][0]["deviceId"] == DEVICE_SN
        assert devices_payload["items"][0]["online"] is False

        state["device"]["online"] = "1"
        state["device"]["stateList"][1]["fnValue"] = "61"

        refresh_response = await client.post(f"/api/devices/{DEVICE_SN}/refresh")
        assert refresh_response.status_code == 200
        refreshed_device = refresh_response.json()["item"]
        assert refreshed_device["online"] is True
        assert refreshed_device["batteryLevel"] == 61

        command_response = await client.post(
            f"/api/devices/{DEVICE_SN}/commands",
            json={"fnCode": CONTROL_CODE, "fnValue": "1"},
        )
        assert command_response.status_code == 200
        assert command_response.json()["accepted"] is True
        assert state["last_control"] == {"sn": DEVICE_SN, "fnCode": CONTROL_CODE, "fnValue": "1"}
        assert command_response.json()["device"]["states"][0]["fnValue"] == "1"


@pytest.mark.asyncio
async def test_backend_returns_sanitized_errors() -> None:
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        missing_session = await client.get("/api/devices")
        assert missing_session.status_code == 503
        assert missing_session.json()["error"]["code"] == "SESSION_NOT_CONFIGURED"

        invalid_session = await client.post(
            "/api/session",
            json={
                "accessToken": "test-access-token",
                "gatewayUrl": "http://127.0.0.1:9",
            },
        )
        assert invalid_session.status_code == 200

        connectivity_error = await client.get("/api/devices")
        assert connectivity_error.status_code == 502
        assert connectivity_error.json()["error"]["code"] == "BLUETTI_CONNECTIVITY_ERROR"

        validation_error = await client.post(
            "/api/devices/AC200L-TEST-001/commands",
            json={"fnCode": ""},
        )
        assert validation_error.status_code == 422
        assert validation_error.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_backend_bootstraps_from_refresh_token_only(
    fake_bluetti_gateway: tuple[str, dict[str, Any]],
    tmp_path,
) -> None:
    base_url, state = fake_bluetti_gateway
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        session_response = await client.post(
            "/api/session",
            json={
                "refreshToken": "test-refresh-token",
                "ssoUrl": f"{base_url}/sso",
                "gatewayUrl": base_url,
                "wssUrl": "ws://127.0.0.1/unused",
            },
        )
        assert session_response.status_code == 200
        assert session_response.json()["hasAccessToken"] is False
        assert session_response.json()["hasRefreshToken"] is True

        devices_response = await client.get("/api/devices")
        assert devices_response.status_code == 200
        assert devices_response.json()["count"] == 1
        assert len(state["refresh_requests"]) == 1

        persisted = json.loads((tmp_path / "tokens.json").read_text())
        assert persisted["accessToken"] == "refreshed-access-token-1"
        assert persisted["refreshToken"] == "refreshed-refresh-token-1"


@pytest.mark.asyncio
async def test_backend_refreshes_expired_access_token_and_retries(
    fake_bluetti_gateway: tuple[str, dict[str, Any]],
    tmp_path,
) -> None:
    base_url, state = fake_bluetti_gateway
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        session_response = await client.post(
            "/api/session",
            json={
                "accessToken": "expired-access-token",
                "refreshToken": "test-refresh-token",
                "ssoUrl": f"{base_url}/sso",
                "gatewayUrl": base_url,
                "wssUrl": "ws://127.0.0.1/unused",
            },
        )
        assert session_response.status_code == 200

        devices_response = await client.get("/api/devices")
        assert devices_response.status_code == 200
        assert devices_response.json()["count"] == 1
        assert len(state["refresh_requests"]) == 1
        assert state["refresh_requests"][0]["refresh_token"] == "test-refresh-token"

        session_status = await client.get("/api/session")
        assert session_status.status_code == 200
        assert session_status.json()["hasAccessToken"] is True
        assert session_status.json()["hasRefreshToken"] is True

        persisted = json.loads((tmp_path / "tokens.json").read_text())
        assert persisted["accessToken"] == "refreshed-access-token-1"
        assert persisted["refreshToken"] == "refreshed-refresh-token-1"


@pytest.mark.asyncio
async def test_backend_refresh_and_command_preserve_list_states_when_device_status_is_sparse(
    fake_bluetti_gateway: tuple[str, dict[str, Any]],
) -> None:
    base_url, state = fake_bluetti_gateway
    state["status_device"] = {
        "sn": DEVICE_SN,
        "online": "1",
        "model": "AC200L",
        "name": "Workshop Battery",
        "isBindByCurUser": "1",
        "stateList": [],
    }
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        session_response = await client.post(
            "/api/session",
            json={
                "accessToken": "test-access-token",
                "ssoUrl": f"{base_url}/sso",
                "gatewayUrl": base_url,
                "wssUrl": "ws://127.0.0.1/unused",
            },
        )
        assert session_response.status_code == 200

        refresh_response = await client.post(f"/api/devices/{DEVICE_SN}/refresh")
        assert refresh_response.status_code == 200
        refreshed_device = refresh_response.json()["item"]
        assert refreshed_device["online"] is True
        assert any(state_item["fnCode"] == CONTROL_CODE for state_item in refreshed_device["states"])

        command_response = await client.post(
            f"/api/devices/{DEVICE_SN}/commands",
            json={"fnCode": CONTROL_CODE, "fnValue": "1"},
        )
        assert command_response.status_code == 200
        assert command_response.json()["accepted"] is True
        assert state["last_control"] == {"sn": DEVICE_SN, "fnCode": CONTROL_CODE, "fnValue": "1"}


@pytest.mark.asyncio
async def test_backend_binds_device_before_command_when_status_reports_unbound(
    fake_bluetti_gateway: tuple[str, dict[str, Any]],
) -> None:
    base_url, state = fake_bluetti_gateway
    state["status_device"] = {
        "sn": DEVICE_SN,
        "online": "1",
        "model": "AC200L",
        "name": "Workshop Battery",
        "isBindByCurUser": "0",
        "stateList": [],
    }
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        session_response = await client.post(
            "/api/session",
            json={
                "accessToken": "test-access-token",
                "ssoUrl": f"{base_url}/sso",
                "gatewayUrl": base_url,
                "wssUrl": "ws://127.0.0.1/unused",
            },
        )
        assert session_response.status_code == 200

        command_response = await client.post(
            f"/api/devices/{DEVICE_SN}/commands",
            json={"fnCode": CONTROL_CODE, "fnValue": "1"},
        )

    assert command_response.status_code == 200
    assert command_response.json()["accepted"] is True
    assert state["bind_requests"] == [{"bindSnList": [DEVICE_SN]}]
    assert state["last_control"] == {"sn": DEVICE_SN, "fnCode": CONTROL_CODE, "fnValue": "1"}