# Roadmap

## Current Baseline
- No active OpenSpec changes are currently open.
- The initial standalone BLUETTI baseline is archived at `openspec/changes/archive/2026-05-25-build-local-bluetti-control/`.
- The repository now includes the standalone core, local backend API, local web control page, main capability specs, and a documented fake-gateway smoke harness.

## Next Workstreams
- Validate the standalone auth and token refresh path against a real BLUETTI account now that deterministic local verification exists.
- Decide the next safe command expansion and whether polling remains sufficient or websocket push is required.

## Next Decisions
- Define the standalone authentication approach and token persistence model for non-test usage.
- Choose the first post-baseline slice: broader command coverage, live-auth hardening, or periodic auto-refresh.
- Decide how the local backend and web UI should be packaged for local operators.

## Later
- Consolidate repeated fake-gateway verification helpers if the smoke surface grows.
- Evaluate websocket-driven updates after the polling-based local control slice is stable.