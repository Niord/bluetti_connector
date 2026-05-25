## Why

The upstream BLUETTI integration is implemented as a Home Assistant component, which makes its useful cloud transport, authentication, and device-control logic hard to reuse outside that runtime. We need a standalone local application so the connector can evolve independently and reach an initial user-visible win: a local web page for viewing devices and sending basic control commands.

## What Changes

- Extract a standalone Python BLUETTI core from the upstream Home Assistant integration, removing `homeassistant` runtime dependencies from the reusable transport and domain logic.
- Add a local backend surface that authenticates with the BLUETTI cloud, lists available devices, refreshes device state, and executes a small safe command set.
- Add a minimal local web control page that talks to the local backend and exposes device state plus basic control actions.
- Record upstream provenance for adapted code so later sync and review work stays traceable.

## Capabilities

### New Capabilities
- `bluetti-standalone-core`: Standalone Python core for BLUETTI authentication, cloud communication, device discovery, state refresh, and device control without Home Assistant.
- `local-bluetti-control-ui`: Local web experience that shows BLUETTI devices and lets a user perform basic control actions through the standalone backend.

### Modified Capabilities
- None.

## Impact

- Affects the repository bootstrap into a real standalone application with Python backend and local web surface.
- Introduces a clear boundary between reusable BLUETTI core logic and adapter-specific integrations.
- Requires adapting upstream BLUETTI code with traceable provenance and adding project-local verification for backend and UI behavior.