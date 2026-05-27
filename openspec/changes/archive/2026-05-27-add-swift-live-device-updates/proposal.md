## Why

The native Swift slices are still explicitly poll-only even though the Python runtime now has verified BLUETTI live-update behavior and deterministic fake-gateway coverage. The next useful Apple-platform step is to bring that live-update capability into `BluettiKit` and the menu bar sample so the first native app is not limited to interval refresh for every visible state change.

## What Changes

- Add native BLUETTI live-update session support to `BluettiKit`, including authenticated websocket lifecycle, sanitized device-update delivery, and graceful degradation when live delivery is unavailable.
- Extend the menu bar sample to subscribe to `BluettiKit` live updates, refresh the selected device on targeted update hints, and show whether the native app is currently live or has fallen back to explicit refresh or polling.
- Preserve the existing polling path as a fallback for unsupported websocket configurations, disconnects, or auth recovery gaps instead of making live updates a hard dependency.
- Add focused Swift tests and sample documentation for live-update connection, disconnect fallback, and native app integration expectations.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `swift-native-bluetti-kit`: extend the native client contract with authenticated live-update session management and device-update delivery.
- `swift-menubar-monitor-sample`: extend the sample app contract so it can consume native live updates and visibly fall back when the live session is degraded.

## Impact

- `swift/BluettiKit/Sources/BluettiKit/` transport, client, and model surfaces
- `swift/BluettiKit/Tests/BluettiKitTests/` coverage for live-update session lifecycle and fallback behavior
- `swift/BluettiMonitorSample/Sources/BluettiMonitorSample/` view-model and menu-bar UI state
- Swift package and sample documentation for native live-update setup, limitations, and validation