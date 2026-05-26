## Context

The current native Swift slices compile and the browser login starts correctly, which rules out package wiring and most of the request-building path. The failure now appears after the browser submits credentials and tries to return to the app, which strongly suggests a callback-lifecycle issue around `ASWebAuthenticationSession` rather than BLUETTI API transport itself.

The most likely local problem is that the session lifecycle and callback completion are not explicitly constrained to the main actor. That is easy to miss because the surrounding SwiftUI view model is `@MainActor`, but `ASWebAuthenticationSession` completion handlers can arrive off the main queue and still touch state or continuation boundaries that expect the UI actor.

## Goals / Non-Goals

**Goals:**
- make the native browser OAuth callback path main-actor safe for macOS apps
- preserve the existing `BluettiKit` public API so consumers only need the package update, not a rewritten integration
- keep the menu bar sample aligned with the fixed path and validate the native build again

**Non-Goals:**
- redesigning the native auth flow around a dedicated settings window
- changing BLUETTI endpoint semantics or token exchange logic
- adding websocket live updates or other unrelated native features

## Decisions

### 1. Main-actor isolate the browser OAuth session lifecycle
The fix will move `ASWebAuthenticationSession` ownership and callback handling onto the main actor.

Why: that directly addresses the observed dispatch assertion and matches the UI-bound nature of the Apple auth session API.

Alternative considered: leave the session object nonisolated and only wrap selected state mutations in `DispatchQueue.main.async`. Rejected because it would be less explicit and easier to regress.

### 2. Keep the app-facing view model API unchanged
The fix will preserve the current `connect()` and `authenticate(...)` flow in the sample unless a small actor-bridging adjustment is required.

Why: the user already copied this integration into Xcode, so the least disruptive correction is the best one.

Alternative considered: introduce a new auth coordinator abstraction in the sample app. Rejected because it widens the change for a narrow runtime defect.

## Risks / Trade-offs

- [The callback crash could also depend on menu-bar-specific presentation edge cases] -> Fix the main-actor ownership first because it is the most local plausible cause; only widen scope if the issue survives that correction.
- [Objective-C auth-session protocol methods can be sensitive to actor annotations] -> Rebuild the sample package after the change so any actor-interop mistake is caught immediately.

## Migration Plan

1. Update the OpenSpec artifacts for the callback-threading fix.
2. Main-actor isolate the browser OAuth session implementation and any needed sample integration points.
3. Rebuild the sample package and rerun OpenSpec validation.

Rollback strategy: revert the Swift auth-session fix if it proves unrelated; no persisted-session migration is involved.

## Open Questions

- Whether a later native slice should always open a dedicated app window before browser OAuth instead of relying on menu bar window anchors.