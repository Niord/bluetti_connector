from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from copy import deepcopy
import json
from typing import Any

import pytest
from aiohttp import web
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient

from bluetti_connector.backend.app import create_app


DEVICE_SN = "AC200L-TEST-001"
CONTROL_CODE = "AC_OUTPUT_ON"
SELECT_CONTROL_CODE = "SetCtrlWorkMode"
LIVE_UPDATE_USER = "fake-user"


def _parse_stomp_headers(frame: str) -> tuple[str, dict[str, str]]:
    lines = frame.replace("\x00", "").splitlines()
    if not lines:
        return "", {}

    headers: dict[str, str] = {}
    for line in lines[1:]:
        if not line:
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key] = value.strip()
    return lines[0].strip(), headers


def _build_connected_frame() -> str:
    return (
        "CONNECTED\n"
        "version:1.2\n"
        "heart-beat:10000,10000\n"
        f"user-name:{LIVE_UPDATE_USER}\n"
        "\n\x00"
    )


def _build_message_frame(*, destination: str, body: str) -> str:
    return (
        "MESSAGE\n"
        "subscription:clientUniqueId\n"
        f"destination:{destination}\n"
        "content-type:application/json\n"
        "\n"
        f"{body}\x00"
    )


def _build_live_updates_url(base_url: str) -> str:
    return base_url.replace("http://", "ws://", 1) + "/api/edgeiotgw/ws-coordination"


async def _read_one_sse_event(response) -> tuple[str, dict[str, object]]:
    chunk = await asyncio.wait_for(response.body_iterator.__anext__(), timeout=2)
    lines = [line for line in chunk.splitlines() if line]

    event_name = next(line.split(": ", 1)[1] for line in lines if line.startswith("event: "))
    payload = json.loads(next(line.split(": ", 1)[1] for line in lines if line.startswith("data: ")))
    return event_name, payload


async def _open_live_updates_stream(app):
    route = next(
        route
        for route in app.router.routes
        if isinstance(route, APIRoute) and route.path == "/api/live-updates"
    )
    return await route.endpoint()


async def _wait_for_status_event(response, expected_status: str) -> dict[str, object]:
    for _ in range(10):
        event_name, payload = await _read_one_sse_event(response)
        if event_name == "status" and payload.get("status") == expected_status:
            return payload
    raise AssertionError(f"Expected live update status {expected_status!r}.")


async def _wait_for_device_update_event(response, expected_device_sn: str) -> dict[str, object]:
    for _ in range(10):
        event_name, payload = await _read_one_sse_event(response)
        if event_name == "device-update" and payload.get("deviceSn") == expected_device_sn:
            return payload
    raise AssertionError(f"Expected live update event for {expected_device_sn!r}.")


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
                {
                    "fnCode": SELECT_CONTROL_CODE,
                    "fnName": "Working mode",
                    "fnValue": "workmode_1",
                    "fnType": "select",
                    "supportModeValues": [
                        {"code": "workmode_1", "name": "Standard UPS"},
                        {"code": "workmode_2", "name": "Time Control UPS"},
                    ],
                },
            ],
        },
        "status_device": None,
        "last_control": None,
        "bind_requests": [],
        "active_access_token": "test-access-token",
        "active_refresh_token": "test-refresh-token",
        "refresh_requests": [],
        "live_update_sockets": [],
        "last_live_update_subscription": None,
        "reject_next_live_update_connection": False,
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

    async def websocket_handler(request: web.Request) -> web.StreamResponse:
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)

        try:
            async for message in ws:
                if message.type != web.WSMsgType.TEXT:
                    continue
                if not message.data or message.data == "\n":
                    continue

                command, headers = _parse_stomp_headers(message.data)
                if command == "CONNECT":
                    if state["reject_next_live_update_connection"]:
                        state["reject_next_live_update_connection"] = False
                        await ws.close(message=b"rejected")
                        break
                    if headers.get("Authorization") != state["active_access_token"]:
                        await ws.close(message=b"unauthorized")
                        break
                    await ws.send_str(_build_connected_frame())
                    continue

                if command == "SUBSCRIBE":
                    state["last_live_update_subscription"] = headers.get("destination")
                    state["live_update_sockets"].append(ws)
        finally:
            state["live_update_sockets"] = [
                active_socket
                for active_socket in state["live_update_sockets"]
                if active_socket is not ws and not active_socket.closed
            ]

        return ws

    async def emit_live_update_handler(request: web.Request) -> web.Response:
        payload = await request.json()
        device_sn = payload.get("deviceSn") or DEVICE_SN
        destination = state["last_live_update_subscription"] or f"/ws-subscribe/user/{LIVE_UPDATE_USER}/notify"
        frame = _build_message_frame(
            destination=destination,
            body=json.dumps({"data": {"deviceSn": device_sn}}),
        )

        live_update_sockets = [socket for socket in state["live_update_sockets"] if not socket.closed]
        state["live_update_sockets"] = live_update_sockets
        for socket in live_update_sockets:
            await socket.send_str(frame)

        return web.json_response(
            {
                "accepted": True,
                "deviceSn": device_sn,
                "subscriberCount": len(live_update_sockets),
            }
        )

    async def disconnect_live_updates_handler(request: web.Request) -> web.Response:
        state["reject_next_live_update_connection"] = True
        for socket in list(state["live_update_sockets"]):
            if not socket.closed:
                await socket.close()
        state["live_update_sockets"] = []
        return web.json_response({"accepted": True})

    app = web.Application()
    app.router.add_get("/api/bluiotdata/ha/v1/devices", devices_handler)
    app.router.add_get("/api/bluiotdata/ha/v1/deviceStates", device_states_handler)
    app.router.add_post("/api/bluiotdata/ha/v1/fulfillment", control_handler)
    app.router.add_post("/api/bluiotdata/ha/v1/bindDevices", bind_devices_handler)
    app.router.add_post("/sso/oauth2/token", token_handler)
    app.router.add_get("/api/edgeiotgw/ws-coordination/websocket", websocket_handler)
    app.router.add_post("/api/test/live-updates/device-update", emit_live_update_handler)
    app.router.add_post("/api/test/live-updates/disconnect", disconnect_live_updates_handler)

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
async def test_backend_exposes_control_metadata_for_supported_states(
    fake_bluetti_gateway: tuple[str, dict[str, Any]],
) -> None:
    base_url, _state = fake_bluetti_gateway
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

        devices_response = await client.get("/api/devices")

    assert devices_response.status_code == 200
    states = {item["fnCode"]: item for item in devices_response.json()["items"][0]["states"]}
    assert states[CONTROL_CODE]["displayValue"] == "Off"
    assert states[CONTROL_CODE]["control"] == {
        "kind": "switch",
        "allowedValues": [
            {"value": "0", "label": "Off"},
            {"value": "1", "label": "On"},
        ],
    }
    assert states["SOC"]["displayValue"] == "55"
    assert states["SOC"]["control"] is None
    assert states[SELECT_CONTROL_CODE]["displayValue"] == "Standard UPS"
    assert states[SELECT_CONTROL_CODE]["control"] == {
        "kind": "select",
        "allowedValues": [
            {"value": "workmode_1", "label": "Standard UPS"},
            {"value": "workmode_2", "label": "Time Control UPS"},
        ],
    }


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


@pytest.mark.asyncio
async def test_backend_executes_select_style_commands(
    fake_bluetti_gateway: tuple[str, dict[str, Any]],
) -> None:
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

        command_response = await client.post(
            f"/api/devices/{DEVICE_SN}/commands",
            json={"fnCode": SELECT_CONTROL_CODE, "fnValue": "workmode_2"},
        )

    assert command_response.status_code == 200
    assert command_response.json()["accepted"] is True
    assert state["last_control"] == {"sn": DEVICE_SN, "fnCode": SELECT_CONTROL_CODE, "fnValue": "workmode_2"}
    returned_states = {item["fnCode"]: item for item in command_response.json()["device"]["states"]}
    assert returned_states[SELECT_CONTROL_CODE]["fnValue"] == "workmode_2"
    assert returned_states[SELECT_CONTROL_CODE]["displayValue"] == "Time Control UPS"


@pytest.mark.asyncio
async def test_backend_rejects_invalid_select_values(
    fake_bluetti_gateway: tuple[str, dict[str, Any]],
) -> None:
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

        command_response = await client.post(
            f"/api/devices/{DEVICE_SN}/commands",
            json={"fnCode": SELECT_CONTROL_CODE, "fnValue": "workmode_invalid"},
        )

    assert command_response.status_code == 400
    assert command_response.json()["error"]["code"] == "INVALID_COMMAND"
    assert state["last_control"] is None


@pytest.mark.asyncio
async def test_backend_rejects_read_only_state_commands(
    fake_bluetti_gateway: tuple[str, dict[str, Any]],
) -> None:
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

        command_response = await client.post(
            f"/api/devices/{DEVICE_SN}/commands",
            json={"fnCode": "SOC", "fnValue": "42"},
        )

    assert command_response.status_code == 400
    assert command_response.json()["error"]["code"] == "INVALID_COMMAND"
    assert state["last_control"] is None


@pytest.mark.asyncio
async def test_backend_streams_fake_gateway_live_update_events(
    fake_bluetti_gateway: tuple[str, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_url, state = fake_bluetti_gateway
    monkeypatch.setenv("BLUETTI_ENABLE_FAKE_GATEWAY_LIVE_UPDATES", "true")
    app = create_app()

    async with (
        AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client,
        AsyncClient(base_url=base_url) as gateway_client,
    ):
        session_response = await client.post(
            "/api/session",
            json={
                "accessToken": "test-access-token",
                "ssoUrl": f"{base_url}/sso",
                "gatewayUrl": base_url,
                "wssUrl": _build_live_updates_url(base_url),
            },
        )
        assert session_response.status_code == 200
        assert session_response.json()["liveUpdates"]["status"] in {"connecting", "connected"}

        response = await _open_live_updates_stream(app)
        try:
            connected_payload = await _wait_for_status_event(response, "connected")
            assert connected_payload == {
                "eventType": "status",
                "status": "connected",
            }

            emit_response = await gateway_client.post(
                "/api/test/live-updates/device-update",
                json={"deviceSn": DEVICE_SN},
            )
            assert emit_response.status_code == 200
            assert emit_response.json()["subscriberCount"] == 1
            assert state["last_live_update_subscription"] == f"/ws-subscribe/user/{LIVE_UPDATE_USER}/notify"

            update_payload = await _wait_for_device_update_event(response, DEVICE_SN)
        finally:
            await response.body_iterator.aclose()

    assert update_payload == {
        "eventType": "device-update",
        "deviceSn": DEVICE_SN,
    }


@pytest.mark.asyncio
async def test_backend_reports_degraded_live_updates_when_fake_gateway_disconnects(
    fake_bluetti_gateway: tuple[str, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_url, _state = fake_bluetti_gateway
    monkeypatch.setenv("BLUETTI_ENABLE_FAKE_GATEWAY_LIVE_UPDATES", "true")
    app = create_app()

    async with (
        AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client,
        AsyncClient(base_url=base_url) as gateway_client,
    ):
        session_response = await client.post(
            "/api/session",
            json={
                "accessToken": "test-access-token",
                "ssoUrl": f"{base_url}/sso",
                "gatewayUrl": base_url,
                "wssUrl": _build_live_updates_url(base_url),
            },
        )
        assert session_response.status_code == 200

        response = await _open_live_updates_stream(app)
        try:
            await _wait_for_status_event(response, "connected")

            disconnect_response = await gateway_client.post("/api/test/live-updates/disconnect")
            assert disconnect_response.status_code == 200

            degraded_payload = await _wait_for_status_event(response, "degraded")
        finally:
            await response.body_iterator.aclose()

    assert degraded_payload == {
        "eventType": "status",
        "status": "degraded",
        "lastError": "Live updates disconnected.",
    }