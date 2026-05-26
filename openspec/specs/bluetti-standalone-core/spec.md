# bluetti-standalone-core Specification

## Purpose
Define the standalone BLUETTI core contract for authentication, cloud communication, device discovery, state refresh, and supported command execution without Home Assistant runtime dependencies.

## Requirements
### Requirement: Standalone Core Has No Home Assistant Runtime Dependency
The BLUETTI standalone core MUST be usable without installing or importing `homeassistant` runtime modules.

#### Scenario: Core imports in a standalone environment
- **WHEN** a standalone backend imports the BLUETTI core package in an environment without Home Assistant installed
- **THEN** the import succeeds without requiring `homeassistant` modules

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

### Requirement: Standalone Core Supports Persisted Session Tokens
The BLUETTI standalone core SHALL support backend-provided persistence of refreshed session tokens so a standalone runtime can resume from stored session state without manual token re-entry.

#### Scenario: Refreshed tokens are saved
- **WHEN** the standalone core obtains a new access token or refresh token through refresh recovery
- **THEN** it provides the updated token state to the backend token-store boundary for durable local persistence

#### Scenario: Persistence is not configured
- **WHEN** the backend does not provide token persistence for the current runtime
- **THEN** the standalone core still authenticates and refreshes in memory for the lifetime of the current process

### Requirement: Standalone Core Discovers Devices And Refreshes State
The BLUETTI standalone core SHALL retrieve the authenticated user's devices and SHALL refresh the latest known device state on request.

#### Scenario: Device list is retrieved
- **WHEN** the local backend requests the current BLUETTI account devices
- **THEN** the standalone core returns the discovered devices with their cloud identifiers and available state payloads

#### Scenario: Device state is refreshed
- **WHEN** the local backend requests a device state refresh for a discovered device
- **THEN** the standalone core returns the latest known state for that device from the BLUETTI cloud

### Requirement: Standalone Core Classifies Command-Capable Device States
The BLUETTI standalone core SHALL preserve enough device-state metadata for the backend to distinguish writable controls from read-only telemetry and SHALL keep the allowed value set for command-capable states when BLUETTI provides one.

#### Scenario: Device state exposes supported control values
- **WHEN** a discovered or refreshed device state includes explicit control options for a writable BLUETTI state
- **THEN** the standalone core preserves those allowed values so the caller can validate and present that state as a constrained control

#### Scenario: Device state is telemetry only
- **WHEN** a discovered or refreshed device state represents read-only runtime telemetry
- **THEN** the standalone core does not classify that state as a writable control only because it lacks enumerated options

### Requirement: Standalone Core Executes Supported Device Commands
The BLUETTI standalone core SHALL send supported control commands for a discovered device, SHALL validate requested values against the current command-capable state metadata before sending them when the local snapshot is sufficient to do so, and SHALL return the resulting success or failure to the local backend.

#### Scenario: Supported command succeeds
- **WHEN** the local backend sends a supported command for a command-capable state with an allowed value
- **THEN** the standalone core forwards the command to the BLUETTI cloud and returns a success result that includes the targeted device and command outcome

#### Scenario: Unsupported or invalid command is rejected
- **WHEN** the local backend submits a command for a read-only state or a value that is not allowed for the current command-capable state metadata
- **THEN** the standalone core returns a validation or execution failure instead of reporting success

