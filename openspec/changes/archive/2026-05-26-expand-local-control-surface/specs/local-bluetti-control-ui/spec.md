## MODIFIED Requirements

### Requirement: Local UI Shows Available BLUETTI Devices
The local BLUETTI control UI SHALL display the devices exposed by the local backend together with their current connectivity or power-state summary, richer prioritized runtime state, and any backend-provided command metadata needed to render safe controls.

#### Scenario: Device overview renders from backend data
- **WHEN** a user opens the local BLUETTI control page and the backend returns discovered devices
- **THEN** the page shows each available device with identifying information, prioritized display values for important runtime states, and control affordances only for states that the backend marks as command-capable

### Requirement: Local UI Executes Basic Device Controls Through The Backend
The local BLUETTI control UI SHALL allow a user to trigger supported switch-style and select-style device commands through the local backend using backend-provided allowed values, and SHALL display the resulting outcome.

#### Scenario: User sends a supported switch command
- **WHEN** a user triggers a supported switch-like device command from the local control page
- **THEN** the UI sends the request to the local backend and shows whether the command succeeded or failed

#### Scenario: User sends a supported select command
- **WHEN** a user chooses an allowed value for a supported select-style device state and submits it from the local page
- **THEN** the UI sends the selected value through the local backend and shows whether the command succeeded or failed

#### Scenario: Read-only state is displayed without a control
- **WHEN** the backend returns a device state that is not command-capable
- **THEN** the UI renders that state as read-only runtime information and does not offer a command submission control for it