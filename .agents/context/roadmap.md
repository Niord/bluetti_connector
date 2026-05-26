# Roadmap

## Current Baseline
- The initial standalone BLUETTI baseline has been completed and archived.
- The initial standalone BLUETTI baseline is archived at `openspec/changes/archive/2026-05-25-build-local-bluetti-control/`.
- The standalone auth hardening slice is archived at `openspec/changes/archive/2026-05-26-harden-standalone-auth/`.
- The standalone browser OAuth slice is archived at `openspec/changes/archive/2026-05-26-add-standalone-browser-oauth/`.
- The expanded local control surface slice is archived at `openspec/changes/archive/2026-05-26-expand-local-control-surface/`.
- The backend-owned websocket device updates slice is archived at `openspec/changes/archive/2026-05-26-add-websocket-device-updates/`.
- The repository now includes the standalone core, local backend API, local web control page, refresh-capable token bootstrap, persisted token reuse, token refresh recovery, backend-owned browser OAuth start and callback flow, backend-normalized safe switch-style and select-style controls, synced main capability specs, backend-owned live updates with local SSE fan-out and UI auto-refresh, and documented fake-gateway plus live local-operator verification paths.

## Active Workstreams
- The standalone auth path now includes both manual token entry and backend-owned browser OAuth for first-time local setup.
- The current local control surface treats safe switch-style and select-style controls as backend-normalized metadata, while leaving states without verified allowed values read-only.
- Backend-owned live updates now cover backend-managed BLUETTI websocket lifecycle, `/api/live-updates` SSE fan-out, session-level live-update status, and browser-side auto-refresh for visible device cards.
- Backend-owned live updates degrade cleanly to manual refresh when websocket startup, authentication, disconnect, or unsupported `ws://` configuration prevents live delivery.
- The next roadmap focus is packaging the local backend and web UI for repeatable operator installation and persisted local runtime use.

## Next Workstreams
- Package the local backend and web UI for repeatable operator installation and persisted local runtime use.
- Add a trustworthy live-account verification strategy beyond manual operator smoke runs.

## Next Decisions
- Decide whether manual token entry remains a permanent fallback after browser OAuth is live-validated.
- Decide how much callback status detail belongs in the local UI versus backend logs and docs.
- Decide how the packaging slice should balance simple local install ergonomics against future distribution formats.
- Decide whether additional read-only BLUETTI telemetry should be surfaced by default or remain behind prioritized device-card selection.
- Decide how the local backend and web UI should be packaged for local operators.

## Later
- Consolidate repeated fake-gateway verification helpers if the smoke surface grows.
- Extend the fake gateway with websocket notifications if operator-free end-to-end live-update coverage becomes worth the maintenance cost.