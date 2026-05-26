# BluettiKit

`BluettiKit` is a self-contained Swift Package for native macOS BLUETTI clients. It talks directly to the verified BLUETTI cloud endpoints and does not call the Python runtime.

## Included Surface

- browser OAuth authorize URL generation
- authorization-code exchange and refresh-token recovery
- pluggable token persistence with a Keychain-backed default
- device list loading and per-device refresh
- normalized battery, power, AC, and DC helpers
- supported switch-style and select-style command execution

The first slice intentionally does not include websocket live updates.

## Add To Xcode

1. In Xcode, choose `File -> Add Package Dependencies...`
2. Click `Add Local...`
3. Select `swift/BluettiKit` from this repository
4. Link the `BluettiKit` library product to your macOS target

## Minimal Usage

```swift
import AppKit
import BluettiKit

let tokenStore = BluettiKeychainTokenStore(service: "com.example.BluettiApp")
let client = BluettiClient(tokenStore: tokenStore)

let authSession = BluettiBrowserOAuthSession(
    presentationAnchor: NSApp.keyWindow ?? NSWindow()
)

let redirectURI = URL(string: "bluetti-macos://oauth/callback")!
let _ = try await authSession.authenticate(
    with: client,
    redirectURI: redirectURI
)

let devices = try await client.listDevices()
let refreshed = try await client.refreshDevice(serialNumber: devices[0].serialNumber)
let updated = try await client.setACOutput(serialNumber: refreshed.serialNumber, isOn: true)

print(updated.batteryLevel ?? -1)
print(updated.powerMetrics.acLoadWatts ?? 0)
print(updated.acOutputEnabled ?? false)
```

## Notes For Your macOS App

- Register a custom URL scheme in the app that matches the `redirectURI` you pass to BLUETTI.
- `ASWebAuthenticationSession` must receive a presentation anchor from your app window.
- Raw BLUETTI state payloads stay available through `device.stateList`; the convenience helpers only normalize the first verified surface.