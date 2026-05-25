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
The BLUETTI standalone core SHALL establish a valid authenticated session for BLUETTI cloud operations and SHALL surface authentication failure or expiry to its caller.

#### Scenario: Authentication succeeds with valid credentials
- **WHEN** the local backend provides valid BLUETTI authentication input to the standalone core
- **THEN** the standalone core returns a usable authenticated session for subsequent device operations

#### Scenario: Authentication expires or fails
- **WHEN** the BLUETTI cloud rejects the current session or token
- **THEN** the standalone core reports the session failure to the local backend without requiring Home Assistant event handling

### Requirement: Standalone Core Discovers Devices And Refreshes State
The BLUETTI standalone core SHALL retrieve the authenticated user's devices and SHALL refresh the latest known device state on request.

#### Scenario: Device list is retrieved
- **WHEN** the local backend requests the current BLUETTI account devices
- **THEN** the standalone core returns the discovered devices with their cloud identifiers and available state payloads

#### Scenario: Device state is refreshed
- **WHEN** the local backend requests a device state refresh for a discovered device
- **THEN** the standalone core returns the latest known state for that device from the BLUETTI cloud

### Requirement: Standalone Core Executes Supported Device Commands
The BLUETTI standalone core SHALL send supported control commands to a discovered device and SHALL return the resulting success or failure to the local backend.

#### Scenario: Supported command succeeds
- **WHEN** the local backend sends a supported control command for a discovered device
- **THEN** the standalone core forwards the command to the BLUETTI cloud and returns a success result that includes the targeted device and command outcome

#### Scenario: Unsupported or invalid command is rejected
- **WHEN** the local backend submits a command that is unsupported for the current device or payload shape
- **THEN** the standalone core returns a validation or execution failure instead of reporting success

