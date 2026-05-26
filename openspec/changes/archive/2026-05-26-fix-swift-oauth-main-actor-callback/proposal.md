## Why

The native Swift browser OAuth flow now reaches the BLUETTI login screen, but a macOS app can still hit a dispatch queue assertion when the browser callback returns to the app. That breaks the first real sign-in path for both `BluettiKit` consumers and the menu bar sample even though the package compiles successfully.

## What Changes

- Fix the native Swift browser OAuth callback path so `ASWebAuthenticationSession` lifecycle and callback completion stay on the expected main-actor path for macOS apps.
- Keep the menu bar sample aligned with the safer browser OAuth behavior so the copy-ready Xcode file follows the same fixed path.
- Add or update focused validation for the native Swift package and sample package after the callback-threading fix.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `swift-native-bluetti-kit`: tighten the browser OAuth requirement so callback completion works safely in native macOS apps.
- `swift-menubar-monitor-sample`: tighten the menu bar sample requirement so browser login can return into the app without a callback-threading crash.

## Impact

- Affects `swift/BluettiKit/Sources/BluettiKit/BluettiBrowserOAuthSession.swift`.
- May affect the copy-ready or sample app-facing integration code under `swift/BluettiMonitorSample/` if any explicit main-actor bridging is needed.
- Requires focused `swift build` validation for the sample package and OpenSpec validation after the fix.