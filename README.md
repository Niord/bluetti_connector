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
6. Fill in the BLUETTI access-token or refresh-token values you want to use locally if you want startup defaults
7. `bluetti-connector-dev`
8. Open `http://127.0.0.1:8080`

The local server binds to `http://127.0.0.1:8080` by default and serves:

- `/` - local web control page
- `/health` - runtime health snapshot
- `/api/bootstrap` - sanitized bootstrap metadata for local development
- `/api/session` - current backend session snapshot and session setup
- `/api/session/oauth/start` - backend-owned browser OAuth start route
- `/api/session/oauth/callback` - backend-owned browser OAuth callback route
- `/api/devices` - discovered BLUETTI devices for the current session
- `/api/devices/{device_sn}/refresh` - device state refresh through the backend
- `/api/devices/{device_sn}/commands` - safe switch-style and select-style command execution through the backend

## Runtime Settings

The application reads `.env` values with the `BLUETTI_` prefix. The initial bootstrap exposes these settings groups:

- app and server: `BLUETTI_APP_NAME`, `BLUETTI_ENVIRONMENT`, `BLUETTI_SERVER_HOST`, `BLUETTI_SERVER_PORT`, `BLUETTI_DEV_RELOAD`
- BLUETTI cloud endpoints: `BLUETTI_CLOUD_SSO_URL`, `BLUETTI_CLOUD_GATEWAY_URL`, `BLUETTI_CLOUD_WSS_URL`
- session and refresh tokens: `BLUETTI_ACCESS_TOKEN`, `BLUETTI_REFRESH_TOKEN`, `BLUETTI_OAUTH_CLIENT_ID`, `BLUETTI_OAUTH_CLIENT_SECRET`, `BLUETTI_OAUTH_STATE_TTL_SECONDS`, `BLUETTI_TOKEN_STORE_PATH`
- runtime behavior: `BLUETTI_REQUEST_TIMEOUT_SECONDS`

The standalone runtime currently supports direct access tokens, direct refresh tokens, backend-owned browser OAuth, or any persisted combination of those tokens. A live probe against `https://sso.bluettipower.com/oauth2/token` rejected `grant_type=password`, so direct username and password bootstrap is intentionally out of scope.

## Verification

### Automated Smoke Checks

Run the deterministic smoke checks for the extracted core and backend:

```bash
.venv/bin/python -m pytest tests/core/test_standalone_core_smoke.py tests/backend/test_backend_smoke.py
```

These checks use a fake BLUETTI gateway that preserves the first-pass upstream response envelope while verifying device discovery, refresh, richer device payloads, and safe command execution.

### Local UI Smoke Harness

Use the reusable fake gateway to validate the browser flow without a real BLUETTI account:

1. Start the fake gateway: `.venv/bin/python tests/fake_bluetti_gateway.py --port 18081`
2. Start the local app: `bluetti-connector-dev`
3. Open `http://127.0.0.1:8080`
4. Click `Load devices` before configuring a session and confirm the page shows the backend session error
5. Fill the session form with `expired-access-token` as the access token, `test-refresh-token` as the refresh token, `http://127.0.0.1:18081` as Gateway URL, `http://127.0.0.1:18081/sso` as SSO URL, and `ws://127.0.0.1/unused` as WebSocket URL
6. Save the session and confirm the page renders `Workshop Battery` even though the initial access token is stale
7. Refresh devices, toggle `AC Output`, and change `Working mode`; confirm success feedback and the runtime panel shows that both access and refresh tokens are present

### Browser OAuth Verification

The local session panel now also offers `Connect with BLUETTI`, which sends the current page through `/api/session/oauth/start` and returns through `/api/session/oauth/callback` after BLUETTI login.

For live-account verification:

1. Start the local app: `bluetti-connector-dev`
2. Open `http://127.0.0.1:8080`
3. Click `Connect with BLUETTI`
4. Complete BLUETTI login in the browser and confirm the app returns to `/` with a success message and a configured session
5. If BLUETTI rejects the callback or the local redirect URI is not accepted, use the manual token form as a temporary fallback and record the exact failure in `.agents/context/known-issues.md`

## Current Scope

Implemented in the current baseline:

- standalone core extraction without `homeassistant` imports
- local backend session setup, refresh-token bootstrap, backend-owned browser OAuth start/callback flow, device listing, device refresh, and safe switch-style or select-style command execution
- backend-served local UI with loading, empty, error, richer device-state display, and command feedback states
- deterministic smoke verification against a fake BLUETTI gateway, including token refresh and retry recovery, command-state classification, and focused backend coverage for browser OAuth state and callback exchange

Still intentionally out of scope for the first change:

- automated verification against a real BLUETTI account
- free-form numeric or text command entry for BLUETTI states that do not expose safe allowed values in the current snapshot
- production packaging, multi-user behavior, and websocket-first updates