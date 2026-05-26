# Roadmap

## Current Baseline
- The initial standalone BLUETTI baseline has been completed and archived.
- The initial standalone BLUETTI baseline is archived at `openspec/changes/archive/2026-05-25-build-local-bluetti-control/`.
- The standalone auth hardening slice is archived at `openspec/changes/archive/2026-05-26-harden-standalone-auth/`.
- The standalone browser OAuth slice is archived at `openspec/changes/archive/2026-05-26-add-standalone-browser-oauth/`.
- The expanded local control surface slice is archived at `openspec/changes/archive/2026-05-26-expand-local-control-surface/`.
- The backend-owned websocket device updates slice is archived at `openspec/changes/archive/2026-05-26-add-websocket-device-updates/`.
- The local operator runtime packaging slice is archived at `openspec/changes/archive/2026-05-26-package-local-operator-runtime/`.
- The live-account verification hardening slice is archived at `openspec/changes/archive/2026-05-26-harden-live-account-verification/`.
- The standalone core surface cleanup slice is archived at `openspec/changes/archive/2026-05-26-simplify-standalone-core-surface/`.
- The self-contained native Swift client kit slice is archived at `openspec/changes/archive/2026-05-26-add-swift-macos-client-kit/`.
- The SwiftUI menu bar sample slice is archived at `openspec/changes/archive/2026-05-26-add-swift-menubar-monitor-sample/`.
- The Swift browser OAuth callback hardening slice is archived at `openspec/changes/archive/2026-05-26-fix-swift-oauth-main-actor-callback/`.
- The menu bar status-item battery percentage follow-up is archived at `openspec/changes/archive/2026-05-26-show-menubar-battery-percentage/`.
- The empty Swift command-response tolerance follow-up is archived at `openspec/changes/archive/2026-05-26-tolerate-empty-command-response/`.
- The repository now includes the standalone core, local backend API, local web control page, refresh-capable token bootstrap, persisted token reuse, token refresh recovery, backend-owned browser OAuth start and callback flow, backend-normalized safe switch-style and select-style controls, synced main capability specs, backend-owned live updates with local SSE fan-out and UI auto-refresh, operator and development startup entrypoints, gated secret-safe live-account verification paths, a repository-local `swift/BluettiKit` package for direct BLUETTI cloud access from Xcode macOS apps, and a copyable `swift/BluettiMonitorSample` SwiftUI menu bar app sample whose browser login returns safely into the app, whose visible status item mirrors the current battery percentage, and whose AC/DC commands tolerate successful empty fulfillment payloads without surfacing a false error.

## Active Workstreams
- The standalone auth path now includes both manual token entry and backend-owned browser OAuth for first-time local setup.
- The current local control surface treats safe switch-style and select-style controls as backend-normalized metadata, while leaving states without verified allowed values read-only.
- Backend-owned live updates now cover backend-managed BLUETTI websocket lifecycle, `/api/live-updates` SSE fan-out, session-level live-update status, and browser-side auto-refresh for visible device cards.
- Backend-owned live updates degrade cleanly to manual refresh when websocket startup, authentication, disconnect, or unsupported `ws://` configuration prevents live delivery.
- The current roadmap focus is extending operator confidence from gated live-account verification toward repeatable end-to-end verification workflows.

## Next Workstreams
- Extend fake-gateway and integration coverage so more end-to-end live-update behavior is verifiable without real-account dependencies.
- Decide whether the next native Apple-platform slice should add websocket live updates or keep the first macOS app on explicit refresh plus command flows.
- Decide whether the menu bar sample should stay a copyable reference only or be promoted into a fuller repository-owned native app target.

## Next Decisions
- Decide whether manual token entry remains a permanent fallback after browser OAuth is live-validated.
- Decide how much callback status detail belongs in the local UI versus backend logs and docs.
- Decide how the packaging slice should balance simple local install ergonomics against future distribution formats.
- Decide whether operator defaults should stay XDG-style across platforms or if macOS-specific application support paths deserve a follow-up slice.
- Decide whether additional read-only BLUETTI telemetry should be surfaced by default or remain behind prioritized device-card selection.
- Decide how the local backend and web UI should be packaged for local operators.
- Decide whether the Swift package should stay as a reusable client kit only or grow a repository-owned macOS app target in a follow-up change.

## Later
- Consolidate repeated fake-gateway verification helpers if the smoke surface grows.
- Extend the fake gateway with websocket notifications if operator-free end-to-end live-update coverage becomes worth the maintenance cost.