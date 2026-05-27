## Context

The repository already has three useful but incomplete verification layers for live updates: backend unit-style coverage around `LiveUpdatesManager`, SSE stream coverage around `/api/live-updates`, and a browser-side harness that proves `status` and `device-update` events refresh visible device cards. The remaining gap is end-to-end delivery through the same backend-managed websocket path that production uses, because the fake gateway currently exposes only HTTP endpoints while `LiveUpdatesManager` intentionally refuses non-`wss://` URLs.

This change needs a deterministic repository-local verification path that exercises fake gateway -> backend websocket client -> local SSE fan-out -> browser refresh behavior without introducing a permanent insecure runtime default or depending on live BLUETTI cloud access.

## Goals / Non-Goals

**Goals:**
- Provide a deterministic offline live-update verification flow that runs against the fake gateway instead of a real BLUETTI account.
- Exercise the real backend-managed websocket lifecycle and existing SSE or UI refresh contract end-to-end.
- Keep operator-facing runtime defaults strict so normal runtime behavior remains `wss://`-only unless an explicit local verification gate is enabled.
- Cover both successful live delivery and degraded fallback behavior in focused repository tests.

**Non-Goals:**
- Replace the existing gated live-account verification flow for authenticated upstream checks.
- Add a general-purpose insecure websocket mode for operators.
- Introduce local TLS certificates or a full fake cloud stack if a narrower repository-only gate is sufficient.

## Decisions

### 1. Drive end-to-end verification through a fake STOMP or websocket server instead of injecting live-update callbacks directly
The fake gateway will grow the minimum websocket or STOMP surface needed for the existing `StompClient` to connect, subscribe, and receive a device-update notification.

Why: This keeps the verification path aligned with the production control flow and catches integration regressions across transport setup, `LiveUpdatesManager`, backend stream fan-out, and browser refresh behavior.

Alternative considered: injecting `LiveUpdatesManager._handle_message()` or a fake client directly in integration tests. Rejected because it bypasses the transport seam that currently blocks end-to-end verification.

### 2. Keep insecure local websocket enablement explicit, off by default, and restricted to fake-gateway verification paths
The backend will keep treating `wss://` as the default supported live-update scheme, but repository-local verification can opt into `ws://` only when an explicit setting is enabled and the target is a loopback or fake-gateway endpoint.

Why: The extracted `StompClient` already uses a transport that can connect to `ws://`, so a narrowly gated opt-in is smaller and easier to verify than introducing local TLS. Restricting the override to explicit repository-local verification preserves the current operator safety boundary.

Alternative considered: standing up a local `wss://` fake gateway with certificates. Rejected because it adds certificate and trust-store complexity without improving the verification signal we need right now.

### 3. Reuse the existing local stream and browser refresh contract as the verification target
The offline verification path will continue asserting the current backend-owned `status` and `device-update` event contract and the browser behavior that refreshes only the affected device through backend-owned endpoints.

Why: The SSE and UI contract already exists and is covered in isolation. Reusing it for end-to-end verification closes the gap without creating another live-update surface.

Alternative considered: adding a separate contributor-only debug endpoint for websocket diagnostics. Rejected because it would create another contract to maintain instead of verifying the one the runtime already exposes.

## Risks / Trade-offs

- [The fake websocket surface may drift from BLUETTI's wire behavior] -> Keep the fake gateway protocol surface minimal and only emulate the frames needed by the current `StompClient` contract.
- [A local `ws://` opt-in could accidentally weaken runtime defaults] -> Default the gate to disabled, scope it to repository verification, and reject non-loopback insecure endpoints.
- [Async end-to-end tests can become flaky] -> Use deterministic fake-gateway triggers and explicit waits on SSE or refresh side effects instead of timing-sensitive sleeps.

## Migration Plan

1. Add an explicit repository-local gate for insecure fake-gateway live updates and thread it into the backend live-update setup path.
2. Extend the fake gateway with the minimum websocket notification surface needed to deliver a sanitized device-update event and controlled disconnects.
3. Add focused backend and browser-facing end-to-end tests that verify both successful delivery and degraded fallback.
4. Update contributor documentation, roadmap, and known-issues guidance so the new offline verification path becomes the default repeatable check for live updates.

## Open Questions

- Whether the loopback-only insecure websocket gate should live in general settings or in a narrower test-helper construction path.
- Whether disconnect and reconnect assertions should stay split between Python integration coverage and the existing browser-side harness, or if one broader test should own both concerns.