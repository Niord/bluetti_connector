## Why

The repository now proves the BLUETTI cloud contract through a standalone Python implementation, but the target operator experience for macOS is a native Swift application that does not embed or invoke Python at runtime. A self-contained Swift package is needed so the verified auth, device, telemetry, and control flows can move into Xcode as first-class native code.

## What Changes

- Add a new self-contained Swift Package that talks directly to the BLUETTI cloud instead of calling the local Python backend.
- Implement BLUETTI browser OAuth helpers, authorization-code exchange, refresh-token recovery, and local token-store boundaries in Swift.
- Implement Swift-native device discovery, per-device refresh, typed battery and power helpers, and safe AC/DC or select-style control execution based on the verified BLUETTI payload contract.
- Add repository-local documentation showing how to attach the Swift package to an Xcode macOS app and where the current Swift scope intentionally stops.
- Add focused Swift tests so the native client contract is verified independently from the Python runtime.

## Capabilities

### New Capabilities
- `swift-native-bluetti-kit`: a self-contained Swift package for BLUETTI browser OAuth, token refresh, device discovery, normalized telemetry helpers, and supported device commands for native Apple-platform apps.

### Modified Capabilities
None.

## Impact

- Adds a new Swift Package under `swift/` with package manifest, source files, tests, and package-level documentation.
- Reuses the verified BLUETTI cloud contract from the Python extraction only as implementation reference; the Swift runtime remains independent.
- Adds OpenSpec documentation for the native Swift capability without changing the current Python backend behavior or existing standalone specs.
- Requires focused `swift test` validation in addition to OpenSpec validation.