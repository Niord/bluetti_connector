from __future__ import annotations

from collections.abc import AsyncIterator
from copy import deepcopy
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
        "last_control": None,
    }

    async def devices_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "msgId": "devices",
                "msgCode": 0,
                "data": [deepcopy(state["device"])],
            }
        )

    async def device_states_handler(request: web.Request) -> web.Response:
        sns = request.query.get("sns")
        devices = [deepcopy(state["device"])]
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

    app = web.Application()
    app.router.add_get("/api/bluiotdata/ha/v1/devices", devices_handler)
    app.router.add_get("/api/bluiotdata/ha/v1/deviceStates", device_states_handler)
    app.router.add_post("/api/bluiotdata/ha/v1/fulfillment", control_handler)

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