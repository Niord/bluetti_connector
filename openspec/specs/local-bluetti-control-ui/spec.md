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
The local BLUETTI control UI SHALL provide visible error feedback when the local backend cannot authenticate, refresh state, execute a command, requires the user to re-authenticate, or the browser OAuth callback fails.

#### Scenario: Backend request fails
- **WHEN** the backend returns an authentication, re-authentication, connectivity, or command error for a UI action
- **THEN** the UI shows an error state or message that explains the action did not complete successfully and whether the session must be reconfigured

#### Scenario: Browser OAuth callback fails
- **WHEN** the local page reloads after a failed BLUETTI browser login callback
- **THEN** the UI shows sanitized callback failure feedback and leaves manual session setup available as a fallback

