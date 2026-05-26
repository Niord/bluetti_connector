## Why

The standalone app can now authenticate and execute the first switch-style commands, but the local control surface is still too narrow for real device operation. The next slice should safely expose a broader set of command-capable BLUETTI states while making richer runtime state visible in the local UI.

## What Changes

- Distinguish command-capable device states from read-only telemetry so the standalone core and backend do not treat every non-enum state as a writable switch.
- Extend the command path to support safe non-switch controls, including select-style states with validated option values and clearer command metadata.
- Expand the local device UI so operators can see richer state details and trigger the newly supported safe controls from the same page.
- Add focused verification for command validation, richer state rendering, and device-specific command flows that go beyond the initial toggle-only slice.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `bluetti-standalone-core`: refine the supported command contract so commandable states, allowed values, and invalid payload rejection are modeled explicitly.
- `local-bluetti-control-ui`: extend device cards beyond toggle-only controls so the page can render richer BLUETTI state and submit validated safe commands.

## Impact

- Affects standalone device and state modeling in `src/bluetti_connector/core/models.py` and the backend command request or response boundary in `src/bluetti_connector/backend/`.
- Changes the local UI rendering and interaction model in `src/bluetti_connector/web/` so command-capable states can surface as more than on or off buttons.
- Requires new or expanded focused backend and UI-oriented smoke coverage for state classification, command validation, and richer device-card rendering.