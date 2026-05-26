## Why

The repository has strong fake-gateway and focused regression coverage, but still lacks an automated, trustworthy way to verify behavior against a real BLUETTI account. As more session and live-update logic moves into the backend, we need an explicit live-account verification contract that improves confidence without leaking secrets.

## What Changes

- Add a dedicated live-account verification capability for the standalone runtime that defines a safe, operator-driven verification path.
- Introduce sanitized runtime and verification outputs that confirm auth, device discovery, and live-update readiness without printing tokens.
- Add a scoped verification command or test path that can be enabled only when explicit live-account environment prerequisites are present.
- Document required environment variables, operator steps, and failure triage flow for live-account verification.

## Capabilities

### New Capabilities
- `standalone-live-account-verification`: Safe, explicit verification flow and reporting contract for real BLUETTI account checks.

### Modified Capabilities
- `standalone-live-device-updates`: Define verification expectations for authenticated `wss://` behavior under real-account checks.

## Impact

- backend verification utilities and/or CLI surface
- runtime status reporting and sanitized diagnostics
- test harness gating for live-account runs
- documentation and known-issues guidance for operator verification