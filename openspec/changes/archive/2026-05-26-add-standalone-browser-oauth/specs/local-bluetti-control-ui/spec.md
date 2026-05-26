## ADDED Requirements

### Requirement: Local UI Starts Browser-Based BLUETTI Login
The local BLUETTI control UI SHALL offer a browser-login action that sends the operator through the backend-owned BLUETTI OAuth flow without exposing client secrets or token exchange details in browser code.

#### Scenario: User starts browser-based login
- **WHEN** the user chooses the browser-based BLUETTI login action from the local page
- **THEN** the UI navigates through the backend OAuth start route and returns to the local page after the callback completes

## MODIFIED Requirements

### Requirement: Local UI Surfaces Backend Or Session Failures
The local BLUETTI control UI SHALL provide visible error feedback when the local backend cannot authenticate, refresh state, execute a command, requires the user to re-authenticate, or the browser OAuth callback fails.

#### Scenario: Backend request fails
- **WHEN** the backend returns an authentication, re-authentication, connectivity, or command error for a UI action
- **THEN** the UI shows an error state or message that explains the action did not complete successfully and whether the session must be reconfigured

#### Scenario: Browser OAuth callback fails
- **WHEN** the local page reloads after a failed BLUETTI browser login callback
- **THEN** the UI shows sanitized callback failure feedback and leaves manual session setup available as a fallback