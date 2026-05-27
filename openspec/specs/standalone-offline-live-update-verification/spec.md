# standalone-offline-live-update-verification Specification

## Purpose
Define the repository-local verification contract for backend-owned live updates through the fake BLUETTI gateway without requiring real-account credentials.

## Requirements
### Requirement: Repository Provides Offline Fake-Gateway Live-Update Verification
The repository SHALL provide a repeatable verification flow that exercises backend-owned live updates against a repository-local fake gateway without requiring live BLUETTI account credentials.

#### Scenario: Contributor runs offline live-update verification
- **WHEN** the repository-local fake gateway verification flow is invoked with the required local prerequisites
- **THEN** the backend establishes a fake-gateway live-update session, reports live updates as connected, and keeps the verification flow independent of real-account cloud access

#### Scenario: Offline verification prerequisites are missing
- **WHEN** the offline live-update verification flow is invoked without the required fake-gateway or local verification prerequisites
- **THEN** the verification flow fails fast with a local setup error instead of attempting a live-account fallback

### Requirement: Offline Verification Covers End-to-End Device Update Delivery
The offline verification flow SHALL cover fake-gateway websocket delivery through the backend live-update stream and browser-facing device refresh behavior.

#### Scenario: Fake gateway publishes a device update
- **WHEN** the fake gateway emits a live device-update notification for a visible device
- **THEN** the backend publishes the sanitized local update event and the browser-facing verification flow refreshes the affected device through backend-owned endpoints

#### Scenario: Fake gateway live updates degrade
- **WHEN** the fake gateway disconnects, rejects the websocket session, or otherwise stops delivering live updates during offline verification
- **THEN** the backend reports a degraded live-update status and the verification flow confirms manual refresh fallback remains available

### Requirement: Offline Verification Does Not Relax Default Runtime Safety
The offline fake-gateway verification flow SHALL keep insecure live-update transport opt-in and SHALL not silently broaden the default operator runtime beyond the current secure `wss://` expectation.

#### Scenario: Normal runtime remains secure by default
- **WHEN** the standalone runtime starts without the explicit offline verification opt-in
- **THEN** insecure fake-gateway live updates remain disabled and unsupported `ws://` endpoints do not appear connected

#### Scenario: Offline verification enables local insecure transport explicitly
- **WHEN** a contributor enables the explicit offline verification gate for a supported local fake-gateway endpoint
- **THEN** the repository verification flow may use that local insecure transport without changing the default runtime contract for normal operator sessions