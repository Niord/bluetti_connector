## MODIFIED Requirements

### Requirement: Local UI Shows Available BLUETTI Devices
The local BLUETTI control UI SHALL display the devices exposed by the local backend together with their current connectivity or power-state summary, backend-driven live-update status, richer prioritized runtime state, and any backend-provided command metadata needed to render safe controls.

#### Scenario: Device overview renders from backend data
- **WHEN** a user opens the local BLUETTI control page and the backend returns discovered devices
- **THEN** the page shows each available device with identifying information, prioritized display values for important runtime states, control affordances only for states that the backend marks as command-capable, and whether live updates are connected or degraded

#### Scenario: Device state changes through backend live updates
- **WHEN** the backend publishes a local live update event for a device that is visible on the page
- **THEN** the UI refreshes or reconciles that device through backend-owned data and updates the displayed state without requiring the user to click refresh manually

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