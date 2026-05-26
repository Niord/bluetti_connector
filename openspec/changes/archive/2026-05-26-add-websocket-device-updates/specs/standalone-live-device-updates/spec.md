## ADDED Requirements

### Requirement: Standalone Backend Maintains BLUETTI Live Update Session
The standalone backend SHALL start and stop a BLUETTI websocket session for the active authenticated local session and SHALL expose whether live updates are connected, degraded, or unavailable.

#### Scenario: Backend session enables live updates
- **WHEN** the local backend has a valid authenticated BLUETTI session and websocket configuration
- **THEN** it starts the backend-managed live update session and exposes that live-update status through local backend state

#### Scenario: Live update session becomes unavailable
- **WHEN** the BLUETTI websocket session fails, disconnects, or cannot be started for the current backend session
- **THEN** the backend marks live updates as degraded or unavailable and keeps manual refresh or command flows usable

### Requirement: Standalone Backend Fans Out Live Device Update Notifications Locally
The standalone backend SHALL offer a local stream surface for browser consumers and SHALL publish sanitized device update notifications derived from BLUETTI websocket activity.

#### Scenario: Device update is observed from BLUETTI cloud
- **WHEN** the backend-managed BLUETTI websocket session indicates that a device changed
- **THEN** the backend emits a sanitized local update event that allows the browser to refresh or reconcile the affected device through backend-owned paths

#### Scenario: Subscriber connects without active live updates
- **WHEN** a local browser subscribes while live updates are not currently connected
- **THEN** the backend still responds with local stream state that explains live updates are unavailable or degraded