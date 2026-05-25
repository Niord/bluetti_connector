from __future__ import annotations

import argparse
from copy import deepcopy

from aiohttp import web


DEVICE_SN = "AC200L-TEST-001"
CONTROL_CODE = "AC_OUTPUT_ON"


def build_state() -> dict[str, object]:
    return {
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


def create_fake_gateway_app() -> web.Application:
    state = build_state()
    app = web.Application()

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

    app.router.add_get("/api/bluiotdata/ha/v1/devices", devices_handler)
    app.router.add_get("/api/bluiotdata/ha/v1/deviceStates", device_states_handler)
    app.router.add_post("/api/bluiotdata/ha/v1/fulfillment", control_handler)
    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a fake BLUETTI gateway for local smoke tests.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind the fake gateway to.")
    parser.add_argument("--port", default=18081, type=int, help="Port to bind the fake gateway to.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    web.run_app(create_fake_gateway_app(), host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())