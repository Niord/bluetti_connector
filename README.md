# BLUETTI Connector

Standalone BLUETTI connector under extraction from the official Home Assistant integration. The current baseline includes a standalone Python core, a FastAPI backend for session and device operations, a backend-served local web control page, and a deterministic smoke harness for local verification.

## Initial Layout

- `src/bluetti_connector/core/` - standalone BLUETTI core extraction target
- `src/bluetti_connector/backend/` - local FastAPI backend
- `src/bluetti_connector/web/` - backend-served static web files
- `tests/core/test_standalone_core_smoke.py` - standalone core smoke flow against a fake BLUETTI gateway
- `tests/backend/test_backend_smoke.py` - backend smoke flow against a fake BLUETTI gateway
- `tests/fake_bluetti_gateway.py` - reusable fake BLUETTI gateway for manual local UI verification
- `openspec/specs/` - current capability specifications for the standalone core and local UI
- `openspec/changes/archive/2026-05-25-build-local-bluetti-control/` - archived implementation change for the baseline extraction
- `.agents/context/upstream-provenance.md` - upstream source mapping for extracted modules

## Quick Start

1. `python3 -m venv .venv`
2. `source .venv/bin/activate`
3. `python -m pip install --upgrade pip`
4. `python -m pip install -e '.[dev]'`
5. `cp .env.example .env`
6. Fill in the BLUETTI credentials or token values you want to use locally if you want startup defaults
7. `bluetti-connector-dev`
8. Open `http://127.0.0.1:8080`

The local server binds to `http://127.0.0.1:8080` by default and serves:

- `/` - local web control page
- `/health` - runtime health snapshot
- `/api/bootstrap` - sanitized bootstrap metadata for local development
- `/api/session` - current backend session snapshot and session setup
- `/api/devices` - discovered BLUETTI devices for the current session
- `/api/devices/{device_sn}/refresh` - device state refresh through the backend
- `/api/devices/{device_sn}/commands` - initial safe command execution through the backend

## Runtime Settings

The application reads `.env` values with the `BLUETTI_` prefix. The initial bootstrap exposes these settings groups:

- app and server: `BLUETTI_APP_NAME`, `BLUETTI_ENVIRONMENT`, `BLUETTI_SERVER_HOST`, `BLUETTI_SERVER_PORT`, `BLUETTI_DEV_RELOAD`
- BLUETTI cloud endpoints: `BLUETTI_CLOUD_SSO_URL`, `BLUETTI_CLOUD_GATEWAY_URL`, `BLUETTI_CLOUD_WSS_URL`
- credentials and tokens: `BLUETTI_USERNAME`, `BLUETTI_PASSWORD`, `BLUETTI_ACCESS_TOKEN`, `BLUETTI_REFRESH_TOKEN`, `BLUETTI_TOKEN_STORE_PATH`
- runtime behavior: `BLUETTI_REQUEST_TIMEOUT_SECONDS`

## Verification

### Automated Smoke Checks

Run the deterministic smoke checks for the extracted core and backend:

```bash
.venv/bin/python -m pytest tests/core/test_standalone_core_smoke.py tests/backend/test_backend_smoke.py
```

These checks use a fake BLUETTI gateway that preserves the first-pass upstream response envelope while verifying device discovery, refresh, and command execution.

### Local UI Smoke Harness

Use the reusable fake gateway to validate the browser flow without a real BLUETTI account:

1. Start the fake gateway: `.venv/bin/python tests/fake_bluetti_gateway.py --port 18081`
2. Start the local app: `bluetti-connector-dev`
3. Open `http://127.0.0.1:8080`
4. Click `Load devices` before configuring a session and confirm the page shows the backend session error
5. Fill the session form with any non-empty access token, `http://127.0.0.1:18081` as Gateway URL, `http://127.0.0.1:18081/sso` as SSO URL, and `ws://127.0.0.1/unused` as WebSocket URL
6. Save the session and confirm the page renders `Workshop Battery`
7. Refresh devices and toggle `AC Output`; confirm success feedback and the button label changes between on and off

## Current Scope

Implemented in the current baseline:

- standalone core extraction without `homeassistant` imports
- local backend session setup, device listing, device refresh, and initial command execution
- backend-served local UI with loading, empty, error, and command feedback states
- deterministic smoke verification against a fake BLUETTI gateway

Still intentionally out of scope for the first change:

- automated verification against a real BLUETTI account
- broader command coverage beyond the initial safe switch-style controls
- production packaging, multi-user behavior, and websocket-first updates