# Upstream Provenance

This repository is a standalone BLUETTI connector project based on verified behavior from the official BLUETTI Home Assistant integration. It is not a Home Assistant custom component itself, and it should not be described as an official BLUETTI product unless it is published by the BLUETTI organization.

## Primary References

- Official upstream repository: `https://github.com/bluetti-official/bluetti-home-assistant`
- Stable release baseline: `v1.0.2`, published `2026-03-25`
- Current upstream `main` reference commit used during extraction: `64aa1f85e2eea9c6621cc80d390d7252cd13a83c`, dated `2026-05-19`

## What Was Adapted

The Python core extraction keeps reusable BLUETTI cloud transport, model, profile, and state behavior separate from Home Assistant lifecycle code. The local backend and web page wrap that standalone core for local operator use. The Swift package implements a native client surface against the same verified BLUETTI cloud behavior without calling the Python runtime.

Initial Python extraction targets included these upstream paths:

- `custom_components/bluetti/application_exception.py`
- `custom_components/bluetti/const.py`
- `custom_components/bluetti/api/__init__.py`
- `custom_components/bluetti/api/bluetti.py`
- `custom_components/bluetti/api/product_client.py`
- `custom_components/bluetti/api/unify_response.py`
- `custom_components/bluetti/api/websocket.py`
- `custom_components/bluetti/model/product.py`
- `custom_components/bluetti/profile/application.yaml`
- `custom_components/bluetti/profile/application_profile.py`
- `custom_components/bluetti/models.py`, limited to reusable `BluettiData`, `BluettiDevice`, and `BluettiState` behavior

These upstream files were used as behavioral references rather than direct standalone runtime surfaces:

- `custom_components/bluetti/oauth.py`
- `custom_components/bluetti/__init__.py`
- `custom_components/bluetti/sensor.py`
- `custom_components/bluetti/switch.py`
- `custom_components/bluetti/select.py`

## Verification Mapping

The local fake gateway mirrors these upstream BLUETTI cloud paths and response envelopes for deterministic checks:

- `/api/bluiotdata/ha/v1/devices`
- `/api/bluiotdata/ha/v1/deviceStates`
- `/api/bluiotdata/ha/v1/fulfillment`

The harness keeps `msgId`, `msgCode`, and `data` aligned with the upstream transport contract so local tests remain traceable before live-account verification.

## Attribution Practice

When adapting additional upstream behavior, record the upstream source path, release or commit reference, and whether the local implementation copies code, ports behavior, or only uses the upstream file as a reference. Keep Home Assistant-specific lifecycle behavior out of the standalone core unless a future change explicitly introduces a Home Assistant adapter.
