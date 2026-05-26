## Context

The standalone connector already persists BLUETTI cloud session state, refreshes tokens when needed, and exposes device discovery and command flows through a local FastAPI backend. Device state freshness still depends on explicit `/api/devices` or `/refresh` calls and on command responses. At the same time, the extracted codebase already contains a BLUETTI STOMP or WebSocket client adapted from upstream, but the local backend does not currently manage or expose that channel.

The next slice should use that existing transport to improve freshness without violating a core constraint of this repo: the browser must keep talking only to the local backend, not directly to BLUETTI cloud. That makes the backend the correct place to own cloud websocket connection lifecycle, token-aware reconnects, and any local fan-out surface to the page.

## Goals / Non-Goals

**Goals:**
- start and stop a backend-managed BLUETTI websocket session together with the current authenticated backend session
- expose backend-visible live-update status so the local app can tell whether it is receiving push updates or has fallen back to polling
- let the browser receive backend-owned live update events without connecting to BLUETTI cloud directly
- reuse the existing merged refresh path when websocket notifications indicate that a device should be refreshed

**Non-Goals:**
- exposing raw BLUETTI websocket messages to browser code
- replacing all manual refresh behavior immediately
- solving multi-user browser fan-out or remote deployment concerns in this first pass
- introducing a second browser-to-backend realtime protocol if a simpler local stream works

## Decisions

### 1. The backend will own the BLUETTI websocket session and the browser will consume a local stream
The backend should manage the cloud websocket because it already owns access tokens, refresh recovery, and device refresh orchestration. The browser should consume a local backend stream instead of connecting to BLUETTI cloud directly.

Alternative considered: connecting the browser directly to BLUETTI websocket infrastructure. Rejected because it would leak cloud session details to browser code and undermine the existing backend-owned security boundary.

### 2. The first local fan-out surface will use server-sent events rather than a second browser websocket
The local page only needs one-way delivery of update notifications and connection state from the backend. Server-sent events are simpler to integrate with the existing FastAPI app and browser code than standing up a second websocket protocol just for local fan-out.

Alternative considered: exposing a local websocket endpoint to the browser. Rejected for the first slice because it would add another bidirectional protocol without a clear need.

### 3. Websocket notifications will trigger targeted refresh through the existing device merge path
The backend should treat BLUETTI websocket messages as a hint that a device changed, then call the existing refresh path for the affected device. That keeps product and status merging, bind recovery, and state normalization centralized.

Alternative considered: mutating local device state directly from raw websocket payloads. Rejected because it would duplicate mapping logic and risk diverging from the current validated refresh behavior.

### 4. Live updates must degrade cleanly to polling status when websocket delivery is unavailable
The local UI should treat live updates as an enhancement, not a hard dependency. If websocket connection fails, expires, or is unavailable for the current session, the backend and UI should remain usable with explicit refresh and command flows.

Alternative considered: requiring websocket connectivity for normal device operation. Rejected because local control is already functional with polling and manual refresh.

## Risks / Trade-offs

- [BLUETTI websocket behavior may differ from the upstream assumptions in the extracted client] -> keep the first slice focused on backend ownership, connection status, and refresh triggers, with clear fallback to polling.
- [Threaded websocket-client callbacks must interact safely with the async backend] -> isolate websocket lifecycle in a dedicated backend manager and bridge into the async loop with explicit callbacks.
- [SSE subscribers can outlive the active session] -> bind local stream lifecycle to the backend session and send clear degraded or disconnected status events.
- [Live updates may arrive before the backend has a cached device set] -> trigger refresh only for device identifiers that can be resolved, and keep manual refresh available.

## Migration Plan

1. Add backend live-update state and lifecycle management around the existing BLUETTI websocket client.
2. Expose local live-update status and a backend-owned SSE stream for the browser.
3. Update the local page to subscribe to that stream, surface connection state, and refresh targeted devices automatically.
4. Expand fake-gateway and regression coverage for websocket lifecycle, fallback behavior, and UI-visible updates.

Rollback strategy: disable backend websocket startup and fall back to the existing polling-only flow while keeping the local stream endpoints dormant or removed.

## Open Questions

- Whether the extracted websocket client needs protocol or reconnect adjustments before it can be considered trustworthy against the real BLUETTI cloud.
- Whether a single device-level refresh per websocket notification is sufficient, or whether the backend should coalesce bursts before refreshing.