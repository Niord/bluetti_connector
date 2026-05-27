from __future__ import annotations

import argparse
from copy import deepcopy
import json

from aiohttp import web


DEVICE_SN = "AC200L-TEST-001"
CONTROL_CODE = "AC_OUTPUT_ON"
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
        "live_update_sockets": [],
        "last_live_update_subscription": None,
        "reject_next_live_update_connection": False,
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

    app.router.add_get("/api/bluiotdata/ha/v1/devices", devices_handler)
    app.router.add_get("/api/bluiotdata/ha/v1/deviceStates", device_states_handler)
    app.router.add_post("/api/bluiotdata/ha/v1/fulfillment", control_handler)
    app.router.add_post("/sso/oauth2/token", token_handler)
    app.router.add_get("/api/edgeiotgw/ws-coordination/websocket", websocket_handler)
    app.router.add_post("/api/test/live-updates/device-update", emit_live_update_handler)
    app.router.add_post("/api/test/live-updates/disconnect", disconnect_live_updates_handler)
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