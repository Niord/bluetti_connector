## ADDED Requirements

### Requirement: Local UI Shows Available BLUETTI Devices
The local BLUETTI control UI SHALL display the devices exposed by the local backend together with their current connectivity or power-state summary.

#### Scenario: Device overview renders from backend data
- **WHEN** a user opens the local BLUETTI control page and the backend returns discovered devices
- **THEN** the page shows each available device with identifying information and current state summary

### Requirement: Local UI Executes Basic Device Controls Through The Backend
The local BLUETTI control UI SHALL allow a user to trigger the supported initial command set through the local backend and SHALL display the resulting outcome.

#### Scenario: User sends a supported command
- **WHEN** a user triggers a supported device command from the local control page
- **THEN** the UI sends the request to the local backend and shows whether the command succeeded or failed

### Requirement: Local UI Surfaces Backend Or Session Failures
The local BLUETTI control UI SHALL provide visible error feedback when the local backend cannot authenticate, refresh state, or execute a command.

#### Scenario: Backend request fails
- **WHEN** the backend returns an authentication, connectivity, or command error for a UI action
- **THEN** the UI shows an error state or message that explains the action did not complete successfully