## Context

Current coverage is deterministic for fake-gateway and local regressions, but live-account behavior remains manual. The repository already avoids printing secrets and centralizes cloud interaction in the backend, which provides a good boundary for adding a gated live verification surface.

## Goals / Non-Goals

**Goals:**
- Provide a repeatable live-account verification path that is explicit, opt-in, and safe for local operators.
- Validate the critical real-account behaviors: session bootstrap, device discovery, and live-update readiness.
- Emit only sanitized diagnostics suitable for issue triage and roadmap tracking.
- Keep default test and development workflows offline and deterministic.

**Non-Goals:**
- Running live-account checks in regular CI by default.
- Storing account credentials in repository files.
- Replacing existing fake-gateway and focused local regression coverage.

## Decisions

### 1. Keep live-account verification explicitly gated
Live-account verification runs only when dedicated environment variables are present and an explicit verification command/path is invoked.

Why: Prevent accidental cloud calls and protect local development ergonomics.

Alternative considered: auto-run live checks whenever tokens are present. Rejected because it increases accidental risk and makes local runs unpredictable.

### 2. Report sanitized verification outcomes
Verification output includes high-level status and failure categories but never raw tokens or secrets.

Why: Operators need actionable diagnostics while preserving security boundaries.

Alternative considered: full raw payload dump for debugging. Rejected due to credential leakage risk.

### 3. Verify live-update readiness as part of account checks
The flow checks authenticated websocket readiness semantics (`wss://`, connected or degraded with reason) in addition to token and device checks.

Why: Live updates are now a core runtime capability and must be covered in real-account validation.

Alternative considered: restrict live verification to token exchange and device listing only. Rejected because it leaves the websocket path unverified.

## Risks / Trade-offs

- [Live verification may fail due to upstream outages] -> Classify failures as environmental versus regression and keep offline suites as primary gate.
- [Operators may provide partial credentials] -> Validate prerequisites early and fail fast with clear sanitized guidance.
- [Slow live checks] -> Keep command scope narrow and optional.

## Migration Plan

1. Add gated live-account verification surface and prerequisite validation.
2. Wire sanitized result reporting for auth, devices, and live-update readiness.
3. Document run procedure and triage guidance.
4. Keep fake-gateway and local regression checks as required baseline while live checks remain opt-in.

## Open Questions

- Whether live-account verification should live in a dedicated CLI command or a pytest marker-based path (or both).
- Whether to store a bounded verification artifact for roadmap tracking after each manual live run.