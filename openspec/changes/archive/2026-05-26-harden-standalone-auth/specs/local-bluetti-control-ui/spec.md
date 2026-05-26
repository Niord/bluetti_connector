## ADDED Requirements

### Requirement: Local UI Configures Credential-Backed Session
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

## MODIFIED Requirements

### Requirement: Local UI Surfaces Backend Or Session Failures
The local BLUETTI control UI SHALL provide visible error feedback when the local backend cannot authenticate, refresh state, execute a command, or requires the user to re-authenticate.

#### Scenario: Backend request fails
- **WHEN** the backend returns an authentication, re-authentication, connectivity, or command error for a UI action
- **THEN** the UI shows an error state or message that explains the action did not complete successfully and whether the session must be reconfigured