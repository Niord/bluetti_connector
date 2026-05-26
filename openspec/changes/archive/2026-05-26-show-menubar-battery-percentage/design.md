## Context

The current SwiftUI sample already derives `menuBarTitle` from the selected device battery level, so there is no missing BLUETTI data or view-model state to solve. The visible problem is narrower: `MenuBarExtra` currently receives a `Label(viewModel.menuBarTitle, systemImage: viewModel.batteryIcon)`, and in the user's Xcode-hosted app that renders as an icon-only status item even when the title is populated.

This change should stay local to the status item view layer. The polling flow, device refresh logic, OAuth path, and command execution already work, and changing them would widen a simple UI follow-up into unrelated behavior risk.

## Goals / Non-Goals

**Goals:**
- make the menu bar item show the current battery percentage immediately when a selected device is available
- keep the current battery icon so the status item still conveys charging and battery-state context
- keep the packaged sample and the single-file Xcode copy variant behavior aligned

**Non-Goals:**
- changing how battery level is fetched, refreshed, or normalized
- redesigning the popup menu content
- adding websocket live updates or any new BLUETTI client behavior

## Decisions

### 1. Replace `Label(...)` with an explicit text-and-icon stack in the status item
The menu bar status item will use a small `HStack` with `Text(viewModel.menuBarTitle)` and `Image(systemName: viewModel.batteryIcon)` instead of `Label`.

Why: the current issue is specific to how the label is rendered by the status item host, not to the underlying title value. An explicit stack removes the framework's label-style interpretation and makes the percentage visible whenever the title contains battery data.

Alternative considered: keep `Label` and apply a label style override. Rejected because that still depends on `Label`-specific rendering behavior and is less direct than composing the visible content explicitly.

### 2. Use `monospacedDigit()` on the title text
The battery percentage text will opt into `monospacedDigit()`.

Why: this keeps the menu bar item width steadier as the battery level changes from one percentage to another.

Alternative considered: leave the default digit spacing. Rejected because the cost of a one-line stability improvement is negligible.

## Risks / Trade-offs

- [The status item can become slightly wider than the current icon-only rendering] -> Keep the text short, continue using the existing compact `menuBarTitle` states, and preserve the small SF Symbol icon.
- [Some users may prefer icon-only appearance] -> Keep the implementation local and easy to adjust later if a configurable display mode becomes worth adding.

## Migration Plan

1. Update the OpenSpec change artifacts for the status item battery-percentage follow-up.
2. Patch both Swift menu bar entrypoints to use explicit text-plus-icon content.
3. Rebuild the sample package and run OpenSpec validation.

Rollback strategy: restore the previous `Label(...)` usage in the two sample entrypoints and remove this change's artifacts.

## Open Questions

- Whether a later native app slice should let the user choose between text-plus-icon and icon-only menu bar presentation.