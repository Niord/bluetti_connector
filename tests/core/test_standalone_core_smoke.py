from __future__ import annotations

from collections.abc import AsyncIterator
from copy import deepcopy
from typing import Any

import aiohttp
import pytest
from aiohttp import web

from bluetti_connector.core.api.product_client import ProductClient
from bluetti_connector.core.models import BluettiData
from bluetti_connector.core.profile.application_profile import ApplicationProfile


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
async def test_standalone_core_smoke_flow(fake_bluetti_gateway: tuple[str, dict[str, Any]]) -> None:
    base_url, state = fake_bluetti_gateway
    profile = ApplicationProfile(active="test")
    profile.config = {
        "server": {
            "sso": f"{base_url}/sso",
            "gateway": base_url,
            "wss": "ws://127.0.0.1/unused",
        }
    }

    async with aiohttp.ClientSession() as session:
        client = ProductClient(
            httpSession=session,
            accessToken="test-access-token",
            application_profile=profile,
        )

        products = await client.get_user_products()
        assert products.is_ok()
        assert products.data is not None
        assert len(products.data) == 1
        assert products.data[0].sn == DEVICE_SN

        devices = BluettiData(products.data)
        devices.attach_api_client(client)
        device = devices.get_device_by_sn(DEVICE_SN)

        assert device is not None
        assert device.online is False
        assert device.battery_level == 55

        state["device"]["online"] = "1"
        state["device"]["stateList"][1]["fnValue"] = "61"

        await device.async_update()

        assert device.online is True
        assert device.battery_level == 61

        await device.set_state_value(CONTROL_CODE, "1")

        assert state["last_control"] == {"sn": DEVICE_SN, "fnCode": CONTROL_CODE, "fnValue": "1"}
        assert device.get_state(CONTROL_CODE) is not None
        assert device.get_state(CONTROL_CODE).fn_value == "1"