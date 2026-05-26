## ADDED Requirements

### Requirement: Standalone Runtime Keeps Runtime Defaults And Verification Aligned
The standalone runtime SHALL keep its development-path defaults, focused repository verification helpers, and declared Python support aligned so contributors and operators exercise the same supported standalone contract.

#### Scenario: Development defaults resolve from the active runtime context
- **WHEN** a repository contributor starts or tests the development runtime from a repository checkout without explicit path overrides
- **THEN** the default configuration and token-store paths are resolved from the active development runtime context at settings resolution time rather than from a stale import-time location

#### Scenario: Focused verification matches declared Python support
- **WHEN** the repository runs focused standalone verification under the declared supported Python versions
- **THEN** the verification helpers and tests avoid unsupported language features unless the project metadata is updated to declare the higher Python baseline first