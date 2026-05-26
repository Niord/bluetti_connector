# standalone-live-account-verification Specification

## Purpose
Define the standalone runtime contract for explicit, gated, and secret-safe verification against a real BLUETTI account.

## Requirements
### Requirement: Standalone Runtime Exposes Gated Live-Account Verification
The standalone runtime SHALL provide an explicit, opt-in live-account verification flow that runs only when required live-account inputs are present.

#### Scenario: Live verification prerequisites are missing
- **WHEN** a user starts the live-account verification flow without required live-account inputs
- **THEN** the runtime fails fast with a sanitized prerequisite error and does not attempt cloud verification calls

#### Scenario: Live verification is explicitly requested
- **WHEN** required live-account inputs are present and the user explicitly invokes live-account verification
- **THEN** the runtime performs the live-account verification checks and reports sanitized outcomes

### Requirement: Live-Account Verification Covers Core Runtime Paths
The live-account verification flow SHALL validate backend-owned authentication, device discovery, and live-update readiness semantics for an authenticated account.

#### Scenario: Live account verification succeeds
- **WHEN** valid live-account session inputs are provided and upstream calls succeed
- **THEN** the verification flow confirms successful session bootstrap, at least one successful device query, and live-update readiness status

#### Scenario: Live account verification fails
- **WHEN** the verification flow encounters an authentication, device, or live-update failure
- **THEN** it reports a categorized sanitized failure result that distinguishes the failing stage

### Requirement: Live Verification Output Remains Secret-Safe
The live-account verification flow SHALL avoid printing or storing raw access tokens, refresh tokens, or client secrets in verification output.

#### Scenario: Verification emits diagnostics
- **WHEN** the runtime emits live-account verification diagnostics
- **THEN** diagnostics include only sanitized status and troubleshooting context without secret values