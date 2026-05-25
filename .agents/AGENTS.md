# Bluetti Connector Agent Working Standard

## 1. Purpose
This document defines the active working rules for humans and LLM agents in this repository.
The goal is predictable extraction of a standalone BLUETTI connector from the upstream Home Assistant integration, with small change sets, clear provenance, and truthful verification.

### Rule Levels
- `MUST` - mandatory.
- `SHOULD` - recommended; deviations require explicit rationale.
- `CAN` - optional.

### Rule Priority
1. `MUST` overrides `SHOULD` and `CAN`.
2. If rules conflict, choose the simpler lower-risk correct option.
3. Record deliberate exceptions in the active OpenSpec change or in `.agents/context/roadmap.md`.

## 2. Source of Truth
When documents conflict, use this order:
1. Code and tests in this repository.
2. `openspec/specs/*/spec.md`.
3. `openspec/changes/*/`.
4. `.agents/context/*`.
5. Verified upstream BLUETTI Home Assistant source and release notes.
6. Any other notes.

If behavior cannot be confirmed from local code or verified upstream source, write `Unknown from current code`.

When adapting upstream code, record the upstream source path and reference URL or commit in the active OpenSpec change.

## 3. Execution Model
- `MUST`: for non-trivial work, create or continue an OpenSpec change under `openspec/changes/<name>/`.
- `SHOULD`: start with `openspec-explore` when scope, extraction boundaries, or upstream behavior are unclear.
- `MUST`: keep task execution in `openspec/changes/<name>/tasks.md`.
- `MUST`: keep cross-change backlog, phase planning, and durable decisions in `.agents/context/roadmap.md`.
- `MUST`: document durable blockers, missing upstream details, and workarounds in `.agents/context/known-issues.md`.
- `MUST`: use RTK (`rtk`) for repository shell commands. If RTK has a dedicated filter, use it; otherwise it safely passes the command through unchanged.
- `MUST`: for commands involving `openspec`, use `DO_NOT_TRACK=1`.
- `SHOULD`: if an `openspec` command still emits non-functional noise, append `2>/dev/null` so only meaningful payload is processed.
- `MUST`: keep Home Assistant-specific behavior in adapter code. Reusable transport, auth, models, and orchestration belong in the standalone core.
- `MUST`: prefer narrow, reversible extraction steps over large rewrites.
- `SHOULD`: import upstream code into clearly separated modules and remove `homeassistant` dependencies before treating it as standalone core logic.

RTK usage examples and token-oriented notes live in `.agents/context/rtk.md`.

## 4. Engineering Rules

### 4.1 General
- `MUST`: fix root causes, not only symptoms.
- `MUST`: minimize blast radius.
- `MUST`: never mark tasks done without verification.
- `MUST`: keep copied or adapted upstream behavior traceable.
- `MUST`: never commit secrets, tokens, local caches, or build outputs.
- `MUST`: preserve the MIT license requirements and attribution context when carrying upstream code forward.

### 4.2 Standalone Python Core
- `MUST`: keep the standalone core free of `homeassistant` imports.
- `MUST`: keep transport concerns separated from domain state and UI concerns.
- `MUST`: keep authentication and token refresh logic behind explicit interfaces so Home Assistant OAuth can later be replaced by standalone auth.
- `MUST`: prefer async-first I/O for HTTP and WebSocket communication.
- `MUST`: use explicit typing for public interfaces and data models.
- `SHOULD`: preserve upstream response shapes until a spec-backed normalization is introduced.
- `SHOULD`: add dependencies only with clear justification.

### 4.3 Local Web Control Slice
- `MUST`: the first standalone UI talks to a local backend, not directly to the BLUETTI cloud from browser code.
- `MUST`: first success is functional, not polished: list devices, show current state, and execute at least one safe control action.
- `SHOULD`: keep the initial page simple enough that backend extraction risks dominate the work, not frontend styling.

### 4.4 Security
- `MUST`: never log access tokens, refresh tokens, or device secrets.
- `MUST`: validate external inputs before sending commands to devices or cloud endpoints.
- `SHOULD`: default to least-privilege behavior and explicit user actions for control operations.

## 5. Skill Usage
- `MUST`: apply the relevant local skill when the task clearly matches it.
- `SHOULD`: use the minimum sufficient skill set.

Current mapping:
- Change exploration and scoping: `openspec-explore`.
- Change creation: `openspec-propose`.
- Change implementation: `openspec-apply-change`.
- Change archival: `openspec-archive-change`.
- Agent and instruction maintenance: `agent-customization`.

## 6. Definition of Done
A task is complete only when:
1. Expected behavior is implemented or the requested planning artifact is updated.
2. No relevant regressions are introduced.
3. Required checks for the changed scope pass, or any temporary gap is documented truthfully.
4. OpenSpec tasks and relevant `.agents/context/*` files are updated.
5. Upstream provenance is recorded for any adapted code.
6. Any proposed commit follows the Commit Message Protocol.

### Minimum Checks
- Instruction or documentation changes: verify touched files render correctly and run diagnostics where available.
- Python changes: run the narrowest relevant executable check available, such as `rtk pytest <target>`, `rtk python -m compileall <path>`, or a feature-scoped smoke command.
- Local backend or web changes: run the narrowest relevant executable check and record any manual smoke verification needed for the touched flow.
- OpenSpec artifacts: run `DO_NOT_TRACK=1 rtk openspec validate 2>/dev/null` when a change exists.

Required checks are only valid done gates when they are currently trustworthy in this repository state. If a check is missing, noisy, or not yet bootstrapped, document that fact in the active OpenSpec change and `.agents/context/known-issues.md`.

### Documentation Updates
- `MUST`: keep `openspec/changes/<name>/tasks.md` current during implementation.
- `MUST`: update `.agents/context/roadmap.md` when phase planning, blockers, or technical debt change.
- `MUST`: update `.agents/context/known-issues.md` when a durable blocker or workaround changes.

## 7. Commit Message Protocol
Each commit must follow:

```text
<subject>

details: <short stage goal>
- <bullet 1>
- <bullet 2>
- <bullet 3>
```

Rules:
- `MUST`: `subject` states the behavioral idea of the change.
- `MUST`: include `details:`.
- `MUST`: include 3-7 concrete bullets.
- `SHOULD`: use imperative style focused on behavioral changes.

## 8. Blockers and Non-Negotiables
- `MUST`: document technical or organizational blockers in `.agents/context/known-issues.md`.
- `MUST`: reflect roadmap-impacting blockers in `.agents/context/roadmap.md`.
- `MUST`: include a practical workaround when one exists.
- Do not close tasks without verification.
- Do not hide technical debt behind `done`.
- Do not invent behavior not supported by code or verified upstream source.
- Do not leave OpenSpec or `.agents` context stale after changes.
