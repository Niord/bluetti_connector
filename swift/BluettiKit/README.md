# BluettiKit

`BluettiKit` is a self-contained Swift Package for native macOS BLUETTI clients. It talks directly to the verified BLUETTI cloud endpoints and does not call the Python runtime.

## Included Surface

- browser OAuth authorize URL generation
- authorization-code exchange and refresh-token recovery
- pluggable token persistence with a Keychain-backed default
- device list loading and per-device refresh
- authenticated live-update session startup, status snapshots, and sanitized device-update hints
- normalized battery, power, AC, and DC helpers
- supported switch-style and select-style command execution

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

let liveUpdates = await client.liveUpdates()
await client.startLiveUpdates()

for await event in liveUpdates {
    switch event {
    case let .status(snapshot):
        print(snapshot.status.rawValue)
    case let .deviceUpdate(serialNumber):
        let refreshedDevice = try await client.refreshDevice(serialNumber: serialNumber)
        print(refreshedDevice.displayName)
    }
}
```

## Notes For Your macOS App

- Register a custom URL scheme in the app that matches the `redirectURI` you pass to BLUETTI.
- `ASWebAuthenticationSession` must receive a presentation anchor from your app window.
- `liveUpdates()` emits sanitized `.status` and `.deviceUpdate` events; app code does not need to parse websocket or STOMP frames.
- If live updates become degraded or unavailable, the app can keep using explicit refresh or any fallback polling strategy.
- Raw BLUETTI state payloads stay available through `device.stateList`; the convenience helpers only normalize the first verified surface.