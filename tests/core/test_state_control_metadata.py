from __future__ import annotations

import pytest

from bluetti_connector.core.models import BluettiDevice, BluettiState


def test_state_marks_telemetry_as_read_only() -> None:
    state = BluettiState(
        fn_code="SOC",
        fn_name="Battery SOC",
        fn_value="55",
        fn_type="number",
        support_mode_values=[],
        sensor_info={"unit": "%"},
    )

    assert state.is_command_capable() is False
    assert state.allowed_values() == []
    assert state.get_name_for_value() == "55"

    with pytest.raises(ValueError, match="read-only"):
        state.validate_value("42")


def test_state_normalizes_switch_control_metadata() -> None:
    state = BluettiState(
        fn_code="SetCtrlAc",
        fn_name="AC",
        fn_value="1",
        fn_type="switch",
        support_mode_values=[],
        sensor_info={},
    )

    assert state.is_command_capable() is True
    assert state.is_switch() is True
    assert state.allowed_values() == [
        {"value": "0", "label": "Off"},
        {"value": "1", "label": "On"},
    ]
    assert state.get_name_for_value() == "On"


def test_state_validates_select_values_against_allowed_options() -> None:
    state = BluettiState(
        fn_code="SetCtrlWorkMode",
        fn_name="Working mode",
        fn_value="workmode_1",
        fn_type="select",
        support_mode_values=[
            {"code": "workmode_1", "name": "Standard UPS"},
            {"code": "workmode_2", "name": "Time Control UPS"},
        ],
        sensor_info={},
    )

    assert state.control_kind() == "select"
    assert state.allowed_values() == [
        {"value": "workmode_1", "label": "Standard UPS"},
        {"value": "workmode_2", "label": "Time Control UPS"},
    ]
    assert state.get_name_for_value() == "Standard UPS"

    state.validate_value("workmode_2")
    state.set_value("workmode_2")

    assert state.fn_value == "workmode_2"
    assert state.get_name_for_value() == "Time Control UPS"

    with pytest.raises(ValueError, match="Invalid value"):
        state.validate_value("workmode_invalid")


def test_device_merge_states_accepts_typed_state_objects() -> None:
    device = BluettiDevice(
        device_id="AC300-TEST-001",
        on_line="0",
        name="Workshop Battery",
        sn="AC300-TEST-001",
        model="AC300",
        state_list=[
            {
                "fnCode": "SOC",
                "fnName": "Battery SOC",
                "fnValue": "55",
                "fnType": "number",
                "supportModeValues": [],
                "sensorInfo": {"unit": "%"},
            }
        ],
    )

    device.merge_states(
        [
            BluettiState(
                fn_code="SOC",
                fn_name="Battery SOC",
                fn_value="61",
                fn_type="number",
                support_mode_values=[],
                sensor_info={"unit": "%"},
            ),
            BluettiState(
                fn_code="SetCtrlAc",
                fn_name="AC Output",
                fn_value="1",
                fn_type="switch",
                support_mode_values=[],
                sensor_info={},
            ),
        ]
    )

    assert device.battery_level == 61
    assert device.get_state("SetCtrlAc") is not None
    assert device.get_state("SetCtrlAc").fn_value == "1"