# swift-menubar-monitor-sample Specification

## Purpose
Define the copyable SwiftUI macOS menu bar sample that uses `BluettiKit` for BLUETTI authentication, native live updates with polling fallback, low-battery notification, and safe AC/DC output control.

## Requirements
### Requirement: Menu Bar Sample Restores Or Starts A BLUETTI Session
The menu bar sample SHALL load persisted BLUETTI token state on startup, SHALL allow the user to start browser-based BLUETTI login when needed, and SHALL continue into device polling without Python runtime dependencies.

#### Scenario: Stored native session is available
- **WHEN** the sample app launches and the configured token store still has BLUETTI session tokens
- **THEN** the sample restores the session and attempts to load device data without forcing the user to log in again

#### Scenario: User starts browser login from the menu bar app
- **WHEN** the sample app has no usable BLUETTI session and the user chooses the connect action
- **THEN** the sample starts browser OAuth through `BluettiKit`, stores the resulting token state, and proceeds to load devices when login succeeds

### Requirement: Menu Bar Sample Survives Browser OAuth Return
The menu bar sample SHALL be able to return from the BLUETTI browser login callback into the app without crashing on callback-threading or queue-assertion failure.

#### Scenario: Browser OAuth completes from the sample app
- **WHEN** the sample app starts BLUETTI browser login and the operator completes authentication in the browser
- **THEN** the app returns from the callback into the menu bar flow without a dispatch queue assertion and proceeds to device loading or sanitized error display

### Requirement: Menu Bar Sample Polls And Displays Device Status
The menu bar sample SHALL subscribe to `BluettiKit` live updates for the active BLUETTI session when that live path is available, SHALL refresh the selected device on relevant live-update hints, SHALL fall back to explicit refresh or polling when live updates are degraded or unavailable, SHALL let the user choose the visible device when multiple devices exist, SHALL show the current battery and power summary in menu bar content, and SHALL mirror the selected device battery percentage in the visible menu bar status item whenever device state is available.

#### Scenario: Selected device status is refreshed from a live-update hint
- **WHEN** the sample app has an authenticated BLUETTI session, live updates are connected, and the selected device receives a live-update hint
- **THEN** the sample refreshes that selected device through `BluettiKit` and updates the displayed battery percentage and power readings without waiting for the fallback poll interval

#### Scenario: Live updates are unavailable for the selected device
- **WHEN** the sample app cannot keep the BLUETTI live-update session connected for the current selection
- **THEN** it shows that live updates are unavailable or degraded and continues to keep device status fresh through explicit refresh or fallback polling

#### Scenario: Selected device battery is shown in the menu bar item
- **WHEN** the sample app has an authenticated BLUETTI session and a selected device with battery state
- **THEN** the visible menu bar status item shows that battery percentage without requiring the user to open the menu

#### Scenario: Multiple devices are available
- **WHEN** the BLUETTI account exposes more than one device
- **THEN** the sample app allows the user to change the active device shown in the menu bar content

### Requirement: Menu Bar Sample Controls AC And DC Outputs Safely
The menu bar sample SHALL surface the current AC and DC output states for the selected device, SHALL let the user toggle those outputs through `BluettiKit` when the device exposes command-capable switch metadata, and SHALL avoid showing a false command failure when BLUETTI accepts the command with an empty success payload.

#### Scenario: User toggles AC output
- **WHEN** the selected device exposes a supported AC output switch state and the user changes that control in the menu bar app
- **THEN** the sample sends the corresponding BLUETTI command and updates the visible device state when the command succeeds

#### Scenario: User toggles DC output
- **WHEN** the selected device exposes a supported DC output switch state and the user changes that control in the menu bar app
- **THEN** the sample sends the corresponding BLUETTI command and updates the visible device state when the command succeeds

#### Scenario: Command success omits fulfillment payload data
- **WHEN** BLUETTI accepts an AC or DC output command with a success envelope that omits `data`
- **THEN** the sample keeps the command on the success path and does not show a false error message solely because the fulfillment payload was empty

### Requirement: Menu Bar Sample Warns On Low Battery Without Spamming
The menu bar sample SHALL request local notification permission and SHALL emit a low-battery notification only when the monitored device crosses below the configured threshold.

#### Scenario: Battery drops below threshold
- **WHEN** the selected device battery level falls below the configured low-battery threshold after previously being above it
- **THEN** the sample app sends one low-battery notification for that low-battery period

#### Scenario: Battery stays below threshold across multiple polls
- **WHEN** the selected device remains below the configured low-battery threshold on later refresh cycles
- **THEN** the sample app does not repeat the same low-battery notification until the battery level first recovers above the threshold

### Requirement: Menu Bar Sample Surfaces Session And Request Failures
The menu bar sample SHALL show visible state when BLUETTI authentication, device refresh, or command execution fails and SHALL keep the user able to retry, reconnect, or quit the app.

#### Scenario: Refresh or command request fails
- **WHEN** a BLUETTI load or command request throws an error
- **THEN** the sample app shows the failure message in menu content without crashing the app

#### Scenario: Session must be reconnected
- **WHEN** the BLUETTI session is missing or expires without successful refresh recovery
- **THEN** the sample app returns to a reconnectable state that still offers a browser-login action from the menu bar UI