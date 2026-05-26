## Context

The current repository has already established the verified BLUETTI HTTP and OAuth behavior through the standalone Python core and backend. That Python implementation is still valuable as the closest executable reference for cloud endpoints, request headers, refresh-token semantics, and device-state interpretation, but it is not the intended runtime for a native macOS application.

This change introduces a repository-local Swift Package that can be attached to an Xcode app as a local dependency. The package will implement the verified BLUETTI cloud flows directly in Swift: browser-login URL construction, authorization-code exchange, refresh-token recovery, device list and refresh calls, device-state decoding, and supported control commands. The first slice should stay narrow and production-oriented: account connection, battery percentage, power readings, AC/DC status, and AC/DC control matter now; websocket live updates, installers, and a full shipped macOS app target do not.

## Goals / Non-Goals

**Goals:**
- create a self-contained Swift Package that can be opened from this repository and linked into an Xcode macOS app
- implement native BLUETTI browser OAuth, authorization-code exchange, refresh-token recovery, and token-store boundaries without Python runtime dependencies
- implement device discovery, per-device refresh, and typed helpers for battery SOC, prioritized power metrics, and AC/DC control states
- implement supported command execution for switch-style and select-style BLUETTI states with local validation based on current state metadata
- provide repository-local guidance for wiring the package into an Xcode macOS app

**Non-Goals:**
- shipping a complete macOS application target from this repository
- reproducing every current Python backend feature, especially backend-served UI routes or local SSE fan-out
- implementing BLUETTI websocket live updates in the first Swift slice
- introducing direct username/password login when the verified BLUETTI contract still centers on browser OAuth plus token refresh

## Decisions

### 1. Place the native client in a local Swift Package under `swift/BluettiKit`
The Swift implementation will live in its own package directory instead of being mixed into `src/` or stored as loose code snippets.

Why: a Swift Package is the cleanest way to keep the native client self-contained, testable with `swift test`, and attachable to an Xcode app through “Add Local Package”.

Alternative considered: generate only copy-paste Swift source files without package structure. Rejected because it makes dependency wiring, tests, and Xcode reuse weaker.

### 2. Mirror only the verified BLUETTI cloud contract and keep transport explicit
The package will use `URLSession`, `Codable`, and a small typed response envelope for the BLUETTI API instead of trying to port the Python architecture module-for-module.

Why: the stable part is the cloud contract, not the exact Python layering. A direct Swift-native transport keeps the code smaller and easier to integrate into app code.

Alternative considered: port the Python backend structure one-to-one into Swift. Rejected because it adds translation noise without improving the native API.

### 3. Expose both raw decoded device states and normalized convenience helpers
The package will preserve the raw `stateList` payload while also offering convenience accessors for the first app needs: battery percentage, prioritized power readings, AC/DC switch states, and writable controls.

Why: BLUETTI payloads vary by model, so throwing away raw state details would make future extensions harder. At the same time, the macOS app needs a stable high-level surface for common values.

Alternative considered: expose only hard-coded top-level properties. Rejected because it would either hide important device details or force repeated parsing in the app layer.

### 4. Make token persistence pluggable and ship a Keychain-backed default
The package will define a token-store protocol plus a Keychain implementation suitable for native macOS use.

Why: apps need durable session reuse, but tests should not depend on the Keychain and some callers may prefer custom storage.

Alternative considered: bake persistence directly into the client actor. Rejected because it couples networking and storage too tightly.

### 5. Include a macOS-focused browser OAuth helper, but keep the main client usable without UI frameworks
The package will keep browser OAuth core logic in plain Foundation types and add an `ASWebAuthenticationSession` helper behind conditional availability for macOS integration.

Why: this keeps the core package testable and reusable while still giving the user a concrete native login path for Xcode.

Alternative considered: keep browser login entirely out of scope and require manual token entry. Rejected because account connection is part of the requested native flow.

## Risks / Trade-offs

- [BLUETTI cloud behavior is not fully documented publicly] -> Keep the Swift implementation tightly aligned with the already verified request paths, headers, and response envelopes from the repository reference flow.
- [Model-specific state names can vary beyond the first power and switch surface] -> Preserve raw state payloads and keep convenience helpers intentionally limited to verified codes and switch metadata.
- [Browser OAuth integration depends on app callback configuration] -> Provide the helper plus explicit Xcode integration guidance, and keep manual token bootstrap possible through the lower-level client surface.
- [Future websocket support may want different session orchestration] -> Keep the first package slice centered on HTTP flows and token management so later live-update work can layer on top instead of forcing premature abstractions.

## Migration Plan

1. Add the OpenSpec artifacts for the new Swift-native capability.
2. Create the `swift/BluettiKit` package with auth, transport, models, token-store, and repository-style device service APIs.
3. Add focused Swift tests that cover OAuth URL creation, token refresh recovery, device decoding, and supported control execution.
4. Add package-level Xcode integration guidance for a macOS app.
5. Run `swift test` for the package and `DO_NOT_TRACK=1 rtk openspec validate --all --no-interactive 2>/dev/null` before closing the change.

Rollback strategy: remove the Swift package and the new OpenSpec change; no persisted data migration is required because the package introduces an independent native runtime surface.

## Open Questions

- Whether the next native slice should add BLUETTI websocket live updates or keep periodic refresh as the preferred initial app strategy.
- Whether the eventual macOS app wants to expose raw device states directly in UI or keep them behind higher-level view models.