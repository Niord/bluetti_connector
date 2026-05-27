# Contributing

Thanks for helping improve BLUETTI Connector. This repository touches local tokens, cloud account sessions, and device state, so changes should stay small, traceable, and easy to verify.

## Ground Rules

- Do not commit access tokens, refresh tokens, `.env` files, token stores, local caches, or account-specific logs.
- Redact BLUETTI account details and unnecessary device serial numbers from issues, test fixtures, and screenshots.
- Keep Home Assistant-specific lifecycle behavior out of the standalone core unless a future change explicitly adds an adapter.
- Preserve upstream provenance when adapting behavior from the official BLUETTI Home Assistant integration.
- Prefer focused changes with matching tests or documented verification steps.

## Development Setup

Python development:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
cp .env.example .env
```

Swift package checks:

```bash
cd swift/BluettiKit
swift test
```

See [docs/python.md](docs/python.md), [docs/local-web.md](docs/local-web.md), [docs/swift.md](docs/swift.md), and [docs/macos-sample.md](docs/macos-sample.md) for module-specific details.

## Specs And Change Tracking

The repository uses OpenSpec for non-trivial work. Public capability specs live under `openspec/specs/`, and implementation changes live under `openspec/changes/` until archived.

For non-trivial changes, include:

- a clear proposal or issue describing the behavior or documentation change
- updated specs when requirements change
- focused implementation tasks
- verification commands or a truthful note when a check cannot be run

## Verification

Run the narrowest checks that cover your change. Common checks include:

```bash
.venv/bin/python -m pytest tests/core/test_standalone_core_smoke.py tests/backend/test_backend_smoke.py
.venv/bin/python -m ruff check src/bluetti_connector tests
node --check src/bluetti_connector/web/assets/app.js
node --test tests/web/test_app_live_updates.mjs
cd swift/BluettiKit && swift test
```

Documentation-only changes should still be reviewed for stale commands, broken relative links, and accidental references to private agent context as the only public source.
