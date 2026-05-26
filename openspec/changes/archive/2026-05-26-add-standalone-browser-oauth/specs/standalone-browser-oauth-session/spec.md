## ADDED Requirements

### Requirement: Standalone Backend Starts BLUETTI Browser OAuth
The standalone backend SHALL provide a local browser-login start route that creates callback state and redirects the operator to the BLUETTI authorization endpoint.

#### Scenario: Browser login is started from the local app
- **WHEN** the operator starts BLUETTI login from the local standalone app
- **THEN** the backend creates a short-lived OAuth state value and redirects the browser to the configured BLUETTI authorize URL with the local callback URI and that state

### Requirement: Standalone Backend Completes OAuth Callback Exchange
The standalone backend SHALL validate the callback state, exchange a valid authorization code for BLUETTI tokens, and bootstrap the local session from the exchanged token state.

#### Scenario: OAuth callback succeeds
- **WHEN** BLUETTI redirects the browser back with a valid authorization code and matching callback state
- **THEN** the backend exchanges the code for access and refresh tokens, persists the resulting session state, and redirects the browser back to the local app with sanitized success status

### Requirement: Standalone Backend Rejects Invalid OAuth Callback State
The standalone backend SHALL reject callback requests with unknown, expired, or reused state and SHALL NOT mutate the active session for those requests.

#### Scenario: OAuth callback state is invalid
- **WHEN** the callback request arrives with missing, expired, or mismatched state
- **THEN** the backend refuses the callback, leaves the current session unchanged, and redirects the browser back to the local app with sanitized failure status