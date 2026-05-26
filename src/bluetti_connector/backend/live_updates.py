from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
from threading import Lock
from typing import Callable, Literal
from urllib.parse import urlparse

from ..core import StompClient


LiveUpdateStatus = Literal["disabled", "connecting", "connected", "degraded"]
StompClientFactory = Callable[..., StompClient]


@dataclass(frozen=True)
class LiveUpdateEvent:
    eventType: Literal["status", "device-update"]
    status: LiveUpdateStatus | None = None
    lastError: str | None = None
    deviceSn: str | None = None


@dataclass(frozen=True)
class LiveUpdatesSnapshot:
    configured: bool
    status: LiveUpdateStatus
    lastError: str | None = None


class LiveUpdatesManager:
    def __init__(self, stomp_client_factory: StompClientFactory = StompClient) -> None:
        self._stomp_client_factory = stomp_client_factory
        self._lock = Lock()
        self._client: StompClient | None = None
        self._access_token: str | None = None
        self._wss_url: str | None = None
        self._suppress_disconnect_event = False
        self._subscribers: dict[int, tuple[asyncio.AbstractEventLoop, asyncio.Queue[LiveUpdateEvent]]] = {}
        self._next_subscriber_id = 0
        self._snapshot = LiveUpdatesSnapshot(configured=False, status="disabled", lastError=None)

    def snapshot(self) -> LiveUpdatesSnapshot:
        with self._lock:
            return self._snapshot

    def configure(self, *, access_token: str | None, wss_url: str | None) -> None:
        should_enable = bool(access_token) and self._supports_live_updates(wss_url)

        client_to_stop: StompClient | None = None
        client_to_start: StompClient | None = None

        with self._lock:
            same_config = (
                self._client is not None
                and self._access_token == access_token
                and self._wss_url == wss_url
            )
            if same_config:
                return

            if self._client is not None:
                client_to_stop = self._client
                self._client = None

            self._access_token = access_token
            self._wss_url = wss_url

            if not should_enable:
                self._snapshot = LiveUpdatesSnapshot(configured=False, status="disabled", lastError=None)
            else:
                self._snapshot = LiveUpdatesSnapshot(configured=True, status="connecting", lastError=None)
                client_to_start = self._stomp_client_factory(
                    wss_url,
                    access_token,
                    handler=self._handle_message,
                    on_token_expired=self._handle_token_expired,
                    on_error=self._handle_error,
                    on_connected=self._handle_connected,
                    on_disconnected=self._handle_disconnected,
                )
                self._client = client_to_start

            status_event = self._build_status_event_locked()

        if client_to_stop is not None:
            self._disconnect_client(client_to_stop)
        self._publish_event(status_event)
        if client_to_start is not None:
            try:
                client_to_start.connect()
            except Exception as error:
                self._handle_error(error)

    def shutdown(self) -> None:
        client_to_stop: StompClient | None = None
        with self._lock:
            if self._client is not None:
                client_to_stop = self._client
                self._client = None
            self._access_token = None
            self._wss_url = None
            self._snapshot = LiveUpdatesSnapshot(configured=False, status="disabled", lastError=None)
            status_event = self._build_status_event_locked()

        if client_to_stop is not None:
            self._disconnect_client(client_to_stop)
        self._publish_event(status_event)

    def subscribe(self) -> tuple[int, asyncio.Queue[LiveUpdateEvent]]:
        queue: asyncio.Queue[LiveUpdateEvent] = asyncio.Queue()
        loop = asyncio.get_running_loop()
        with self._lock:
            subscriber_id = self._next_subscriber_id
            self._next_subscriber_id += 1
            self._subscribers[subscriber_id] = (loop, queue)
            queue.put_nowait(self._build_status_event_locked())
        return subscriber_id, queue

    def unsubscribe(self, subscriber_id: int) -> None:
        with self._lock:
            self._subscribers.pop(subscriber_id, None)

    def _disconnect_client(self, client: StompClient) -> None:
        with self._lock:
            self._suppress_disconnect_event = True
        try:
            client.disconnect()
        finally:
            with self._lock:
                self._suppress_disconnect_event = False

    def _handle_connected(self) -> None:
        with self._lock:
            if self._snapshot.status == "disabled":
                return
            self._snapshot = LiveUpdatesSnapshot(configured=True, status="connected", lastError=None)
            status_event = self._build_status_event_locked()
        self._publish_event(status_event)

    def _handle_disconnected(self) -> None:
        with self._lock:
            if self._suppress_disconnect_event or self._snapshot.status == "disabled":
                return
            self._snapshot = LiveUpdatesSnapshot(
                configured=bool(self._access_token and self._supports_live_updates(self._wss_url)),
                status="degraded",
                lastError="Live updates disconnected.",
            )
            status_event = self._build_status_event_locked()
        self._publish_event(status_event)

    def _handle_token_expired(self) -> None:
        with self._lock:
            if self._snapshot.status == "disabled":
                return
            self._snapshot = LiveUpdatesSnapshot(
                configured=True,
                status="degraded",
                lastError="Live updates authentication expired.",
            )
            status_event = self._build_status_event_locked()
        self._publish_event(status_event)

    def _handle_error(self, error: Exception) -> None:
        with self._lock:
            if self._snapshot.status == "disabled":
                return
            self._snapshot = LiveUpdatesSnapshot(
                configured=True,
                status="degraded",
                lastError=str(error),
            )
            status_event = self._build_status_event_locked()
        self._publish_event(status_event)

    def _handle_message(self, message: str) -> None:
        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            return

        device_sn = payload.get("data", {}).get("deviceSn")
        if not device_sn:
            return

        self._publish_event(
            LiveUpdateEvent(
                eventType="device-update",
                deviceSn=str(device_sn),
            )
        )

    def _build_status_event_locked(self) -> LiveUpdateEvent:
        return LiveUpdateEvent(
            eventType="status",
            status=self._snapshot.status,
            lastError=self._snapshot.lastError,
        )

    def _publish_event(self, event: LiveUpdateEvent) -> None:
        with self._lock:
            subscribers = list(self._subscribers.values())

        for loop, queue in subscribers:
            loop.call_soon_threadsafe(queue.put_nowait, event)

    @staticmethod
    def _supports_live_updates(wss_url: str | None) -> bool:
        if not wss_url:
            return False
        return urlparse(wss_url).scheme.lower() == "wss"