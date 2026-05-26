# Roadmap

## Current Baseline
- The initial standalone BLUETTI baseline has been completed and archived.
- The initial standalone BLUETTI baseline is archived at `openspec/changes/archive/2026-05-25-build-local-bluetti-control/`.
- The standalone auth hardening slice is archived at `openspec/changes/archive/2026-05-26-harden-standalone-auth/`.
- The repository now includes the standalone core, local backend API, local web control page, refresh-capable token bootstrap, persisted token reuse, token refresh recovery, main capability specs, and a documented fake-gateway smoke harness.

## Active Workstreams
- No active OpenSpec change is open after `harden-standalone-auth` archives.
- The current standalone auth path works with direct access and refresh tokens plus the local token store.
- Manual token entry remains the main operator friction until browser-based OAuth is implemented.

## Next Workstreams
- Implement a standalone browser-based OAuth login flow so the operator can authenticate in the local app without manually pasting access or refresh tokens.
- Define the local callback and backend-owned authorization-code exchange needed for that browser OAuth flow.
- Validate the standalone auth and token refresh path against a real BLUETTI account after the browser OAuth slice exists.
- Decide the next safe command expansion and whether polling remains sufficient or websocket push is required.

## Next Decisions
- Define the standalone browser OAuth UX, callback routing, and local-only trust boundaries.
- Decide how the backend should persist callback state, refresh tokens, and token-store invalidation during re-auth.
- Choose the first post-browser-OAuth slice: broader command coverage, websocket updates, or packaging.
- Decide how the local backend and web UI should be packaged for local operators.

## Later
- Consolidate repeated fake-gateway verification helpers if the smoke surface grows.
- Evaluate websocket-driven updates after the polling-based local control slice is stable.