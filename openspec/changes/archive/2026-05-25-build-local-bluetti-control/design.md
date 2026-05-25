## Context

The upstream BLUETTI Home Assistant integration combines reusable cloud-facing logic with Home Assistant-specific lifecycle, OAuth, event bus, registry, and entity code. This repository starts from an empty standalone workspace, so the first change needs to establish both an extraction strategy and a usable local application slice.

The main constraints are:
- the reusable core must not depend on `homeassistant` imports or runtime services;
- the first visible milestone is a local web page, not a full Home Assistant replacement;
- browser code must not talk directly to BLUETTI cloud services;
- adapted upstream logic must remain traceable so later sync or review work is practical.

## Goals / Non-Goals

**Goals:**
- define a standalone Python BLUETTI core for auth, transport, device discovery, state refresh, and control;
- expose that core through a local backend API that the UI can call safely;
- deliver a minimal local web page that lists devices, shows current state, and performs a small safe command set;
- preserve enough of the upstream request and response model to reduce extraction risk in the first iteration.

**Non-Goals:**
- full feature parity with the upstream Home Assistant integration;
- a production-grade multi-user deployment model;
- direct browser-to-cloud BLUETTI integration;
- broad UI polish, advanced dashboards, or historical analytics in the first change.

## Decisions

### 1. Split the application into core, local backend, and local web UI
The system will be structured as three layers: a standalone BLUETTI core, a local backend adapter, and a local browser UI. This keeps transport and domain logic reusable while allowing the local control surface to evolve without reintroducing Home Assistant coupling.

Alternative considered: a single monolithic app that mixes transport, HTTP routes, and UI concerns. Rejected because it would make extraction and later reuse harder.

### 2. Extract from upstream modules selectively instead of rewriting from scratch
The first implementation will adapt the upstream BLUETTI `api/`, `model/`, `profile/`, and domain portions of `models.py`, while removing Home Assistant-specific runtime hooks. This reduces protocol risk because the cloud request paths, payloads, and device model shape already exist upstream.

Alternative considered: reimplement the BLUETTI client from scratch from observed behavior. Rejected for the first change because auth, websocket, and command semantics are still partly unknown.

### 3. Move authentication ownership to the local backend boundary
Authentication, token refresh, and secret handling will live in the local backend rather than in browser code. The backend will supply the standalone core with valid credentials or session state and will expose sanitized API responses to the UI.

Alternative considered: letting the browser own BLUETTI auth. Rejected because it would expose tokens in the browser runtime and complicate refresh and secret storage.

### 4. Make the first UI deliberately narrow
The initial UI will focus on device discovery, current state visibility, and a minimal command set that is safe and easy to validate. This keeps the first change anchored on backend extraction correctness rather than broad frontend scope.

Alternative considered: replicating the full Home Assistant surface area immediately. Rejected because it would expand scope before the standalone core is proven.

### 5. Keep upstream provenance as explicit project metadata
Adapted upstream code will be accompanied by provenance notes in the change artifacts and in the extracted modules where needed. This keeps future upstream resync and review feasible without turning the local codebase into an opaque fork.

Alternative considered: importing code without provenance tracking. Rejected because later debugging and sync work would become unnecessarily expensive.

## Risks / Trade-offs

- [BLUETTI auth and token refresh may depend on Home Assistant OAuth assumptions] -> Validate auth extraction early with a dedicated smoke path before expanding backend or UI scope.
- [WebSocket/STOMP behavior may be brittle outside the original runtime] -> Keep polling-based refresh as a valid first milestone and treat websocket updates as additive if needed.
- [Upstream code may embed Home Assistant assumptions in domain objects] -> Extract only the reusable portions first and replace event-bus or registry hooks with local abstractions.
- [A narrow initial command set may feel incomplete] -> Prefer a small trustworthy control surface now and expand only after the standalone core is stable.

## Migration Plan

1. Bootstrap the standalone project structure and record upstream provenance for the extracted source.
2. Extract the standalone BLUETTI core and prove authentication, device listing, state refresh, and one control action.
3. Add a local backend API on top of the core.
4. Add a minimal local web page that consumes the backend.
5. Validate the end-to-end local flow and iterate on command coverage.

Rollback strategy: because this is a new standalone repository, rollback is simply reverting the change or pausing at a smaller validated layer such as core-only or backend-only.

## Open Questions

- What standalone credential flow will replace the current Home Assistant OAuth integration most cleanly?
- Should token persistence be file-based, memory-only, or deferred until after the first local UI milestone?
- Which exact control actions are safe enough to expose in the first UI without widening risk too quickly?
- Is websocket push required for the first milestone, or is polling sufficient for the first end-to-end slice?