## Context

`BluettiKit` currently owns only HTTP-based auth, device refresh, and command flows, while `BluettiMonitorSample` keeps device state fresh through a polling task. The repository already has a verified BLUETTI websocket or STOMP path on the Python side, so the next native gap is not cloud contract uncertainty but bringing a comparable live-update path into the Swift package and sample app without giving up the current explicit refresh and auth-recovery behavior.

The change is cross-cutting because it touches transport inside `BluettiKit`, app-facing state in the sample view model, Swift tests, and sample documentation. It also needs a clear choice about how much websocket detail should surface to app code versus staying internal to the package.

## Goals / Non-Goals

**Goals:**
- Add native BLUETTI live-update support to `BluettiKit` without introducing a Python runtime dependency.
- Expose a high-level Swift live-update surface that app code can consume without parsing raw websocket or STOMP frames.
- Update the menu bar sample to use live updates for targeted device refresh while keeping explicit refresh or polling fallback when live delivery is unavailable.
- Keep Swift validation focused and repository-local through package tests and sample behavior checks.

**Non-Goals:**
- Mirroring the Python backend SSE surface inside Swift.
- Delivering raw full device state through websocket messages when a sanitized device-update hint plus refresh path is sufficient.
- Replacing every fallback path with always-on websocket behavior; manual refresh and fallback polling remain valid.

## Decisions

### 1. Implement a minimal internal STOMP-over-WebSocket client inside `BluettiKit`
`BluettiKit` will add an internal websocket session component built on `URLSessionWebSocketTask` that handles BLUETTI connection setup, STOMP handshake, subscription, heartbeats, and disconnect callbacks without pulling in a new third-party dependency.

Why: The existing Swift package already relies on Foundation networking only, and the repository already knows the minimum BLUETTI websocket contract from the extracted Python path. Keeping the STOMP layer internal avoids exposing protocol details or widening the package dependency surface.

Alternative considered: adopting an external Swift STOMP library. Rejected because it adds maintenance and packaging cost for a narrow protocol surface the repository already understands.

### 2. Expose sanitized live-update events and status through `BluettiClient`, not raw frames
The package will surface a high-level live-update contract centered on status transitions and device serial-number hints, while keeping raw websocket payloads, frame parsing, and reconnect details internal.

Why: The sample app only needs to know whether live updates are connected, degraded, or disabled and which device should be refreshed. This matches the existing backend-owned live-update shape and preserves flexibility inside the package.

Alternative considered: exposing raw websocket callbacks or STOMP frame handlers to app code. Rejected because it leaks transport details into the app layer and makes the menu bar sample responsible for protocol handling.

### 3. Switch the sample app to live-first refresh with fallback polling
`BluettiMonitorSample` will subscribe to the `BluettiKit` live-update surface when a session is available, refresh the selected device on relevant device-update hints, and fall back to the existing polling path only when live delivery is unavailable or degraded.

Why: This gives the sample app visibly fresher updates without making live websocket delivery a hard requirement. It also preserves the current poll-driven safety net for unsupported endpoints, disconnects, and auth recovery gaps.

Alternative considered: keeping polling active at the same cadence even while live updates are connected. Rejected because it reduces the value of the native live-update slice and keeps unnecessary background traffic once the websocket path is healthy.

## Risks / Trade-offs

- [BLUETTI websocket semantics may differ subtly from the current Python expectations] -> Keep the first Swift transport surface minimal, cover handshake or message parsing with focused tests, and degrade cleanly on unexpected frames.
- [Long-lived websocket tasks can complicate token refresh and app lifecycle] -> Centralize session lifecycle inside `BluettiClient` and keep the sample view model focused on status consumption plus selected-device refresh.
- [Live updates may not cover every telemetry mutation] -> Preserve explicit refresh and fallback polling rather than assuming websocket hints are sufficient in every state.

## Migration Plan

1. Add internal websocket or STOMP session support and a sanitized live-update event model to `BluettiKit`.
2. Add Swift tests for connection lifecycle, status reporting, token-expiry or disconnect fallback, and device-update hint delivery.
3. Update the menu bar sample view model and UI to consume live-update status and targeted refresh events.
4. Refresh package and sample docs so native live-update setup and fallback expectations are explicit.

## Open Questions

- Whether the public Swift surface should expose a stream per subscriber or a single shared client-owned live-update session handle.
- Whether the first native slice should attempt automatic reconnect after auth refresh, or stop at degraded-state reporting plus explicit reconnect and fallback refresh.