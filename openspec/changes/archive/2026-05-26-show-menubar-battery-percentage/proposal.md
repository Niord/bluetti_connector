## Why

The macOS menu bar sample already computes the selected device battery percentage, but the current status item label is built with `Label(...)` and can render as icon-only in the user's Xcode app. That makes the most useful at-a-glance value unavailable until the menu is opened, so the sample should explicitly surface the percentage in the menu bar item itself.

## What Changes

- Update the SwiftUI menu bar sample to render the status item with explicit text and battery icon content instead of a `Label` that can collapse to icon-only rendering.
- Apply the same status item rendering change to the single-file `CopyIntoXcode` variant so copied apps behave the same way as the packaged sample.
- Add a spec delta that requires the menu bar sample to mirror the selected device battery percentage in the visible menu bar item when device state is available.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `swift-menubar-monitor-sample`: require the visible menu bar status item to show the selected device battery percentage when live device data is available.

## Impact

- Updates the menu bar label composition in `swift/BluettiMonitorSample/Sources/BluettiMonitorSample/BluettiMonitorApp.swift`.
- Updates the copy-ready Xcode file in `swift/BluettiMonitorSample/CopyIntoXcode/BluettiMonitorApp.swift`.
- Adds a focused OpenSpec delta for `swift-menubar-monitor-sample` and requires a narrow Swift build plus OpenSpec validation.