## MODIFIED Requirements

### Requirement: Standalone Core Authenticates Against BLUETTI Cloud
The BLUETTI standalone core SHALL establish and maintain an authenticated BLUETTI cloud session from backend-provided access tokens or refresh tokens, and SHALL surface unrecoverable authentication failure to its caller.

#### Scenario: Stored or provided token is reused
- **WHEN** the local backend provides a valid access token or refresh token to the standalone core
- **THEN** the standalone core reuses or refreshes that token context without requiring the caller to resubmit username and password

#### Scenario: Authentication expires and can be refreshed
- **WHEN** the BLUETTI cloud rejects the current access token but the available refresh context is still valid
- **THEN** the standalone core refreshes the session so the caller can retry the pending operation without Home Assistant event handling

#### Scenario: Authentication expires or fails unrecoverably
- **WHEN** the BLUETTI cloud rejects login credentials or refresh context cannot recover the session
- **THEN** the standalone core reports the session failure to the local backend without requiring Home Assistant event handling

## ADDED Requirements

### Requirement: Standalone Core Supports Persisted Session Tokens
The BLUETTI standalone core SHALL support backend-provided persistence of refreshed session tokens so a standalone runtime can resume from stored session state without manual token re-entry.

#### Scenario: Refreshed tokens are saved
- **WHEN** the standalone core obtains a new access token or refresh token through login or refresh
- **THEN** it provides the updated token state to the backend token-store boundary for durable local persistence

#### Scenario: Persistence is not configured
- **WHEN** the backend does not provide token persistence for the current runtime
- **THEN** the standalone core still authenticates and refreshes in memory for the lifetime of the current process