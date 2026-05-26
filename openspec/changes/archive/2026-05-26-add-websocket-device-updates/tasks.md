## 1. Backend Live Update Lifecycle

- [x] 1.1 Add backend-managed websocket lifecycle and status tracking tied to the active authenticated session
- [x] 1.2 Bridge websocket notifications into backend refresh triggers or sanitized device update events
- [x] 1.3 Degrade cleanly to polling when websocket startup, reconnect, or token state fails

## 2. Local Stream And UI Integration

- [x] 2.1 Add a backend-owned local live update stream surface for browser subscribers
- [x] 2.2 Update the local page to subscribe to backend live update events and refresh affected device cards automatically
- [x] 2.3 Surface live-update connection or degraded status in the runtime and device UI without exposing raw cloud websocket details

## 3. Verification And Documentation

- [x] 3.1 Add focused regression coverage for websocket lifecycle, status reporting, and graceful fallback behavior
- [x] 3.2 Extend fake-gateway or backend integration coverage for live update notifications and UI-visible device refresh behavior
- [x] 3.3 Update runtime documentation, roadmap, and known-issues context for backend-owned live updates and fallback expectations