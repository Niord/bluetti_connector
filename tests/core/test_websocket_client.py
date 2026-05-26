from __future__ import annotations

from bluetti_connector.core.api.websocket import StompClient


def test_stomp_client_resets_reconnect_delay_after_successful_connect() -> None:
    connected: list[str] = []
    client = StompClient(
        url="wss://gw.example/ws-coordination",
        access_token="access-token",
        on_connected=lambda: connected.append("connected"),
    )
    client.reconnect_delay = 8

    client._handle_connected()

    assert client.reconnect_delay == 1
    assert connected == ["connected"]