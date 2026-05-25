from __future__ import annotations

import json
import logging
import time
from threading import Thread
from typing import Callable
from urllib.parse import urlparse

import stomper
import websocket

from ..application_exception import ApplicationRuntimeException, AuthenticationExpiredError
from ..const import TOKEN_EXPIRED_CODE

__LOGGER__ = logging.getLogger(__name__)

MessageHandler = Callable[[str], None]
ErrorHandler = Callable[[Exception], None]
TokenExpiredHandler = Callable[[], None]


class StompClient:
    def __init__(
        self,
        url: str,
        access_token: str,
        handler: MessageHandler | None = None,
        on_token_expired: TokenExpiredHandler | None = None,
        on_error: ErrorHandler | None = None,
    ) -> None:
        self._base_url = url.rstrip("/")
        self._url = f"{self._base_url}/websocket"
        self._headers = {
            "Host": self._get_host(url),
            "Authorization": access_token,
        }
        self.on_token_expired = on_token_expired
        self.on_error = on_error
        self.listener = StompListener(self, handler)
        self.websocket: websocket.WebSocketApp | None = None
        self.running = False
        self.heartbeat_thread: Thread | None = None
        self.heartbeat_interval = 10
        self.reconnect_delay = 1
        self.max_reconnect_delay = 30

    @staticmethod
    def _get_host(connection_url: str) -> str:
        parsed = urlparse(connection_url)
        return parsed.hostname or ""

    def connect(self) -> None:
        stomp_trace = False
        websocket.enableTrace(stomp_trace)
        __LOGGER__.info("Start to connect the BLUETTI WebSocket Server.")
        __LOGGER__.info("Stomp client trace enable: %s", stomp_trace)

        self.websocket = websocket.WebSocketApp(
            self._url,
            on_message=self.listener.on_message,
            on_error=self.listener.on_error,
            on_close=self.listener.on_close,
        )
        self.websocket.on_open = self._on_open
        self.running = True
        Thread(target=self.websocket.run_forever, daemon=True).start()

    def disconnect(self) -> None:
        self.running = False
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=5)
        if self.websocket is not None:
            self.websocket.close()

    def _on_open(self, ws: websocket.WebSocketApp) -> None:
        connect = (
            "CONNECT\n"
            "accept-version:1.0,1.1,2.0\n"
            f"Host:{self._headers['Host']}\n"
            f"Authorization: {self._headers['Authorization']}\n"
            "heart-beat:10000,10000\n"
            "\n\x00\n"
        )
        __LOGGER__.info("Connect the BLUETTI WebSocket Server successfully.")
        ws.send(connect)
        self._start_heartbeat()

    def _start_heartbeat(self) -> None:
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            return
        self.heartbeat_thread = Thread(target=self._send_heartbeat, daemon=True)
        self.heartbeat_thread.start()

    def _send_heartbeat(self) -> None:
        while self.running and self.websocket and hasattr(self.websocket, "sock") and self.websocket.sock:
            try:
                if not self.websocket.sock.connected:
                    break
                self.websocket.send("\n")
                __LOGGER__.debug("Sent STOMP heartbeat")
            except Exception as error:
                self._handle_error(error)
                break
            time.sleep(self.heartbeat_interval)

    def reconnect(self) -> None:
        __LOGGER__.info("Websocket reconnect")
        if not self.running:
            __LOGGER__.info("Websocket has stopped and will not reconnect")
            return
        time.sleep(self.reconnect_delay)
        self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
        self.connect()

    def _handle_token_expired(self) -> None:
        if self.on_token_expired is not None:
            self.on_token_expired()

    def _handle_error(self, error: Exception) -> None:
        if self.on_error is not None:
            self.on_error(error)
            return
        __LOGGER__.error("BLUETTI websocket error: %s", error)


class StompListener:
    def __init__(self, stomp_client: StompClient, handler: MessageHandler | None = None) -> None:
        self._handler = handler
        self.client = stomp_client

    def _callback(self, callback: Callable[..., None] | None, *args: object) -> None:
        if callback is None:
            return
        try:
            callback(*args)
        except Exception as error:
            self.client._handle_error(error)

    def _on_subscribe(self, ws: websocket.WebSocketApp, destination: str) -> None:
        subscription = stomper.subscribe(destination, "clientUniqueId", ack="auto")
        ws.send(subscription)

    def on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        __LOGGER__.debug("Received the BLUETTI websocket message:\n%s", message)
        if not message or message == "\n":
            __LOGGER__.debug("Received heartbeat from server")
            return

        frame = stomper.Frame()
        frame.unpack(message)

        if frame.cmd == "ERROR":
            payload = json.loads(frame.headers["message"].replace("\\c", ":"))
            if payload["msgCode"] == TOKEN_EXPIRED_CODE:
                self.client.disconnect()
                self.client._handle_token_expired()
                self.client._handle_error(
                    AuthenticationExpiredError(
                        msgCode=payload["msgCode"],
                        data=payload,
                    )
                )
                return

            self.client._handle_error(
                ApplicationRuntimeException(
                    msgCode=payload["msgCode"],
                    errMessage=payload["message"],
                    data=payload,
                )
            )
            return

        if frame.cmd == "CONNECTED":
            heartbeat = frame.headers.get("heart-beat", "0,0")
            server_send, server_receive = map(int, heartbeat.split(","))
            __LOGGER__.info(
                "Server heartbeat configuration: send=%s, receive=%s",
                server_send,
                server_receive,
            )
            destination = f"/ws-subscribe/user/{frame.headers['user-name']}/notify"
            self._on_subscribe(ws, destination)
            return

        if frame.cmd == "MESSAGE":
            self._callback(self._handler, frame.body)

    def on_error(self, ws: websocket.WebSocketApp, error: object) -> None:
        wrapped = error if isinstance(error, Exception) else RuntimeError(str(error))
        self.client._handle_error(wrapped)

    def on_close(self, ws: websocket.WebSocketApp, close_status_code: int | None, close_msg: str | None) -> None:
        __LOGGER__.debug(
            "WebSocket disconnected. status=%s, message=%s",
            close_status_code,
            close_msg,
        )
        self.client.reconnect()