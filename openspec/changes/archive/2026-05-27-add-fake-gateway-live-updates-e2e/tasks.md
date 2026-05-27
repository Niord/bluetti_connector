## 1. Local Live-Update Verification Gate

- [x] 1.1 Add an explicit repository-local gate for insecure fake-gateway live updates while keeping the default runtime `wss://`-only behavior unchanged
- [x] 1.2 Add focused backend coverage for secure-default behavior versus explicitly enabled local fake-gateway `ws://` endpoints

## 2. Fake-Gateway End-To-End Delivery

- [x] 2.1 Extend the fake gateway with the minimum websocket or STOMP notification surface needed by the existing backend live-update client
- [x] 2.2 Add integration coverage that proves fake-gateway live-update delivery reaches the backend status stream and sanitized device-update events
- [x] 2.3 Add integration coverage for degraded fallback when the fake gateway disconnects or rejects the local live-update session

## 3. Browser Verification And Context

- [x] 3.1 Extend the browser-facing live-update harness so fake-gateway-driven events verify affected-device refresh behavior through backend-owned endpoints
- [x] 3.2 Update contributor documentation and agent context to describe the offline live-update verification flow and how it complements gated live-account checks