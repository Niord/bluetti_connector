# local-bluetti-control-ui Specification

## Purpose
Define the local backend-served BLUETTI control page contract for device overview, basic command execution, and visible handling of backend and session failures.

## Requirements
### Requirement: Local UI Configures Token-Based Session
The local BLUETTI control UI SHALL allow a user to configure the local backend session with a direct access token and, when available, an optional refresh token.

#### Scenario: User configures a token-based session
- **WHEN** a user submits the session form with a direct access token
- **THEN** the UI sends a token-based session request to the backend and shows the configured state when the backend accepts it

#### Scenario: User configures a refresh-capable session
- **WHEN** a user submits the session form with a direct access token and a refresh token
- **THEN** the UI sends a refresh-capable session request to the backend and shows the configured state when the backend accepts it

### Requirement: Local UI Shows Sanitized Authentication Session State
The local BLUETTI control UI SHALL display which authentication mode is active and whether the backend is using stored session material without revealing secrets.

#### Scenario: Backend resumes from stored session material
- **WHEN** the page loads and the backend session snapshot indicates stored or refreshed token state
- **THEN** the UI shows that the session was restored from backend-managed state without exposing raw credentials or tokens

### Requirement: Local UI Starts Browser-Based BLUETTI Login
The local BLUETTI control UI SHALL offer a browser-login action that sends the operator through the backend-owned BLUETTI OAuth flow without exposing client secrets or token exchange details in browser code.

#### Scenario: User starts browser-based login
- **WHEN** the user chooses the browser-based BLUETTI login action from the local page
- **THEN** the UI navigates through the backend OAuth start route and returns to the local page after the callback completes

### Requirement: Local UI Shows Available BLUETTI Devices
The local BLUETTI control UI SHALL display the devices exposed by the local backend together with their current connectivity or power-state summary, backend-driven live-update status, richer prioritized runtime state, and any backend-provided command metadata needed to render safe controls.

#### Scenario: Device overview renders from backend data
- **WHEN** a user opens the local BLUETTI control page and the backend returns discovered devices
- **THEN** the page shows each available device with identifying information, prioritized display values for important runtime states, control affordances only for states that the backend marks as command-capable, and whether live updates are connected or degraded

#### Scenario: Device state changes through backend live updates
- **WHEN** the backend publishes a local live update event for a device that is visible on the page
- **THEN** the UI refreshes or reconciles that device through backend-owned data and updates the displayed state without requiring the user to click refresh manually

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

### Requirement: Local UI Surfaces Backend Or Session Failures
The local BLUETTI control UI SHALL provide visible error or degraded-state feedback when the local backend cannot authenticate, refresh state, execute a command, requires the user to re-authenticate, the browser OAuth callback fails, or live updates fall back to polling.

#### Scenario: Backend request fails
- **WHEN** the backend returns an authentication, re-authentication, connectivity, or command error for a UI action
- **THEN** the UI shows an error state or message that explains the action did not complete successfully and whether the session must be reconfigured

#### Scenario: Browser OAuth callback fails
- **WHEN** the local page reloads after a failed BLUETTI browser login callback
- **THEN** the UI shows sanitized callback failure feedback and leaves manual session setup available as a fallback

#### Scenario: Live updates are degraded
- **WHEN** the backend reports that live updates are unavailable or disconnected for the current session
- **THEN** the UI shows that the page has fallen back to manual refresh or polling instead of pretending live updates are active

