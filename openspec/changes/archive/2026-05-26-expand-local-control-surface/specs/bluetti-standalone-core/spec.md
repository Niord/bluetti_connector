## ADDED Requirements

### Requirement: Standalone Core Classifies Command-Capable Device States
The BLUETTI standalone core SHALL preserve enough device-state metadata for the backend to distinguish writable controls from read-only telemetry and SHALL keep the allowed value set for command-capable states when BLUETTI provides one.

#### Scenario: Device state exposes supported control values
- **WHEN** a discovered or refreshed device state includes explicit control options for a writable BLUETTI state
- **THEN** the standalone core preserves those allowed values so the caller can validate and present that state as a constrained control

#### Scenario: Device state is telemetry only
- **WHEN** a discovered or refreshed device state represents read-only runtime telemetry
- **THEN** the standalone core does not classify that state as a writable control only because it lacks enumerated options

## MODIFIED Requirements

### Requirement: Standalone Core Executes Supported Device Commands
The BLUETTI standalone core SHALL send supported control commands for a discovered device, SHALL validate requested values against the current command-capable state metadata before sending them when the local snapshot is sufficient to do so, and SHALL return the resulting success or failure to the local backend.

#### Scenario: Supported command succeeds
- **WHEN** the local backend sends a supported command for a command-capable state with an allowed value
- **THEN** the standalone core forwards the command to the BLUETTI cloud and returns a success result that includes the targeted device and command outcome

#### Scenario: Unsupported or invalid command is rejected
- **WHEN** the local backend submits a command for a read-only state or a value that is not allowed for the current command-capable state metadata
- **THEN** the standalone core returns a validation or execution failure instead of reporting success