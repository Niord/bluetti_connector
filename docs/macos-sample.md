# macOS Menu Bar Sample

`swift/BluettiMonitorSample` is a SwiftUI menu bar reference app built on top of the local `BluettiKit` package. It demonstrates a native app integration pattern; it is not a signed installer or production distribution target.

## What It Demonstrates

- Restoring a persisted BLUETTI session from Keychain
- Starting browser OAuth from a menu bar app
- Loading and selecting BLUETTI devices
- Subscribing to native live updates for the selected device
- Falling back to polling when live updates are degraded or unavailable
- Displaying battery, charging, and power summary in `MenuBarExtra`
- Toggling supported AC and DC outputs
- Sending low-battery notifications without repeating them every poll cycle

## Build With SwiftPM

From the repository root:

```bash
cd swift/BluettiMonitorSample
swift build
```

The sample depends on `../BluettiKit` through a local SwiftPM package dependency.

## Xcode Setup

1. Open or create a macOS app target in Xcode.
2. Add the local package at `swift/BluettiKit`.
3. Link the `BluettiKit` product to the app target.
4. Register a custom URL scheme matching `bluetti-monitor://oauth/callback`.
5. If you change the URL scheme, update `BluettiMonitorSampleConfig.redirectURI` in the sample code.

## Copying Into An Existing App

The main reference files are:

- `Sources/BluettiMonitorSample/BluettiMonitorViewModel.swift`
- `Sources/BluettiMonitorSample/BluettiMonitorMenuContent.swift`
- `Sources/BluettiMonitorSample/BluettiMonitorApp.swift`

For a single-file reference, use `CopyIntoXcode/BluettiMonitorApp.swift`. That file keeps the same top-level app-entry shape while using a real `BluettiKit` client instead of placeholder battery values.

## Runtime Notes

- The sample uses the production BLUETTI cloud endpoints from `BluettiKit`.
- Browser OAuth starts from the menu content and uses the first available macOS window as its presentation anchor.
- The selected device refreshes when matching native live-update hints arrive.
- While live updates are connected, fallback polling pauses; when live updates degrade, the sample keeps state current through manual refresh and polling.
- Low-battery notifications require local notification permission from macOS.

## Limitations

- No installer, code signing, notarization, or update feed is provided in this repository slice.
- Device command support remains limited to switch-style and select-style states with verified allowed values.
- Numeric or free-form command entry is intentionally not exposed by the sample.
