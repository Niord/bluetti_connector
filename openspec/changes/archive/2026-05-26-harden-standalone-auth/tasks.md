## 1. Auth Session Model

- [x] 1.1 Define backend session input and snapshot models for token-based and persisted auth sources
- [x] 1.2 Add a local token-store boundary and bootstrap precedence rules for request, stored, and settings-backed session state

## 2. Core Auth Integration

- [x] 2.1 Adapt the upstream refresh behavior into the standalone auth path without `homeassistant` dependencies
- [x] 2.2 Wire token-expiry refresh, persistence updates, and one retry path into backend-managed product client operations

## 3. Backend And UI Session Flow

- [x] 3.1 Extend the session endpoint and sanitized auth error mapping for refresh-capable setup and refresh recovery
- [x] 3.2 Update the local UI session form and runtime metadata to show auth mode, stored-session usage, refresh capability, and re-authentication feedback

## 4. Verification And Documentation

- [x] 4.1 Add focused smoke coverage for persisted token reuse and token refresh recovery
- [x] 4.2 Update runtime documentation and repo context for the new auth model, token-store behavior, and live-account verification path