## ADDED Requirements

### Requirement: Swift Package Maintains A Native BLUETTI Live-Update Session
The Swift package SHALL let a native app start and stop an authenticated BLUETTI live-update session, SHALL report whether live updates are connected, degraded, or unavailable, and SHALL emit sanitized device-update hints without exposing raw websocket protocol details to app code.

#### Scenario: Live-update session starts for an authenticated app
- **WHEN** the native app has a valid BLUETTI session and requests live updates from `BluettiKit`
- **THEN** the package establishes the BLUETTI websocket session, subscribes to device notifications, and reports that live updates are connected

#### Scenario: Live-update session becomes unavailable
- **WHEN** the BLUETTI websocket session disconnects, cannot be started, or cannot continue for the current native session
- **THEN** the package reports that live updates are degraded or unavailable and keeps the app able to use explicit refresh or fallback behavior

#### Scenario: Device update is observed from BLUETTI cloud
- **WHEN** the BLUETTI live-update session indicates that a device changed
- **THEN** the package emits a sanitized device-update hint that lets the native app refresh the affected device through its normal client APIs