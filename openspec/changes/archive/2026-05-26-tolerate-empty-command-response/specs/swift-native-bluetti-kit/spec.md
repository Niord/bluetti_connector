# swift-native-bluetti-kit Specification

## MODIFIED Requirements

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