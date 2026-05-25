from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Iterable

from .application_exception import ApplicationRuntimeException
from .const import MANUFACTURER
from .model.product import UserProduct

__LOGGER__ = logging.getLogger(__name__)

StateCallback = Callable[[], None]
DeviceUnboundHandler = Callable[["BluettiDevice"], None]


class BluettiData:
    """Standalone container for discovered BLUETTI devices."""

    def __init__(
        self,
        devices: Iterable[UserProduct | dict[str, Any]] | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
        on_device_unbound: DeviceUnboundHandler | None = None,
    ) -> None:
        self.loop = loop
        self.devices = [
            BluettiDevice.from_product(device, loop=loop, on_device_unbound=on_device_unbound)
            for device in devices or []
        ]

    async def test_connection(self) -> bool:
        await asyncio.sleep(0.1)
        return True

    def get_device_by_sn(self, sn: str) -> "BluettiDevice | None":
        for device in self.devices:
            if device.device_id == sn:
                return device
        return None

    def attach_api_client(self, api_client: Any) -> None:
        for device in self.devices:
            device.api_client = api_client

    def web_socket_message_handler(self, message: str) -> None:
        __LOGGER__.debug("Received websocket payload %s", message)
        payload = json.loads(message)
        sn = payload.get("data", {}).get("deviceSn")
        if not sn:
            return

        device = self.get_device_by_sn(sn)
        if device is None:
            return

        loop = self.loop or device.loop
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(device.async_update(), loop)


class BluettiState:
    def __init__(
        self,
        fn_code: str,
        fn_name: str,
        fn_value: str,
        fn_type: str,
        support_mode_values: list[dict[str, Any]] | None = None,
        sensor_info: dict[str, Any] | None = None,
    ) -> None:
        self.fn_code = fn_code
        self.fn_name = fn_name
        self.fn_value = fn_value
        self.fn_type = fn_type
        self.support_mode_values = support_mode_values or []
        self.sensor_info = sensor_info or {}

    def is_switch(self) -> bool:
        return len(self.support_mode_values) == 0

    def set_value(self, value: str) -> None:
        if self.is_switch() or any(option["code"] == value for option in self.support_mode_values):
            self.fn_value = value
            return
        raise ValueError(f"Invalid value {value} for {self.fn_code}")

    def get_name_for_value(self) -> str:
        if self.is_switch():
            return "On" if self.fn_value == "1" else "Off"
        for option in self.support_mode_values:
            if option["code"] == self.fn_value:
                return option["name"]
        return self.fn_value

    def __repr__(self) -> str:
        return f"<BluettiState {self.fn_code}={self.fn_value}>"


class BluettiDevice:
    def __init__(
        self,
        device_id: str,
        on_line: str,
        name: str | None,
        sn: str,
        model: str | None,
        state_list: list[dict[str, Any]] | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
        api_client: Any | None = None,
        on_device_unbound: DeviceUnboundHandler | None = None,
    ) -> None:
        self.device_id = device_id
        self.on_line = on_line
        self.name = name or sn
        self.sn = sn
        self.model = model
        self.manufacturer = MANUFACTURER
        self.loop = loop
        self._callbacks: set[StateCallback] = set()
        self._api_client = api_client
        self._on_device_unbound = on_device_unbound
        self._unbind_processed = False
        self.states = [
            BluettiState(
                fn_code=state.get("fnCode"),
                fn_name=state.get("fnName") or "",
                fn_value=state.get("fnValue"),
                fn_type=state.get("fnType"),
                support_mode_values=state.get("supportModeValues"),
                sensor_info=state.get("sensorInfo"),
            )
            for state in state_list or []
        ]

    @classmethod
    def from_product(
        cls,
        product: UserProduct | dict[str, Any],
        loop: asyncio.AbstractEventLoop | None = None,
        api_client: Any | None = None,
        on_device_unbound: DeviceUnboundHandler | None = None,
    ) -> "BluettiDevice":
        product_model = product if isinstance(product, UserProduct) else UserProduct.model_validate(product)
        return cls(
            device_id=product_model.sn,
            on_line=product_model.online or "0",
            name=product_model.name,
            sn=product_model.sn,
            model=product_model.model,
            state_list=product_model.stateList or [],
            loop=loop,
            api_client=api_client,
            on_device_unbound=on_device_unbound,
        )

    @property
    def api_client(self) -> Any | None:
        return self._api_client

    @api_client.setter
    def api_client(self, api_client: Any) -> None:
        self._api_client = api_client

    def __repr__(self) -> str:
        return f"<BluettiDevice id={self.device_id} name={self.name}>"

    def get_state(self, fn_code: str) -> BluettiState | None:
        for state in self.states:
            if state.fn_code == fn_code:
                return state
        return None

    async def set_state_value(self, fn_code: str, value: str) -> None:
        state = self.get_state(fn_code)
        if state is None:
            raise ValueError(f"No state with code {fn_code}")
        if self._api_client is None:
            raise RuntimeError("BLUETTI device has no API client attached")

        result = await self._api_client.control_device(
            {"sn": self.device_id, "fnCode": fn_code, "fnValue": value}
        )
        if not result.is_ok():
            raise ApplicationRuntimeException(msgCode=result.msgCode, data=result.data)

        state.set_value(value)
        await self.publish_updates()

    def register_callback(self, callback: StateCallback) -> None:
        self._callbacks.add(callback)

    def remove_callback(self, callback: StateCallback) -> None:
        self._callbacks.discard(callback)

    async def publish_updates(self) -> None:
        for callback in self._callbacks:
            callback()

    @property
    def online(self) -> bool:
        return self.on_line == "1"

    @property
    def battery_level(self) -> int:
        state = self.get_state("SOC")
        if state and state.fn_value:
            return int(state.fn_value)
        return 0

    async def async_update(self) -> None:
        if self._api_client is None:
            raise RuntimeError("BLUETTI device has no API client attached")

        device_status = await self._api_client.get_device_status(self.device_id)
        if not device_status.data:
            return

        data = device_status.data[0]
        if data.sn != self.device_id:
            return

        if data.isBindByCurUser == "0":
            self._handle_unbind()
            return

        self.on_line = data.online
        self._merge_states(data.stateList or [])
        await self.publish_updates()

    def _merge_states(self, state_list: list[dict[str, Any]]) -> None:
        for new_state in state_list:
            existing = self.get_state(new_state["fnCode"])
            if existing is not None:
                existing.fn_value = new_state["fnValue"]
                existing.fn_name = new_state.get("fnName") or existing.fn_name
                existing.fn_type = new_state.get("fnType") or existing.fn_type
                existing.support_mode_values = new_state.get("supportModeValues") or existing.support_mode_values
                existing.sensor_info = new_state.get("sensorInfo") or existing.sensor_info
                continue

            self.states.append(
                BluettiState(
                    fn_code=new_state.get("fnCode"),
                    fn_name=new_state.get("fnName") or "",
                    fn_value=new_state.get("fnValue"),
                    fn_type=new_state.get("fnType"),
                    support_mode_values=new_state.get("supportModeValues"),
                    sensor_info=new_state.get("sensorInfo"),
                )
            )

    def _handle_unbind(self) -> None:
        if self._unbind_processed:
            return
        self._unbind_processed = True
        __LOGGER__.info("Detected device unbinding: %s (%s)", self.name, self.device_id)
        if self._on_device_unbound is not None:
            self._on_device_unbound(self)