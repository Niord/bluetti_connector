# BluettiMonitorSample

`BluettiMonitorSample` is a copyable SwiftUI macOS menu bar sample that uses the local `BluettiKit` package.

It shows how to:

- restore a persisted BLUETTI session from the keychain
- start browser OAuth from a menu bar app
- subscribe to native BLUETTI live updates for the selected device and fall back to polling when needed
- display battery, charging, and power summary in `MenuBarExtra`
- toggle AC and DC outputs
- send low-battery notifications without repeating them every poll cycle

## What To Copy Into Xcode

If you already started a macOS app in Xcode, the most useful files to copy first are:

1. `Sources/BluettiMonitorSample/BluettiMonitorViewModel.swift`
2. `Sources/BluettiMonitorSample/BluettiMonitorMenuContent.swift`
3. `Sources/BluettiMonitorSample/BluettiMonitorApp.swift`

That replaces the random-value `BluettiManager` pattern with a real `BluettiKit`-backed view model.

If you prefer a single-file replacement for your existing `BluettiMonitorApp.swift`, use:

- `CopyIntoXcode/BluettiMonitorApp.swift`

That file keeps the same top-level app entry pattern, but swaps the random mock manager for a real `BluettiKit`-backed `BluettiManager`.

## Xcode Setup

1. Add the local package at `swift/BluettiKit`
2. Link the `BluettiKit` product to your macOS target
3. Register a custom URL scheme that matches `bluetti-monitor://oauth/callback`
4. If you change the URL scheme, update `BluettiMonitorSampleConfig.redirectURI` in the sample code

## Notes

- The sample uses the production BLUETTI cloud endpoints from `BluettiKit`
- Browser OAuth starts from the menu content and uses the first available macOS window as its presentation anchor
- The sample starts native live updates for an authenticated session, refreshes the selected device on matching live-update hints, and pauses fallback polling while live updates stay connected
- When live updates are degraded or unavailable, the sample surfaces that status in the menu and keeps device state current through manual refresh plus fallback polling