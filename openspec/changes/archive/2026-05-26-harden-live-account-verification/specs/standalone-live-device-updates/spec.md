## MODIFIED Requirements

### Requirement: Standalone Backend Maintains BLUETTI Live Update Session
The standalone backend SHALL start and stop a BLUETTI websocket session for the active authenticated local session, SHALL expose whether live updates are connected, degraded, or unavailable, and SHALL support explicit live-account verification of authenticated `wss://` readiness through a sanitized backend-owned verification path.

#### Scenario: Backend session enables live updates
- **WHEN** the local backend has a valid authenticated BLUETTI session and websocket configuration
- **THEN** it starts the backend-managed live update session and exposes that live-update status through local backend state

#### Scenario: Live update session becomes unavailable
- **WHEN** the BLUETTI websocket session fails, disconnects, or cannot be started for the current backend session
- **THEN** the backend marks live updates as degraded or unavailable and keeps manual refresh or command flows usable

#### Scenario: Live-account verification checks websocket readiness
- **WHEN** live-account verification is explicitly invoked with authenticated `wss://` session prerequisites
- **THEN** the backend reports sanitized websocket readiness status as connected, degraded with reason, or unavailable without exposing raw websocket payloads or secrets