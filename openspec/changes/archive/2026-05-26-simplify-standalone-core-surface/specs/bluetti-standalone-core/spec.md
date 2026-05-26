## ADDED Requirements

### Requirement: Standalone Core Uses A Standalone-Oriented Device-State Surface
The BLUETTI standalone core SHALL let the standalone backend build, merge, classify, and command device state through direct standalone model APIs without relying on inactive Home Assistant-style callback registration, loop injection, or entity lifecycle helpers.

#### Scenario: Backend handles device payloads through standalone model APIs
- **WHEN** the standalone backend creates or refreshes device models from BLUETTI product or status payloads
- **THEN** it can merge state, classify command-capable controls, and validate values through the active standalone model surface without registering callbacks or supplying event-loop lifecycle hooks

#### Scenario: Command flow stays on the active standalone state path
- **WHEN** the standalone backend executes a supported device command for a loaded device state
- **THEN** the core validates and applies the command through the active standalone device-state path without depending on inactive websocket callback handlers or entity-style publish hooks