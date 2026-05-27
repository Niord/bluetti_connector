# BluettiMonitorSample

`BluettiMonitorSample` is a SwiftUI macOS menu bar reference app built on top of the local `BluettiKit` package. It demonstrates native browser OAuth, device loading, selected-device live updates, polling fallback, low-battery notifications, and safe AC/DC output control.

See [../../docs/macos-sample.md](../../docs/macos-sample.md) for build, Xcode setup, copy-into-app guidance, runtime notes, and current limitations.

## Package Layout

- `Sources/BluettiMonitorSample/BluettiMonitorApp.swift` contains the sample app entry point.
- `Sources/BluettiMonitorSample/BluettiMonitorViewModel.swift` wires `BluettiKit` into menu state, auth, polling, live updates, and commands.
- `Sources/BluettiMonitorSample/BluettiMonitorMenuContent.swift` contains the compact menu bar UI.
- `CopyIntoXcode/BluettiMonitorApp.swift` provides a single-file reference for app prototypes that want the same integration shape.

## Quick Build

```bash
swift build
```

The package depends on `../BluettiKit` through a local SwiftPM dependency.

## Xcode Notes

1. Add the local package at `swift/BluettiKit`.
2. Link the `BluettiKit` product to your macOS target.
3. Register a custom URL scheme matching `bluetti-monitor://oauth/callback`.
4. If you change the URL scheme, update `BluettiMonitorSampleConfig.redirectURI` in the sample code.

The sample is intentionally a reference app. It does not include signing, notarization, installer packaging, or an update feed.
