## 1. Project Bootstrap

- [x] 1.1 Choose the initial Python backend and local web project layout and add the required dependency manifests
- [x] 1.2 Record the upstream BLUETTI source paths and reference commit or release for extracted modules
- [x] 1.3 Add local configuration scaffolding for BLUETTI credentials, runtime settings, and developer startup flow

## 2. Standalone Core Extraction

- [x] 2.1 Extract the reusable BLUETTI API, profile, model, and domain modules into a standalone package without `homeassistant` imports
- [x] 2.2 Replace Home Assistant-specific auth, event, and lifecycle hooks with standalone interfaces and error handling
- [x] 2.3 Prove device discovery, state refresh, and one supported control action through the standalone core

## 3. Local Backend Surface

- [x] 3.1 Add local backend endpoints for session setup, device listing, device state refresh, and command execution
- [x] 3.2 Add backend-side request validation and sanitized error mapping for auth, connectivity, and control failures
- [x] 3.3 Add backend-focused smoke checks or automated tests for the extracted core integration

## 4. Local Web Control UI

- [x] 4.1 Build a local web page that renders available BLUETTI devices and current state summaries from the backend
- [x] 4.2 Add the initial supported control actions and visible success or failure feedback in the UI
- [x] 4.3 Add loading, empty, and backend error states for the local control flow

## 5. Verification And Documentation

- [x] 5.1 Run an end-to-end local verification flow against a BLUETTI account or a documented smoke harness
- [x] 5.2 Update project documentation, roadmap, and provenance notes with the implemented runtime and verification flow