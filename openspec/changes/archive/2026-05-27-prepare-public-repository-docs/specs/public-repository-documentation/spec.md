## ADDED Requirements

### Requirement: Public Repository Overview
The repository SHALL provide a concise public overview that identifies the Python connector, local browser test page, Swift package, and macOS sample app as separate reader entry points.

#### Scenario: Reader enters through root README
- **WHEN** a new reader opens the root README
- **THEN** the README explains the repository purpose, public status, module layout, and links to module-specific setup documentation

### Requirement: Upstream Provenance Is Public
The repository SHALL publicly document that this work is based on the official BLUETTI Home Assistant integration and SHALL identify the upstream repository, release baseline, and reference commit used for provenance.

#### Scenario: Reader audits source provenance
- **WHEN** a reader looks for upstream attribution
- **THEN** public documentation links to the official upstream repository and describes the local extraction/adaptation boundary without requiring `.agents/` context files

### Requirement: Module Setup Instructions Are Separated
The repository SHALL provide separate setup and verification instructions for the Python/backend runtime, the backend-served local web page, the Swift package, and the macOS sample app.

#### Scenario: Reader wants one module only
- **WHEN** a reader wants to run or integrate only one repository module
- **THEN** the relevant module documentation provides commands, configuration notes, and verification steps without forcing the reader through unrelated module details

### Requirement: Public Guidance Covers Security And Contributions
The repository SHALL include lightweight public guidance for contribution expectations and security reporting that reflects the local-token and cloud-account sensitivity of the project.

#### Scenario: Reader wants to report a vulnerability or contribute
- **WHEN** a reader looks for contribution or vulnerability-reporting guidance
- **THEN** public repository files describe the expected path and warn against sharing BLUETTI tokens, refresh tokens, account details, or device identifiers unnecessarily