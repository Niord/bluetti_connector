## Why

The current standalone runtime is still shaped like a repository-local development app: it starts through `bluetti-connector-dev`, reads `.env` from the current working directory, and persists token state under a relative `.local/state/...` path. Now that the local UI, backend-owned OAuth, and live updates are working, the next gap is a repeatable operator install that behaves consistently outside a repo checkout.

## What Changes

- Add an operator-oriented runtime packaging contract with a stable non-dev entrypoint for starting the local backend and web UI.
- Resolve configuration and persisted session state from deterministic application directories instead of the current working directory by default, while preserving explicit environment overrides.
- Preserve the existing development-oriented launch flow for local repository work.
- Document repeatable install, runtime, and persistence expectations for local operators.

## Capabilities

### New Capabilities
- `local-operator-runtime`: Operator-facing runtime packaging, startup, and persistence contract for the standalone local backend and web UI.

### Modified Capabilities
None.

## Impact

- `pyproject.toml` scripts and packaging metadata
- `src/bluetti_connector/config.py` and CLI/runtime startup paths
- persisted token-store and config path resolution
- runtime documentation and focused packaging verification