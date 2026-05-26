from __future__ import annotations

from typing import Any, Iterable, Literal

from .application_exception import ApplicationRuntimeException
from .const import MANUFACTURER
from .model.product import UserProduct

StateControlKind = Literal["switch", "select"]


class BluettiData:
    """Standalone container for discovered BLUETTI devices."""

    def __init__(
        self,
        devices: Iterable[UserProduct | dict[str, Any]] | None = None,
    ) -> None:
        self.devices = [BluettiDevice.from_product(device) for device in devices or []]

    def get_device_by_sn(self, sn: str) -> "BluettiDevice | None":
        for device in self.devices:
            if device.device_id == sn:
                return device
        return None

    def attach_api_client(self, api_client: Any) -> None:
        for device in self.devices:
            device.api_client = api_client


class BluettiState:
    @classmethod
    def from_payload(cls, payload: "BluettiState | dict[str, Any]") -> "BluettiState":
        if isinstance(payload, BluettiState):
            return cls(
                fn_code=payload.fn_code,
                fn_name=payload.fn_name,
                fn_value=payload.fn_value,
                fn_type=payload.fn_type,
                support_mode_values=payload.support_mode_values,
                sensor_info=payload.sensor_info,
            )

        return cls(
            fn_code=payload.get("fnCode"),
            fn_name=payload.get("fnName") or "",
            fn_value=payload.get("fnValue"),
            fn_type=payload.get("fnType"),
            support_mode_values=payload.get("supportModeValues"),
            sensor_info=payload.get("sensorInfo"),
        )

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

    def control_kind(self) -> StateControlKind | None:
        fn_type = (self.fn_type or "").lower()
        if "switch" in fn_type:
            return "switch"
        if self.support_mode_values:
            return "select"
        return None

    def is_command_capable(self) -> bool:
        return self.control_kind() is not None

    def is_switch(self) -> bool:
        return self.control_kind() == "switch"

    def allowed_values(self) -> list[dict[str, str]]:
        options = [
            {
                "value": str(option.get("code")),
                "label": str(option.get("name") or option.get("code")),
            }
            for option in self.support_mode_values
            if option.get("code") is not None
        ]
        if options:
            return options
        if self.is_switch():
            return [
                {"value": "0", "label": "Off"},
                {"value": "1", "label": "On"},
            ]
        return []

    def validate_value(self, value: str) -> None:
        if not self.is_command_capable():
            raise ValueError(f"State {self.fn_code} is read-only")
        if any(option["value"] == value for option in self.allowed_values()):
            return
        raise ValueError(f"Invalid value {value} for {self.fn_code}")

    def set_value(self, value: str) -> None:
        self.validate_value(value)
        self.fn_value = value

    def merge(self, state: "BluettiState") -> None:
        self.fn_value = state.fn_value
        self.fn_name = state.fn_name or self.fn_name
        self.fn_type = state.fn_type or self.fn_type
        self.support_mode_values = state.support_mode_values or self.support_mode_values
        self.sensor_info = state.sensor_info or self.sensor_info

    def get_name_for_value(self) -> str:
        for option in self.allowed_values():
            if option["value"] == self.fn_value:
                return option["label"]
        if self.fn_value is not None and self.fn_value != "":
            return self.fn_value
        return "Unknown"

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
        api_client: Any | None = None,
    ) -> None:
        self.device_id = device_id
        self.on_line = on_line
        self.name = name or sn
        self.sn = sn
        self.model = model
        self.manufacturer = MANUFACTURER
        self._api_client = api_client
        self.states = [BluettiState.from_payload(state) for state in state_list or []]

    @classmethod
    def from_product(
        cls,
        product: UserProduct | dict[str, Any],
        api_client: Any | None = None,
    ) -> "BluettiDevice":
        product_model = product if isinstance(product, UserProduct) else UserProduct.model_validate(product)
        return cls(
            device_id=product_model.sn,
            on_line=product_model.online or "0",
            name=product_model.name,
            sn=product_model.sn,
            model=product_model.model,
            state_list=product_model.stateList or [],
            api_client=api_client,
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

        state.validate_value(value)

        result = await self._api_client.control_device(
            {"sn": self.device_id, "fnCode": fn_code, "fnValue": value}
        )
        if not result.is_ok():
            raise ApplicationRuntimeException(msgCode=result.msgCode, data=result.data)

        state.set_value(value)

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
            return

        self.on_line = data.online
        self.merge_states(data.stateList or [])

    def merge_states(self, state_list: Iterable[BluettiState | dict[str, Any]]) -> None:
        for payload in state_list:
            new_state = BluettiState.from_payload(payload)
            existing = self.get_state(new_state.fn_code)
            if existing is not None:
                existing.merge(new_state)
                continue

            self.states.append(new_state)