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
        "active_access_token": "test-access-token",
        "active_refresh_token": "test-refresh-token",
        "refresh_requests": [],
    }


def create_fake_gateway_app() -> web.Application:
    state = build_state()
    app = web.Application()

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
        if not is_authorized(request):
            return token_expired_response()
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

    app.router.add_get("/api/bluiotdata/ha/v1/devices", devices_handler)
    app.router.add_get("/api/bluiotdata/ha/v1/deviceStates", device_states_handler)
    app.router.add_post("/api/bluiotdata/ha/v1/fulfillment", control_handler)
    app.router.add_post("/sso/oauth2/token", token_handler)
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