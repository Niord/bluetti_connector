## 1. Swift Package Foundation

- [x] 1.1 Create the `swift/BluettiKit` package manifest, source layout, and package documentation for local Xcode integration
- [x] 1.2 Implement native BLUETTI auth primitives for authorize URL building, authorization-code exchange, refresh-token recovery, and pluggable token persistence

## 2. Native Device Flow

- [x] 2.1 Implement BLUETTI cloud transport, response-envelope decoding, device list loading, and per-device refresh with auth recovery
- [x] 2.2 Implement decoded state models, normalized battery and power helpers, and supported command execution for switch-style and select-style controls

## 3. Validation

- [x] 3.1 Add focused Swift tests for OAuth, token refresh retry, decoded telemetry helpers, and command validation
- [x] 3.2 Run `swift test` for the package and `DO_NOT_TRACK=1 rtk openspec validate --all --no-interactive 2>/dev/null`, then record any required documentation updates