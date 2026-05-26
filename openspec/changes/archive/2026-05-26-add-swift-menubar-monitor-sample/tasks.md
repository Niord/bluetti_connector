## 1. Sample Package Setup

- [x] 1.1 Create the `swift/BluettiMonitorSample` package structure and local dependency on `../BluettiKit`
- [x] 1.2 Add package-level documentation that explains how to adapt the sample into an Xcode macOS app
- [x] 1.3 Add a single-file `BluettiMonitorApp.swift` variant for direct replacement in an existing Xcode menu bar app

## 2. Menu Bar App Implementation

- [x] 2.1 Implement the SwiftUI `MenuBarExtra` app, copyable view model, session bootstrap, and browser OAuth entry point
- [x] 2.2 Implement device polling, device selection, low-battery notifications, and AC/DC output controls for the selected device

## 3. Validation

- [x] 3.1 Run a focused Swift build or equivalent compile validation for the sample app package
- [x] 3.2 Run `DO_NOT_TRACK=1 rtk openspec validate --all --no-interactive 2>/dev/null` after the sample change artifacts and code are updated