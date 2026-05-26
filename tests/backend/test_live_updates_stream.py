from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.routing import APIRoute

from bluetti_connector.backend.app import create_app


async def _read_one_sse_event(response) -> tuple[str, dict[str, object]]:
    chunk = await asyncio.wait_for(anext(response.body_iterator), timeout=1)
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


@pytest.mark.asyncio
async def test_live_updates_stream_emits_initial_status_without_active_session() -> None:
    app = create_app()

    response = await _open_live_updates_stream(app)
    try:
        event_name, payload = await _read_one_sse_event(response)
    finally:
        await response.body_iterator.aclose()

    assert response.media_type == "text/event-stream"
    assert response.headers["cache-control"] == "no-cache"
    assert event_name == "status"
    assert payload == {
        "eventType": "status",
        "status": "disabled",
    }


@pytest.mark.asyncio
async def test_live_updates_stream_forwards_device_update_events() -> None:
    app = create_app()

    response = await _open_live_updates_stream(app)
    try:
        await _read_one_sse_event(response)

        app.state.backend_service._live_updates._handle_message(
            '{"data":{"deviceSn":"AC3002306000478165","ignored":"value"}}'
        )

        event_name, payload = await _read_one_sse_event(response)
    finally:
        await response.body_iterator.aclose()

    assert event_name == "device-update"
    assert payload == {
        "eventType": "device-update",
        "deviceSn": "AC3002306000478165",
    }