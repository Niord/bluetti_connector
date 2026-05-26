## Context

The standalone connector now covers backend-owned authentication, device discovery, refresh, and the first safe switch-style commands. The current control surface is still constrained by an overly rough state model: the local UI only renders toggle buttons, the backend request shape only carries `fnCode` and `fnValue`, and the standalone core currently infers writability too loosely from BLUETTI state payloads.

Recent live-device work exposed why the next slice should be more explicit. Some returned states are clearly telemetry and should remain read-only, while others include richer control semantics such as select-style values that the local page cannot yet submit. The next change should widen the supported control surface without collapsing back into raw, device-specific payload entry.

## Goals / Non-Goals

**Goals:**
- classify BLUETTI states so the backend and UI can distinguish writable controls from read-only telemetry
- support a broader but still safe control surface, starting with switch-style and select-style states that expose allowed values
- surface richer device state in the local UI using backend-provided display data and command metadata
- reject invalid or unsupported command payloads before they are sent to BLUETTI cloud when the current state snapshot is sufficient to do so

**Non-Goals:**
- generic free-form numeric or text command entry for arbitrary BLUETTI states
- websocket-driven live updates in this slice
- solving every model-specific BLUETTI command quirk in one pass
- removing existing manual fallback paths when device metadata is too sparse to support richer controls safely

## Decisions

### 1. The backend will expose explicit command metadata instead of forcing the UI to infer writability
The next slice should derive commandability from normalized backend metadata rather than asking browser code to guess from raw `fnType` or `supportModeValues`. This keeps validation and future device-specific exceptions in one place, and it avoids repeating the current mistake where non-enum states can be mistaken for writable switches.

Alternative considered: keep the current API shape and let the UI infer control widgets from raw state fields. Rejected because it spreads BLUETTI quirks into browser code and makes it harder to keep validation consistent with backend execution.

### 2. The first expanded control surface will stay limited to switch-style and select-style commands
The safest next step is to support controls whose valid values are already explicit in the current device snapshot: binary toggles and select-like states with enumerated options. This broadens real usability while avoiding free-form command entry for numeric or opaque values that still need device-specific understanding.

Alternative considered: add a generic command composer for any `fnCode` and `fnValue`. Rejected because it would bypass the current safety goal and turn the local app into a thin raw API client.

### 3. Command validation should happen before the cloud call and should use the current merged device snapshot
The backend should validate that a requested state is command-capable and that the requested value is allowed by the most recent merged device view before forwarding the command. That keeps failure feedback local and deterministic for unsupported values, while still relying on BLUETTI cloud as the final authority for model-specific runtime constraints.

Alternative considered: rely only on BLUETTI cloud rejection. Rejected because it would keep avoidable validation errors in the slow path and produce weaker operator feedback.

### 4. Richer UI state and richer controls should share one normalized device-card model
The same backend-normalized state payload should drive both read-only display rows and interactive controls. The UI should render read-only telemetry as display rows, switch-like states as direct actions, and select-like states as constrained choice controls using the allowed option labels from the backend.

Alternative considered: keep separate display and command models. Rejected because it would duplicate state mapping logic and increase drift between what the user sees and what they can control.

## Risks / Trade-offs

- [Some BLUETTI models may expose inconsistent `fnType` or option metadata] -> Normalize command metadata in the backend and keep the first expanded surface limited to states whose writability can be justified from the current snapshot.
- [Local validation can still disagree with cloud-only runtime constraints] -> Treat backend validation as a preflight filter and preserve sanitized cloud failures as the final fallback.
- [Richer device cards can become noisy if too many states are rendered] -> Keep prioritized state surfacing and render interactive controls only for explicitly command-capable states.
- [Refreshing state after commands may still show sparse upstream data on some models] -> Reuse the existing merged product/status refresh path instead of trusting a single upstream payload.

## Migration Plan

1. Extend the backend device payload so each state can expose normalized command metadata and allowed values when present.
2. Update command validation and execution to use that metadata before forwarding to BLUETTI cloud.
3. Extend the local page to render switch and select controls from the normalized device-card model while preserving read-only state rows.
4. Add focused regression coverage for state classification, invalid command rejection, and the richer device-card interactions.

Rollback strategy: keep the new metadata additive where possible and fall back to the existing switch-only UI path if richer controls reveal unsafe or inconsistent device behavior.

## Open Questions

- Whether any high-value BLUETTI controls need device-specific value transforms even when the current snapshot exposes enumerated options.
- Whether the backend command response should eventually include separate `displayState` and `controlState` groupings once the device-card surface grows further.