## 1. BluettiKit Live Update Transport

- [x] 1.1 Add the internal websocket or STOMP session, sanitized live-update event model, and client-facing status surface to `swift/BluettiKit`
- [x] 1.2 Add focused `BluettiKit` tests for live-update handshake, device-update hint delivery, and degraded disconnect or auth-failure behavior

## 2. Menu Bar Sample Integration

- [x] 2.1 Update `BluettiMonitorViewModel` and related sample UI state to subscribe to native live updates for the active session and selected device
- [x] 2.2 Keep explicit refresh and fallback polling behavior when live updates are unavailable or degraded, and surface that native live-update status in the sample app

## 3. Documentation And Validation

- [x] 3.1 Update Swift package or sample documentation and roadmap context for native live updates, fallback behavior, and integration expectations
- [x] 3.2 Run focused Swift validation for `BluettiKit` and `BluettiMonitorSample`, then rerun `DO_NOT_TRACK=1 rtk openspec validate --all --no-interactive 2>/dev/null`