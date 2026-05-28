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
- The fake-gateway live-update verification slice is archived at `openspec/changes/archive/2026-05-27-add-fake-gateway-live-updates-e2e/`.
- The native Swift live-update slice is archived at `openspec/changes/archive/2026-05-27-add-swift-live-device-updates/`.
- The public repository documentation readiness slice is archived at `openspec/changes/archive/2026-05-27-prepare-public-repository-docs/`.
- The public repository automation slice is archived at `openspec/changes/archive/2026-05-27-add-public-repo-automation/`.
- The repository now includes the standalone core, local backend API, local web control page, refresh-capable token bootstrap, persisted token reuse, token refresh recovery, backend-owned browser OAuth start and callback flow, backend-normalized safe switch-style and select-style controls, synced main capability specs, backend-owned live updates with local SSE fan-out and UI auto-refresh, operator and development startup entrypoints, gated secret-safe live-account verification paths, deterministic repository-local fake-gateway live-update verification with an explicit loopback `ws://` opt-in, a repository-local `swift/BluettiKit` package for direct BLUETTI cloud access from Xcode macOS apps with native live-update status and device-update hints, and a copyable `swift/BluettiMonitorSample` SwiftUI menu bar app sample whose browser login returns safely into the app, whose visible status item mirrors the current battery percentage, whose selected device refreshes from matching native live-update hints, whose UI surfaces degraded live status, and whose AC/DC commands tolerate successful empty fulfillment payloads without surfacing a false error.
- The repository now also includes a public documentation surface with a concise root README, module-specific docs under `docs/`, public upstream attribution, and lightweight contribution or security guidance suitable for a public repository.
- The repository now also includes a public GitHub Actions CI workflow, structured issue or pull-request templates, README badges, and package metadata links for `https://github.com/Niord/bluetti_connector`.

## Active Workstreams
- The standalone auth path now includes both manual token entry and backend-owned browser OAuth for first-time local setup.
- The current local control surface treats safe switch-style and select-style controls as backend-normalized metadata, while leaving states without verified allowed values read-only.
- Backend-owned live updates now cover backend-managed BLUETTI websocket lifecycle, `/api/live-updates` SSE fan-out, session-level live-update status, and browser-side auto-refresh for visible device cards.
- Repository-local fake-gateway verification now covers opt-in loopback `ws://` delivery, backend SSE fan-out, and degraded disconnect fallback without real-account dependencies.
- Backend-owned live updates still degrade cleanly to manual refresh when websocket startup, authentication, disconnect, or unsupported non-loopback `ws://` configuration prevents live delivery.
- The public repository automation now keeps Python and web checks on a cheap Linux workflow, runs the macOS Swift workflow only for Swift-related changes or manual dispatch, cancels superseded runs on the same ref, and caps the Swift job runtime while still using `swift build --build-tests` plus explicit `xcrun xctest` and the synchronized native live-update tests.
- The current roadmap focus is extending operator confidence from gated live-account verification toward repeatable end-to-end verification workflows.

## Next Workstreams
- Broaden fake-gateway verification from the current backend-stream and targeted browser harness coverage into richer operator-facing flows only if the added maintenance remains justified.
- Decide whether the menu bar sample should stay a copyable reference only or be promoted into a fuller repository-owned native app target.

## Next Decisions
- Decide whether the next public-polish slice should add release packaging metadata, contributor automation beyond templates, or broader repository-health surfaces.
- Decide whether the first public automation workflow should later split into separate Python or web and Swift workflows or stay as one repository CI surface.
- Decide whether manual token entry remains a permanent fallback after browser OAuth is live-validated.
- Decide how much callback status detail belongs in the local UI versus backend logs and docs.
- Decide how the packaging slice should balance simple local install ergonomics against future distribution formats.
- Decide whether operator defaults should stay XDG-style across platforms or if macOS-specific application support paths deserve a follow-up slice.
- Decide whether additional read-only BLUETTI telemetry should be surfaced by default or remain behind prioritized device-card selection.
- Decide how the local backend and web UI should be packaged for local operators.
- Decide whether the Swift package should stay as a reusable client kit only or grow a repository-owned macOS app target beyond the current menu bar sample follow-up.

## Later
- Consolidate repeated fake-gateway verification helpers if the smoke surface grows.
- Broaden the fake gateway control endpoints if multi-device or richer operator-free live-update scenarios become worth the maintenance cost.