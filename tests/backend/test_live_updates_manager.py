from __future__ import annotations

import pytest
from typing import Any

from bluetti_connector.backend.live_updates import LiveUpdateEvent, LiveUpdatesManager


class FakeStompClient:
    def __init__(
        self,
        url: str,
        access_token: str,
        handler=None,
        on_token_expired=None,
        on_error=None,
        on_connected=None,
        on_disconnected=None,
    ) -> None:
        self.url = url
        self.access_token = access_token
        self.handler = handler
        self.on_token_expired = on_token_expired
        self.on_error = on_error
        self.on_connected = on_connected
        self.on_disconnected = on_disconnected
        self.connected = False
        self.disconnected = False

    def connect(self) -> None:
        self.connected = True
        if self.on_connected is not None:
            self.on_connected()

    def disconnect(self) -> None:
        self.disconnected = True
        if self.on_disconnected is not None:
            self.on_disconnected()


class FailingStompClient(FakeStompClient):
    def connect(self) -> None:
        raise RuntimeError("websocket unavailable")


def test_live_updates_manager_starts_for_authenticated_wss_sessions() -> None:
    created_clients: list[FakeStompClient] = []

    def client_factory(*args: Any, **kwargs: Any) -> FakeStompClient:
        client = FakeStompClient(*args, **kwargs)
        created_clients.append(client)
        return client

    manager = LiveUpdatesManager(stomp_client_factory=client_factory)

    manager.configure(access_token="access-token", wss_url="wss://gw.example/ws-coordination")

    snapshot = manager.snapshot()
    assert snapshot.configured is True
    assert snapshot.status == "connected"
    assert snapshot.lastError is None
    assert len(created_clients) == 1
    assert created_clients[0].url == "wss://gw.example/ws-coordination"
    assert created_clients[0].access_token == "access-token"


def test_live_updates_manager_disables_for_non_wss_or_missing_auth() -> None:
    created_clients: list[FakeStompClient] = []

    def client_factory(*args: Any, **kwargs: Any) -> FakeStompClient:
        client = FakeStompClient(*args, **kwargs)
        created_clients.append(client)
        return client

    manager = LiveUpdatesManager(stomp_client_factory=client_factory)

    manager.configure(access_token="access-token", wss_url="ws://127.0.0.1/unused")
    assert manager.snapshot().status == "disabled"

    manager.configure(access_token=None, wss_url="wss://gw.example/ws-coordination")
    snapshot = manager.snapshot()
    assert snapshot.configured is False
    assert snapshot.status == "disabled"
    assert created_clients == []


@pytest.mark.asyncio
async def test_live_updates_manager_emits_sanitized_device_update_events() -> None:
    created_clients: list[FakeStompClient] = []

    def client_factory(*args: Any, **kwargs: Any) -> FakeStompClient:
        client = FakeStompClient(*args, **kwargs)
        created_clients.append(client)
        return client

    manager = LiveUpdatesManager(stomp_client_factory=client_factory)
    manager.configure(access_token="access-token", wss_url="wss://gw.example/ws-coordination")

    subscriber_id, queue = manager.subscribe()
    try:
        status_event = await queue.get()
        assert status_event == LiveUpdateEvent(eventType="status", status="connected", lastError=None)

        created_clients[0].handler('{"data":{"deviceSn":"AC200L-TEST-001","raw":"ignored"}}')

        update_event = await queue.get()
        assert update_event == LiveUpdateEvent(
            eventType="device-update",
            deviceSn="AC200L-TEST-001",
        )
    finally:
        manager.unsubscribe(subscriber_id)


def test_live_updates_manager_degrades_when_startup_fails() -> None:
    manager = LiveUpdatesManager(stomp_client_factory=FailingStompClient)

    manager.configure(access_token="access-token", wss_url="wss://gw.example/ws-coordination")

    snapshot = manager.snapshot()
    assert snapshot.configured is True
    assert snapshot.status == "degraded"
    assert snapshot.lastError == "websocket unavailable"


def test_live_updates_manager_degrades_on_disconnect_and_token_expiry() -> None:
    created_clients: list[FakeStompClient] = []

    def client_factory(*args: Any, **kwargs: Any) -> FakeStompClient:
        client = FakeStompClient(*args, **kwargs)
        created_clients.append(client)
        return client

    manager = LiveUpdatesManager(stomp_client_factory=client_factory)
    manager.configure(access_token="access-token", wss_url="wss://gw.example/ws-coordination")

    created_clients[0].on_disconnected()
    disconnect_snapshot = manager.snapshot()
    assert disconnect_snapshot.status == "degraded"
    assert disconnect_snapshot.lastError == "Live updates disconnected."

    created_clients[0].on_token_expired()
    expired_snapshot = manager.snapshot()
    assert expired_snapshot.status == "degraded"
    assert expired_snapshot.lastError == "Live updates authentication expired."