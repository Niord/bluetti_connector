# BLUETTI Connector

Standalone BLUETTI connector under extraction from the official Home Assistant integration. The current baseline includes a standalone Python core, a FastAPI backend for session and device operations, a backend-served local web control page, and a deterministic smoke harness for local verification.

## Initial Layout

- `src/bluetti_connector/core/` - standalone BLUETTI core extraction target
- `src/bluetti_connector/backend/` - local FastAPI backend
- `src/bluetti_connector/web/` - backend-served static web files
- `swift/BluettiKit/` - self-contained Swift Package for direct BLUETTI cloud integration from Xcode macOS apps
- `swift/BluettiMonitorSample/` - copyable SwiftUI menu bar sample app built on top of `BluettiKit`
- `tests/core/test_standalone_core_smoke.py` - standalone core smoke flow against a fake BLUETTI gateway
- `tests/backend/test_backend_smoke.py` - backend smoke flow against a fake BLUETTI gateway
- `tests/fake_bluetti_gateway.py` - reusable fake BLUETTI gateway for manual local UI verification
- `openspec/specs/` - current capability specifications for the standalone core and local UI
- `openspec/changes/archive/2026-05-25-build-local-bluetti-control/` - archived implementation change for the baseline extraction
- `.agents/context/upstream-provenance.md` - upstream source mapping for extracted modules

## Quick Start

### Operator Install

1. `python3 -m venv .venv`
2. `source .venv/bin/activate`
3. `python -m pip install --upgrade pip`
4. `python -m pip install .`
5. `mkdir -p ~/.config/bluetti-connector`
6. `cp .env.example ~/.config/bluetti-connector/.env`
7. Fill in the BLUETTI access-token or refresh-token values you want to use locally if you want startup defaults
8. `bluetti-connector`
9. Open `http://127.0.0.1:8080`

By default, the operator runtime reads configuration from `~/.config/bluetti-connector/.env` and persists local session state at `~/.local/state/bluetti-connector/tokens.json`.

### Repository Development

For repository-local iteration with reload enabled:

1. `python3 -m venv .venv`
2. `source .venv/bin/activate`
3. `python -m pip install --upgrade pip`
4. `python -m pip install -e '.[dev]'`
5. `cp .env.example .env`
6. `bluetti-connector-dev`

The development entrypoint keeps the existing repo-local defaults: it reads `.env` from the current working directory and stores session state under `.local/state/bluetti/tokens.json` relative to that directory.

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
- `/api/live-updates` - backend-owned local Server-Sent Events stream for live-update status and sanitized device-change hints
- `/api/verification/live-account` - gated backend-owned live-account verification endpoint with staged sanitized results

## Runtime Settings

The application reads `.env` values with the `BLUETTI_` prefix. The initial bootstrap exposes these settings groups:

- app and server: `BLUETTI_APP_NAME`, `BLUETTI_ENVIRONMENT`, `BLUETTI_SERVER_HOST`, `BLUETTI_SERVER_PORT`, `BLUETTI_DEV_RELOAD`
- BLUETTI cloud endpoints: `BLUETTI_CLOUD_SSO_URL`, `BLUETTI_CLOUD_GATEWAY_URL`, `BLUETTI_CLOUD_WSS_URL`
- session and refresh tokens: `BLUETTI_ACCESS_TOKEN`, `BLUETTI_REFRESH_TOKEN`, `BLUETTI_OAUTH_CLIENT_ID`, `BLUETTI_OAUTH_CLIENT_SECRET`, `BLUETTI_OAUTH_STATE_TTL_SECONDS`, `BLUETTI_TOKEN_STORE_PATH`
- live update and verification gates: `BLUETTI_ENABLE_FAKE_GATEWAY_LIVE_UPDATES`, `BLUETTI_ENABLE_LIVE_ACCOUNT_VERIFICATION`
- runtime behavior: `BLUETTI_REQUEST_TIMEOUT_SECONDS`

Default runtime path behavior now depends on the startup mode:

- `bluetti-connector`: operator defaults from `~/.config/bluetti-connector/.env` and `~/.local/state/bluetti-connector/tokens.json`
- `bluetti-connector-dev`: development defaults from `.env` and `.local/state/bluetti/tokens.json` in the current working directory

Explicit `BLUETTI_*` environment variables still override both modes.

The standalone runtime currently supports direct access tokens, direct refresh tokens, backend-owned browser OAuth, or any persisted combination of those tokens. A live probe against `https://sso.bluettipower.com/oauth2/token` rejected `grant_type=password`, so direct username and password bootstrap is intentionally out of scope.

## Verification

### Automated Smoke Checks

Run the deterministic smoke checks for the extracted core and backend:

```bash
.venv/bin/python -m pytest tests/core/test_standalone_core_smoke.py tests/backend/test_backend_smoke.py
```

These checks use a fake BLUETTI gateway that preserves the first-pass upstream response envelope while verifying device discovery, refresh, richer device payloads, and safe command execution.

Run the focused repository hygiene check for the standalone Python surface:

```bash
.venv/bin/python -m ruff check src/bluetti_connector tests
```

This check keeps the focused backend or core regression harness aligned with the repository's declared Python support contract and catches cleanup regressions that do not immediately surface through smoke behavior.

### Focused Live Update Checks

Run the focused backend and frontend regression checks for backend-owned live updates:

```bash
.venv/bin/python -m pytest tests/backend/test_live_updates_manager.py tests/backend/test_live_updates_stream.py tests/backend/test_backend_session_state.py tests/core/test_websocket_client.py
node --check src/bluetti_connector/web/assets/app.js
node --test tests/web/test_app_live_updates.mjs
```

These checks verify backend websocket lifecycle status, the local SSE stream surface, and the browser-side device-card refresh plus degraded-status UI behavior without requiring a live BLUETTI account.

### Offline Fake-Gateway Live Update Verification

Run the repository-local end-to-end live-update checks against the fake gateway:

```bash
.venv/bin/python -m pytest tests/backend/test_backend_smoke.py -k live_update
```

This check exercises the opt-in loopback `ws://` gate, the fake-gateway websocket or STOMP surface, backend SSE fan-out, and degraded disconnect fallback without requiring real-account `wss://` access.

### Local UI Smoke Harness

Use the reusable fake gateway to validate the browser flow without a real BLUETTI account:

1. Start the fake gateway: `.venv/bin/python tests/fake_bluetti_gateway.py --port 18081`
2. Start the local app from the repository root with loopback fake-gateway live updates enabled: `BLUETTI_ENABLE_FAKE_GATEWAY_LIVE_UPDATES=true bluetti-connector-dev`
3. Open `http://127.0.0.1:8080`
4. Click `Load devices` before configuring a session and confirm the page shows the backend session error
5. Fill the session form with `expired-access-token` as the access token, `test-refresh-token` as the refresh token, `http://127.0.0.1:18081` as Gateway URL, `http://127.0.0.1:18081/sso` as SSO URL, and `ws://127.0.0.1:18081/api/edgeiotgw/ws-coordination` as WebSocket URL
6. Save the session and confirm the page renders `Workshop Battery` even though the initial access token is stale
7. Confirm the runtime panel reports live updates as connected for the loopback fake gateway instead of falling back immediately to manual refresh
8. Trigger a fake disconnect and confirm the runtime panel falls back to degraded or manual-refresh messaging:

```bash
curl -sS -X POST http://127.0.0.1:18081/api/test/live-updates/disconnect
```

9. Optional: publish a fake device-update hint for local experiments:

```bash
curl -sS -X POST http://127.0.0.1:18081/api/test/live-updates/device-update \
	-H 'Content-Type: application/json' \
	-d '{"deviceSn":"AC200L-TEST-001"}'
```

10. Refresh devices, toggle `AC Output`, and change `Working mode`; confirm success feedback and the runtime panel shows that both access and refresh tokens are present

### Browser OAuth Verification

The local session panel now also offers `Connect with BLUETTI`, which sends the current page through `/api/session/oauth/start` and returns through `/api/session/oauth/callback` after BLUETTI login.

For live-account verification:

1. Start the local app with `bluetti-connector` for operator-style runtime defaults, or `bluetti-connector-dev` from the repository root for development-mode defaults
2. Open `http://127.0.0.1:8080`
3. Click `Connect with BLUETTI`
4. Complete BLUETTI login in the browser and confirm the app returns to `/` with a success message and a configured session
5. If BLUETTI rejects the callback or the local redirect URI is not accepted, use the manual token form as a temporary fallback and record the exact failure in `.agents/context/known-issues.md`

### Gated Live-Account Verification

Use this flow only when you explicitly want real-account verification beyond fake-gateway checks.

1. Start the app with real-account session inputs and set `BLUETTI_ENABLE_LIVE_ACCOUNT_VERIFICATION=true`
2. Invoke the verification endpoint:

```bash
curl -sS http://127.0.0.1:8080/api/verification/live-account | python -m json.tool
```

3. Interpret staged results:
- `auth` verifies backend-owned token readiness
- `devices` verifies live account device discovery
- `live-updates` verifies authenticated `wss://` readiness status (`connected`, `degraded`, or `unavailable`)
4. If prerequisites are missing, the endpoint fails fast with `LIVE_VERIFICATION_PREREQUISITES_MISSING` and does not run cloud verification calls.

Failure triage guidance:

- `AUTHENTICATION_EXPIRED`: session refresh failed; reconfigure tokens or rerun browser OAuth
- `BLUETTI_CONNECTIVITY_ERROR` or `BLUETTI_TIMEOUT`: transient network or upstream reachability issue
- `BLUETTI_CLOUD_ERROR`: upstream rejected the operation (`upstreamCode` included without secrets)
- `LIVE_UPDATES_DEGRADED` or `LIVE_UPDATES_UNAVAILABLE`: verify authenticated `wss://` URL and backend live-update status

## Current Scope

Implemented in the current baseline:

- standalone core extraction without `homeassistant` imports
- operator-facing and development-facing local startup commands with deterministic default config and token-store locations
- local backend session setup, refresh-token bootstrap, backend-owned browser OAuth start/callback flow, device listing, device refresh, safe switch-style or select-style command execution, and backend-owned live-update lifecycle management
- backend-served local UI with loading, empty, error, richer device-state display, safe command controls, backend-owned live-update status, and automatic per-device refresh when the backend publishes sanitized device-update events
- deterministic smoke verification against a fake BLUETTI gateway, including token refresh and retry recovery, plus focused backend and frontend regression coverage for browser OAuth, live-update status, SSE fan-out, and UI refresh behavior
- deterministic smoke verification against a fake BLUETTI gateway, including token refresh and retry recovery, plus focused backend and frontend regression coverage for browser OAuth, live-update status, SSE fan-out, loopback fake-gateway websocket delivery, disconnect fallback, and UI refresh behavior
- gated backend-owned live-account verification with fail-fast prerequisite validation and staged sanitized reporting for auth, devices, and live-update readiness
- a repository-local `swift/BluettiKit` package that implements native BLUETTI OAuth, token refresh, device discovery, battery and power helpers, and AC/DC control flow for Xcode-based macOS apps without Python runtime dependencies
- a repository-local `swift/BluettiMonitorSample` menu bar app sample that shows how to use `BluettiKit` from SwiftUI with browser login, device polling, low-battery notifications, device selection, and AC/DC output control

Still intentionally out of scope for the first change:

- default CI execution of live-account verification against real BLUETTI cloud
- free-form numeric or text command entry for BLUETTI states that do not expose safe allowed values in the current snapshot
- native installers, service-manager integration, multi-user behavior, and richer fake-gateway state-mutation tooling beyond the targeted live-update test endpoints