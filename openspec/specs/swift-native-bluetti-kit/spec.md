# swift-native-bluetti-kit Specification

## Purpose
Define the self-contained Swift package contract for BLUETTI browser OAuth, token refresh, device discovery, normalized device telemetry, and supported device command execution for native Apple-platform apps.

## Requirements
### Requirement: Swift Package Establishes A Native BLUETTI Session
The Swift package SHALL let a native app start BLUETTI browser OAuth, exchange an authorization code for tokens, and refresh the session from a stored refresh token without invoking the Python runtime.

#### Scenario: Browser OAuth authorize URL is built for a native app callback
- **WHEN** the app starts a BLUETTI sign-in flow with a configured redirect URI and generated state token
- **THEN** the package returns the BLUETTI authorize URL targeting `/oauth2/grant` with the expected authorization-code query parameters

#### Scenario: Authorization code is exchanged into a persisted session
- **WHEN** BLUETTI redirects back with a valid authorization code for the configured native callback URI
- **THEN** the package exchanges the code through `/oauth2/token`, returns access and refresh tokens, and makes the token state available to the configured token store

#### Scenario: Expired access token is recovered from refresh context
- **WHEN** a BLUETTI cloud request reports token expiry and the package still holds a valid refresh token
- **THEN** the package refreshes the session through `/oauth2/token`, persists the refreshed token state, and retries the original device operation

### Requirement: Swift Package Completes Browser OAuth Callback Safely On macOS
The Swift package SHALL keep the native BLUETTI browser OAuth session lifecycle on a callback path that is safe for a macOS app to resume without queue-assertion or callback-threading failure.

#### Scenario: Browser login returns to the native app
- **WHEN** a macOS app using the Swift package completes BLUETTI browser login and the callback URL returns to the app
- **THEN** the package finishes the auth-session callback flow without a dispatch queue assertion and continues to token exchange or sanitized error handling

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

### Requirement: Swift Package Retrieves BLUETTI Devices And Current State
The Swift package SHALL retrieve the authenticated account devices from BLUETTI cloud and SHALL return decoded device models that preserve the cloud state payload.

#### Scenario: Device list is loaded from BLUETTI cloud
- **WHEN** the app requests the current devices for an authenticated account
- **THEN** the package calls the BLUETTI devices endpoint, decodes the response envelope, and returns device models with identifiers, names, online status, and raw state entries

#### Scenario: One device is refreshed for the latest state
- **WHEN** the app requests a fresh state for a specific device serial number
- **THEN** the package calls the BLUETTI device-state endpoint and returns the latest decoded state for that device

### Requirement: Swift Package Exposes Normalized Battery Power And AC/DC Helpers
The Swift package SHALL expose convenience helpers for the first native app telemetry surface while preserving raw BLUETTI state payloads.

#### Scenario: Battery percentage is derived from SOC state
- **WHEN** a device payload contains the verified `SOC` state used by the current standalone implementation
- **THEN** the package exposes that value as a typed battery percentage helper in addition to the raw state entry

#### Scenario: Prioritized power and switch helpers are available
- **WHEN** a device payload contains verified power or switch codes such as `PVAllTotalPower`, `GridAllTotalPower`, `ACLoadAllTotalPower`, `DCLoadAllTotalPower`, `SetCtrlAc`, or `SetCtrlDc`
- **THEN** the package exposes convenience helpers for those values and switch statuses without hiding the raw underlying state objects

### Requirement: Swift Package Executes Supported Device Commands
The Swift package SHALL send supported commands for BLUETTI switch-style and select-style states, SHALL reject values that are not allowed by the current decoded control metadata, and SHALL treat a BLUETTI fulfillment response with `msgCode == 0` as a successful command acceptance even when the envelope omits payload data.

#### Scenario: AC or DC switch state is toggled
- **WHEN** the app requests an allowed value for a switch-style BLUETTI state such as `SetCtrlAc` or `SetCtrlDc`
- **THEN** the package validates the command value, sends the control request to the BLUETTI fulfillment endpoint, and returns the updated device state

#### Scenario: Command success omits fulfillment payload data
- **WHEN** the BLUETTI fulfillment endpoint accepts a supported command with `msgCode == 0` but omits the envelope `data` payload
- **THEN** the package still treats the command as accepted and returns the updated device state instead of surfacing a false invalid-response error

#### Scenario: Unsupported state value is rejected before the cloud call
- **WHEN** the app submits a value that is not present in the current allowed values for a command-capable state
- **THEN** the package rejects the command locally instead of reporting success

### Requirement: Swift Package Attaches Cleanly To Xcode
The Swift package SHALL be structured so a native macOS app can add it as a local package dependency from this repository.

#### Scenario: Package is added to an Xcode app
- **WHEN** a developer adds the local package directory from this repository to an Xcode macOS project
- **THEN** Xcode resolves the package manifest, exposes the `BluettiKit` product, and the app can import the package without Python runtime dependencies