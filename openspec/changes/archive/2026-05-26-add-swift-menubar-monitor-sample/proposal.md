## Why

The repository now has a self-contained `BluettiKit` Swift package, but a native macOS operator still needs a concrete example of how to wire that client kit into a real menu bar app. The current user prototype still uses random mock values, so the next useful slice is a copyable SwiftUI menu bar sample that performs real BLUETTI login, polling, device selection, and safe AC/DC control.

## What Changes

- Add a native SwiftUI macOS menu bar sample app package that depends on `BluettiKit` and demonstrates a real BLUETTI monitoring flow.
- Replace the mock battery manager pattern with a `@MainActor` view model that loads persisted tokens, starts browser OAuth, polls device data, sends low-battery notifications, and exposes state to `MenuBarExtra`.
- Add sample UI for device selection, refresh, battery and power display, and AC/DC output toggles so the user can lift the code into an Xcode app.
- Document the Xcode integration steps and required app configuration details such as redirect URI scheme and notification permission behavior.

## Capabilities

### New Capabilities
- `swift-menubar-monitor-sample`: a copyable SwiftUI macOS menu bar sample that uses `BluettiKit` for BLUETTI login, polling, device status display, low-battery notification, and AC/DC control.

### Modified Capabilities
None.

## Impact

- Adds a new Swift sample package under `swift/BluettiMonitorSample/`.
- Adds menu bar app source files, app-facing view-model logic, and sample documentation for Xcode integration.
- Leaves the underlying `BluettiKit` transport and the existing Python runtime unchanged.
- Requires focused Swift build validation for the new sample package in addition to OpenSpec validation.