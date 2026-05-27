## Why

The repository already covers backend-owned live updates with focused unit-style regressions and gated real-account verification, but it still lacks a deterministic end-to-end path that exercises live delivery without BLUETTI cloud dependencies. That gap leaves the fake-gateway smoke flow unable to catch integration regressions across the gateway, backend live-update fan-out, and browser-facing refresh behavior.

## What Changes

- Add a deterministic offline verification capability for backend-owned live updates that contributors can run without real-account credentials.
- Extend the fake BLUETTI gateway so integration coverage can drive backend-consumable live-update notifications instead of stopping at manual refresh and command flows.
- Add focused end-to-end coverage for live-update status transitions, local stream delivery, and UI-visible refresh behavior under the fake gateway.
- Document how the offline verification path complements the existing gated live-account verification flow rather than replacing it.

## Capabilities

### New Capabilities
- `standalone-offline-live-update-verification`: Deterministic repository-local verification for backend-owned live updates using the fake gateway and focused integration harnesses.

### Modified Capabilities
None.

## Impact

- `tests/fake_bluetti_gateway.py` and related integration helpers
- focused backend and web live-update regression coverage
- contributor-facing verification documentation and roadmap or known-issues context
- no new operator-facing runtime surface and no required live-account credentials for the new verification path