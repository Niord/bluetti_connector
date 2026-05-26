## 1. State Metadata And Validation

- [x] 1.1 Normalize device-state metadata so the backend can distinguish command-capable controls from read-only telemetry
- [x] 1.2 Extend the backend device payload and command path to preserve allowed values and display labels for supported controls
- [x] 1.3 Reject unsupported state codes or invalid values locally before forwarding commands to BLUETTI cloud

## 2. Local Control Surface

- [x] 2.1 Expand device-card rendering to show richer prioritized state values from the normalized backend payload
- [x] 2.2 Add select-style control inputs alongside the existing switch actions for backend-marked command-capable states
- [x] 2.3 Keep read-only telemetry visible without rendering unsafe control widgets or raw payload entry

## 3. Verification And Documentation

- [x] 3.1 Add focused regression coverage for state classification, allowed-value validation, and rejected invalid commands
- [x] 3.2 Extend backend smoke coverage for richer device payloads and select-style command execution
- [x] 3.3 Update runtime documentation and repo context for the expanded safe-control surface and any remaining device-specific gaps