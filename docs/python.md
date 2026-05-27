# Python Backend And Package

The Python package provides the standalone BLUETTI core extraction, a FastAPI backend, and CLI entry points for local operation.

## Package Layout

- `src/bluetti_connector/core/` contains reusable BLUETTI transport, profile, model, websocket, and command behavior.
- `src/bluetti_connector/backend/` contains the local FastAPI application, session handling, token persistence, browser OAuth callback handling, device operations, and live-update fan-out.
- `src/bluetti_connector/web/` contains the static browser page served by the backend.
- `tests/` contains deterministic fake-gateway, backend, core, and web checks.

## Operator Install

Use this path when you want the runtime to read config and store session state outside the repository.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
mkdir -p ~/.config/bluetti-connector
cp .env.example ~/.config/bluetti-connector/.env
bluetti-connector
```

Open `http://127.0.0.1:8080` after the server starts.

Operator defaults:

- Config file: `~/.config/bluetti-connector/.env`
- Token store: `~/.local/state/bluetti-connector/tokens.json`

## Repository Development

Use this path for local development with editable installs and reload enabled.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
cp .env.example .env
bluetti-connector-dev
```

Development defaults:

- Config file: `.env` in the repository root
- Token store: `.local/state/bluetti/tokens.json`
- Reload: enabled through `BLUETTI_DEV_RELOAD=true`

## Configuration

Configuration is read from environment variables with the `BLUETTI_` prefix. Explicit environment variables override values loaded from the active `.env` file.

Common settings:

- `BLUETTI_SERVER_HOST` and `BLUETTI_SERVER_PORT` control the local backend listener.
- `BLUETTI_CLOUD_SSO_URL`, `BLUETTI_CLOUD_GATEWAY_URL`, and `BLUETTI_CLOUD_WSS_URL` point at BLUETTI cloud endpoints.
- `BLUETTI_ACCESS_TOKEN` and `BLUETTI_REFRESH_TOKEN` can seed a local session.
- `BLUETTI_OAUTH_CLIENT_ID` and `BLUETTI_OAUTH_CLIENT_SECRET` configure the browser OAuth client values used by the local backend.
- `BLUETTI_TOKEN_STORE_PATH` overrides the default token-store path.
- `BLUETTI_ENABLE_LIVE_ACCOUNT_VERIFICATION=true` enables the gated live-account verification endpoint.
- `BLUETTI_ENABLE_FAKE_GATEWAY_LIVE_UPDATES=true` enables repository-local loopback `ws://` fake-gateway live updates.

Do not commit `.env`, token-store files, access tokens, refresh tokens, account identifiers, or unnecessary device serial numbers.

## Backend Routes

The backend serves the local page and exposes local API routes:

- `/` local browser page
- `/health` runtime health snapshot
- `/api/bootstrap` sanitized bootstrap metadata
- `/api/session` session status and setup
- `/api/session/oauth/start` browser OAuth start
- `/api/session/oauth/callback` browser OAuth callback
- `/api/devices` device discovery
- `/api/devices/{device_sn}/refresh` device state refresh
- `/api/devices/{device_sn}/commands` safe command execution
- `/api/live-updates` local Server-Sent Events stream
- `/api/verification/live-account` gated live-account verification

## Automated Checks

Run focused Python checks from the repository root after installing development dependencies:

```bash
.venv/bin/python -m pytest tests/core/test_standalone_core_smoke.py tests/backend/test_backend_smoke.py
.venv/bin/python -m pytest tests/backend/test_live_updates_manager.py tests/backend/test_live_updates_stream.py tests/backend/test_backend_session_state.py tests/core/test_websocket_client.py
.venv/bin/python -m ruff check src/bluetti_connector tests
```

The local web JavaScript checks are documented in [local-web.md](local-web.md).
