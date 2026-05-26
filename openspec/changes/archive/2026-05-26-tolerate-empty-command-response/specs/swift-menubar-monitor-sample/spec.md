# swift-menubar-monitor-sample Specification

## MODIFIED Requirements

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