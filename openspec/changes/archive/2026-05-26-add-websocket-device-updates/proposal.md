## Why

The local BLUETTI page still depends on manual refreshes and command round-trips to see changed device state, even though the extracted codebase already includes a BLUETTI STOMP or WebSocket client. The next slice should let the backend own live update delivery so operators can see fresher device state without pushing BLUETTI cloud details into browser code.

## What Changes

- Add a backend-managed live update channel that uses the existing extracted BLUETTI websocket client to react to cloud device notifications.
- Expose local live-update status and a backend-owned update stream surface that the browser can consume without connecting directly to BLUETTI cloud.
- Update the local UI to subscribe to backend-driven live device events, refresh affected device state automatically, and surface whether live updates are connected or degraded back to polling.
- Add focused verification and fake-gateway coverage for websocket lifecycle, graceful fallback, and browser-visible live update behavior.

## Capabilities

### New Capabilities
- `standalone-live-device-updates`: backend-managed BLUETTI websocket subscription, local live update fan-out, and graceful degradation to polling when websocket delivery is unavailable.

### Modified Capabilities
- `local-bluetti-control-ui`: extend the local page so it can surface live-update connection state and apply backend-driven device updates without requiring manual refresh for every state change.

## Impact

- Affects backend session lifecycle and runtime state in `src/bluetti_connector/backend/`, especially around session configuration, health or session snapshots, and new local streaming endpoints.
- Reuses and may adapt the extracted websocket transport in `src/bluetti_connector/core/api/websocket.py`.
- Changes local UI behavior in `src/bluetti_connector/web/` so the page can subscribe to backend-driven updates and reconcile them with existing manual refresh or command flows.
- Requires new focused backend and core verification plus a broader fake-gateway harness that can exercise websocket-driven refresh behavior.