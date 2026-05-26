## Why

The current standalone baseline only works reliably when a caller supplies a raw access token, which makes repeated local use brittle and leaves token expiry or refresh recovery unresolved. The next change should harden the supported real-account path so a local operator can reuse and recover a BLUETTI session without re-entering tokens for every run.

## What Changes

- Add backend-managed authentication that can bootstrap a BLUETTI session from direct access-token input, optional refresh-token input, or previously stored refresh context.
- Add local token persistence and single-session refresh recovery so the standalone runtime can survive token expiry without immediately forcing manual reconfiguration.
- Extend the local session flow and UI state so the operator can see which token mode is active and when re-authentication is required.
- Add focused verification and documentation for fake-gateway auth harnesses and the documented live-account verification path.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `bluetti-standalone-core`: expand authentication behavior to support direct token bootstrap, persisted token reuse, and refresh-based recovery.
- `local-bluetti-control-ui`: extend the session configuration and auth-state behavior for refresh-capable local operation.

## Impact

- Affects `src/bluetti_connector/config.py`, backend session schemas and service logic, and the extracted core auth path.
- Likely adapts the upstream `custom_components/bluetti/oauth.py` refresh behavior while keeping secrets out of browser code.
- Changes the local web session form and runtime metadata shown to the operator.
- Requires updated smoke coverage and documentation for token persistence and refresh behavior.