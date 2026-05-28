# BLUETTI Connector

[![Python and Web CI](https://github.com/Niord/bluetti_connector/actions/workflows/ci.yml/badge.svg)](https://github.com/Niord/bluetti_connector/actions/workflows/ci.yml)
[![Swift CI](https://github.com/Niord/bluetti_connector/actions/workflows/swift.yml/badge.svg)](https://github.com/Niord/bluetti_connector/actions/workflows/swift.yml)
[![License](https://img.shields.io/github/license/Niord/bluetti_connector)](https://github.com/Niord/bluetti_connector/blob/main/LICENSE)

BLUETTI Connector is a standalone project for working with BLUETTI cloud-connected power devices outside the Home Assistant runtime. The repository contains a Python connector and local backend, a backend-served browser page for local testing and control, a native Swift package, and a SwiftUI macOS menu bar sample.

The work is based on verified behavior from the official BLUETTI Home Assistant integration. See [docs/upstream.md](docs/upstream.md) and [NOTICE](NOTICE) for provenance, attribution, and source-mapping details.

Repository: [github.com/Niord/bluetti_connector](https://github.com/Niord/bluetti_connector) | Issues: [GitHub Issues](https://github.com/Niord/bluetti_connector/issues)

## Repository Status

This repository is an early standalone extraction and client toolkit. It is useful for local development, integration experiments, and reference implementations, but it does not yet provide packaged installers, CI release automation, or a production macOS distribution.

## Modules

| Area | Path | Documentation |
| --- | --- | --- |
| Python core and FastAPI backend | `src/bluetti_connector/` | [docs/python.md](docs/python.md) |
| Backend-served browser page | `src/bluetti_connector/web/` | [docs/local-web.md](docs/local-web.md) |
| Native Swift client package | `swift/BluettiKit/` | [docs/swift.md](docs/swift.md) |
| SwiftUI macOS menu bar sample | `swift/BluettiMonitorSample/` | [docs/macos-sample.md](docs/macos-sample.md) |
| OpenSpec capability specs | `openspec/specs/` | [CONTRIBUTING.md](CONTRIBUTING.md) |

## Quick Start: Python Backend And Browser Page

For repository-local development:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
cp .env.example .env
bluetti-connector-dev
```

Open `http://127.0.0.1:8080` after the server starts.

For operator-style local installs, use `python -m pip install .` and run `bluetti-connector`. Operator mode reads config from `~/.config/bluetti-connector/.env` and stores local session state under `~/.local/state/bluetti-connector/tokens.json`.

Detailed Python setup, configuration, backend routes, and checks are in [docs/python.md](docs/python.md). Local browser-page and fake-gateway verification details are in [docs/local-web.md](docs/local-web.md).

## Quick Start: Swift

Build and test the Swift package:

```bash
cd swift/BluettiKit
swift build
swift test
```

Build the macOS sample:

```bash
cd swift/BluettiMonitorSample
swift build
```

For Xcode integration, add `swift/BluettiKit` as a local package dependency and register a custom URL scheme for browser OAuth callbacks. See [docs/swift.md](docs/swift.md) and [docs/macos-sample.md](docs/macos-sample.md).

## Configuration And Secrets

The Python runtime reads `BLUETTI_*` settings from the active environment or `.env` file. `.env.example` documents the supported settings.

Do not commit:

- `.env` files
- `.local/` state
- access tokens or refresh tokens
- token-store files
- account-specific logs
- unnecessary device serial numbers

The browser page only talks to the local backend. BLUETTI tokens and cloud calls stay on the server side.

## Verification

Common focused checks:

```bash
.venv/bin/python -m pytest tests/core/test_standalone_core_smoke.py tests/backend/test_backend_smoke.py
.venv/bin/python -m ruff check src/bluetti_connector tests
node --check src/bluetti_connector/web/assets/app.js
node --test tests/web/test_app_live_updates.mjs
cd swift/BluettiKit && swift test
```

The fake BLUETTI gateway in `tests/fake_bluetti_gateway.py` supports deterministic local UI and live-update verification without a real BLUETTI account. See [docs/local-web.md](docs/local-web.md) for the full flow.

## Public Project Files

- [LICENSE](LICENSE) contains the project license.
- [NOTICE](NOTICE) records BLUETTI upstream attribution.
- [CONTRIBUTING.md](CONTRIBUTING.md) describes development and verification expectations.
- [SECURITY.md](SECURITY.md) explains how to report sensitive issues without exposing tokens or account data.
- [Python and Web CI](https://github.com/Niord/bluetti_connector/actions/workflows/ci.yml) runs the deterministic Linux-based Python and browser checks on each push and pull request.
- [Swift CI](https://github.com/Niord/bluetti_connector/actions/workflows/swift.yml) runs the macOS Swift checks only for Swift-related changes, workflow edits, or explicit manual dispatch so the repository keeps public Swift coverage without paying macOS minutes for unrelated pushes.
