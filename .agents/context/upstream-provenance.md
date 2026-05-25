# Upstream Provenance

## Primary References

- Repository: `https://github.com/bluetti-official/bluetti-home-assistant`
- Stable release baseline: `v1.0.2` published `2026-03-25`
- Current upstream `main` reference commit: `64aa1f85e2eea9c6621cc80d390d7252cd13a83c` from `2026-05-19`

## Initial Extraction Targets

- `custom_components/bluetti/application_exception.py` -> standalone exception types
- `custom_components/bluetti/const.py` -> selective transport enums and non-Home-Assistant constants only
- `custom_components/bluetti/api/__init__.py`
- `custom_components/bluetti/api/bluetti.py`
- `custom_components/bluetti/api/product_client.py`
- `custom_components/bluetti/api/unify_response.py`
- `custom_components/bluetti/api/websocket.py`
- `custom_components/bluetti/model/product.py`
- `custom_components/bluetti/profile/application.yaml`
- `custom_components/bluetti/profile/application_profile.py`
- `custom_components/bluetti/models.py` -> extract `BluettiData`, `BluettiDevice`, and `BluettiState` behavior only on the first pass

## Reference Only For The First Pass

- `custom_components/bluetti/oauth.py` -> behavioral reference for standalone auth and token refresh replacement
- `custom_components/bluetti/__init__.py` -> integration lifecycle reference only
- `custom_components/bluetti/sensor.py`, `switch.py`, `select.py` -> Home Assistant adapter references for later backend and UI mapping

## Runtime And Verification Mapping

- Local backend routes `/api/session`, `/api/devices`, `/api/devices/{device_sn}/refresh`, and `/api/devices/{device_sn}/commands` wrap the first-pass extraction built from `custom_components/bluetti/api/bluetti.py` and `custom_components/bluetti/api/product_client.py`.
- The documented verification harness lives in `tests/core/test_standalone_core_smoke.py`, `tests/backend/test_backend_smoke.py`, and `tests/fake_bluetti_gateway.py`.
- The fake gateway intentionally mirrors these upstream cloud paths and response envelopes:
	- `/api/bluiotdata/ha/v1/devices`
	- `/api/bluiotdata/ha/v1/deviceStates`
	- `/api/bluiotdata/ha/v1/fulfillment`
- The harness keeps `msgId`, `msgCode`, and `data` aligned with the upstream transport contract so the standalone runtime stays traceable before live-account validation.

## Notes

- Use release `v1.0.2` as the stable functional baseline when the live `main` branch diverges.
- Compare against upstream `main` for fixes that happened after `v1.0.2`, especially around token refresh and entity state handling.
- When extraction starts, each adapted local module should keep an adjacent note or docstring reference back to its upstream source path.