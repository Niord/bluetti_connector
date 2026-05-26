## Context

The current repository already carries the reusable native BLUETTI client in `swift/BluettiKit`, but the user is building a real menu bar app in Xcode and needs a concrete SwiftUI application surface rather than isolated networking primitives. The existing app sketch uses a `BluettiManager` with random values and a timer, which is the correct local anchor because that is exactly where the sample should substitute real account session, device refresh, charging inference, and notification behavior.

This slice should stay app-facing and copyable. The sample must show how to connect a menu bar extra to `BluettiKit`, how to start browser OAuth from a macOS app, how to surface device and error state sanely in a compact menu, and how to poll because websocket live updates are still intentionally out of scope for the native client kit.

## Goals / Non-Goals

**Goals:**
- add a SwiftUI menu bar sample app package that compiles on macOS and depends on the local `BluettiKit` package
- provide a `BluettiMonitor`-style view model that loads persisted tokens, authenticates through browser OAuth, polls device state, selects a device, and exposes derived battery and power state to the UI
- provide compact sample UI for login, refresh, device selection, status display, AC/DC output toggles, and low-battery notifications
- document exactly what should be copied or adapted in an Xcode app and what app configuration is required

**Non-Goals:**
- adding websocket live updates to `BluettiKit`
- shipping a polished production macOS app or design system
- solving every possible BLUETTI model-specific state presentation in the sample UI
- replacing the user's Xcode project structure directly from this repository

## Decisions

### 1. Ship the sample as a second local Swift package
The repository will add `swift/BluettiMonitorSample` as an executable Swift package that depends on `../BluettiKit`.

Why: this keeps the sample code isolated from the reusable client kit, makes the sample compile in CI-like local validation with `swift build`, and still leaves the source files easy to copy into an Xcode app.

Alternative considered: place loose `.swift` files in a docs folder. Rejected because the user asked for code they can copy, and compile-checked sample code is more trustworthy than documentation-only snippets.

### 2. Use a `@MainActor` observable view model as the app boundary
The sample will centralize account session, device polling, selected device, error state, and notification behavior in a single view model rather than spreading async work across SwiftUI views.

Why: the user's current `BluettiManager` already acts as the natural seam. Replacing it with a real app-facing model minimizes translation effort into the Xcode project.

Alternative considered: put networking calls directly in button actions or use many small environment objects. Rejected because it would be harder to copy and reason about.

### 3. Poll on a repeating async task instead of a Foundation timer
The sample will use a cancellable async polling task with `Task.sleep` instead of `Timer.scheduledTimer`.

Why: polling work already needs async `BluettiClient` calls, and task-based polling is easier to cancel and keep aligned with Swift concurrency.

Alternative considered: keep the existing timer approach. Rejected because it introduces actor hopping and timer lifecycle edge cases without benefit.

### 4. Infer charging state from positive input power and keep notifications edge-triggered
The sample will derive `isCharging` from positive PV or grid input power and send a low-battery notification only when the level crosses below the configured threshold.

Why: `BluettiKit` exposes normalized power helpers today, but not a dedicated charging flag. Edge-triggered notifications avoid repeated alerts every poll cycle.

Alternative considered: use only battery percentage with no charging inference or notify on every low poll. Rejected because both outcomes make the menu bar label and alerts less useful.

## Risks / Trade-offs

- [A menu bar-only app may not always have an obvious presentation anchor for browser OAuth] -> Use the first available app window as the sample default and document that a real app may prefer a dedicated auth or settings window.
- [Polling can make status look less live than websocket updates] -> Keep the polling interval explicit and leave live updates as a later native slice.
- [BLUETTI accounts can expose multiple devices with different state shapes] -> Support device selection and show only the first verified telemetry helpers by default while preserving room for future expansion.
- [Notification permissions or unavailable device state can complicate first-run UX] -> Request permissions up front, keep failures non-fatal, and show current app error state inside the menu.

## Migration Plan

1. Add OpenSpec artifacts for the menu bar sample capability.
2. Add `swift/BluettiMonitorSample` with the sample app source files and README.
3. Build the sample package and validate OpenSpec artifacts.
4. Leave the change active until the user has copied or adapted the code, or archive it if no follow-up changes are needed.

Rollback strategy: remove the sample package and change artifacts; this slice does not alter persisted BLUETTI session format or Python runtime behavior.

## Open Questions

- Whether a future native slice should move authentication into a dedicated app window instead of using a menu bar initiated OAuth session.
- Whether the sample should later grow per-state detail rows beyond the first battery, power, and AC/DC surface.