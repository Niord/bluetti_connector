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


def test_stomp_listener_ignores_close_frame_transport_noise() -> None:
    errors: list[str] = []
    client = StompClient(
        url="wss://gw.example/ws-coordination",
        access_token="access-token",
        on_error=lambda error: errors.append(str(error)),
    )

    client.listener.on_error(None, "fin=1 opcode=8 data=b'\\x03\\xe8'")

    assert errors == []