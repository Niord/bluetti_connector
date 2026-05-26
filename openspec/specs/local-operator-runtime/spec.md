# local-operator-runtime Specification

## Purpose
Define the operator-facing runtime packaging, startup, and persistence contract for the standalone local backend and web UI.

## Requirements
### Requirement: Standalone Runtime Provides An Operator Startup Path
The standalone runtime SHALL provide a stable operator-facing startup command for the local backend and web UI that does not require a repository checkout or development reload behavior.

#### Scenario: Operator starts the packaged runtime
- **WHEN** the standalone package is installed and the operator launches the normal runtime command
- **THEN** the local backend and web UI start with operator-oriented defaults rather than development reload semantics

#### Scenario: Development startup remains available
- **WHEN** a repository contributor launches the development command
- **THEN** the development-oriented startup path remains available for local iteration without changing the operator command contract

### Requirement: Standalone Runtime Uses Stable Config And State Paths
The standalone runtime SHALL resolve its default configuration and persisted session state from deterministic application directories instead of the current working directory, while allowing explicit overrides.

#### Scenario: Operator starts the runtime from an arbitrary directory
- **WHEN** the operator launches the packaged runtime from any working directory without overriding config or token-store paths
- **THEN** the runtime resolves the default configuration file and persisted session state from the application-specific default directories

#### Scenario: Operator provides explicit runtime overrides
- **WHEN** explicit configuration or token-store paths are provided through supported settings overrides
- **THEN** the runtime uses those explicit paths instead of the packaged defaults

### Requirement: Standalone Runtime Documents Repeatable Local Installation
The standalone runtime SHALL document a repeatable installation and startup flow for local operators, including where configuration and persisted session state live by default.

#### Scenario: Operator follows documented install flow
- **WHEN** a local operator follows the documented installation and startup instructions
- **THEN** the operator can install the package, start the runtime, and understand where to configure settings and find persisted session state

### Requirement: Standalone Runtime Keeps Runtime Defaults And Verification Aligned
The standalone runtime SHALL keep its development-path defaults, focused repository verification helpers, and declared Python support aligned so contributors and operators exercise the same supported standalone contract.

#### Scenario: Development defaults resolve from the active runtime context
- **WHEN** a repository contributor starts or tests the development runtime from a repository checkout without explicit path overrides
- **THEN** the default configuration and token-store paths are resolved from the active development runtime context at settings resolution time rather than from a stale import-time location

#### Scenario: Focused verification matches declared Python support
- **WHEN** the repository runs focused standalone verification under the declared supported Python versions
- **THEN** the verification helpers and tests avoid unsupported language features unless the project metadata is updated to declare the higher Python baseline first