# Swift Package

`swift/BluettiKit` is a self-contained Swift Package for native macOS BLUETTI clients. It talks directly to verified BLUETTI cloud endpoints and does not require the Python backend.

## Included Surface

- Browser OAuth authorize URL generation and authorization-code exchange
- Refresh-token recovery
- Pluggable token persistence with a Keychain-backed default
- Device discovery and per-device refresh
- Authenticated live-update session startup, status snapshots, and sanitized device-update hints
- Normalized battery, power, AC output, and DC output helpers
- Supported switch-style and select-style command execution

## Requirements

- macOS 13 or newer
- Swift Package Manager with Swift tools version 6.0
- A macOS app target when using `ASWebAuthenticationSession` browser login

## Build And Test

From the repository root:

```bash
cd swift/BluettiKit
swift build
swift test
```

Tests use mocked URL and websocket surfaces. They do not require a live BLUETTI account.

## Add To Xcode

1. In Xcode, choose `File -> Add Package Dependencies...`.
2. Click `Add Local...`.
3. Select `swift/BluettiKit` from this repository.
4. Link the `BluettiKit` library product to your macOS target.

## OAuth Notes

Native apps should register a custom URL scheme and pass a matching redirect URI to `BluettiBrowserOAuthSession`.

```swift
let tokenStore = BluettiKeychainTokenStore(service: "com.example.BluettiApp")
let client = BluettiClient(tokenStore: tokenStore)
let redirectURI = URL(string: "bluetti-macos://oauth/callback")!

let authSession = BluettiBrowserOAuthSession(
    presentationAnchor: NSApp.keyWindow ?? NSWindow()
)

let tokenState = try await authSession.authenticate(
    with: client,
    redirectURI: redirectURI
)
```

`ASWebAuthenticationSession` requires a presentation anchor from the app. The package stores tokens only through the configured token store.

## Devices, Live Updates, And Commands

After authentication, use `BluettiClient` for device operations:

```swift
let devices = try await client.listDevices()
let refreshed = try await client.refreshDevice(serialNumber: devices[0].serialNumber)
let updated = try await client.setACOutput(serialNumber: refreshed.serialNumber, isOn: true)
```

Live updates emit sanitized events so app code does not need to parse websocket or STOMP frames:

```swift
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

If live updates become degraded or unavailable, apps can continue to use explicit refresh or a polling fallback.

Raw BLUETTI state payloads remain available through `device.stateList`. Convenience helpers cover the first verified battery, power, AC/DC output, and safe command surfaces.
