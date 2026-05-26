## Why

Real BLUETTI command requests can succeed on the device while the fulfillment endpoint returns a success envelope without a `data` payload. The current Swift client treats that response as invalid, which makes the macOS menu bar sample show a false command failure even though the output state actually changed.

## What Changes

- Update the Swift command path so BLUETTI fulfillment responses with `msgCode == 0` are accepted even when the envelope does not include a `data` payload.
- Keep optimistic device-state merging for supported AC/DC commands so the native sample reflects the accepted switch state immediately instead of waiting for a manual refresh.
- Add regression coverage for a successful command response whose envelope omits payload data.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `swift-native-bluetti-kit`: command execution must tolerate successful fulfillment responses that omit payload data.
- `swift-menubar-monitor-sample`: command toggles must not surface a false failure when BLUETTI accepts the command but returns an empty success payload.

## Impact

- Updates command-response handling in `swift/BluettiKit/Sources/BluettiKit/BluettiClient.swift`.
- Adds regression coverage in `swift/BluettiKit/Tests/BluettiKitTests/BluettiClientTests.swift`.
- Adds an OpenSpec delta for the Swift package and menu bar sample requirements, followed by focused Swift test validation and OpenSpec validation.