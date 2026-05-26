## Context

The standalone app currently ships one script, `bluetti-connector-dev`, which starts uvicorn with `reload=settings.dev_reload`. Configuration is loaded from a repository-relative `.env`, and the default token store path is also relative to the current working directory. That works for development, but it makes a normal operator install fragile because startup behavior and persisted session state depend on where the process is launched.

## Goals / Non-Goals

**Goals:**
- Provide a stable operator entrypoint that runs the local backend and web UI without dev-reload semantics.
- Move default config and persisted session state to deterministic application directories that do not depend on the caller's working directory.
- Preserve the current development workflow for local repository iteration.
- Document a repeatable installation and runtime flow that matches the code-level behavior.

**Non-Goals:**
- Shipping a native desktop installer, service manager integration, or signed binary distribution in this slice.
- Replacing environment-variable configuration with a separate settings UI.
- Solving multi-user runtime isolation beyond per-user local directories.

## Decisions

### 1. Introduce separate operator and development startup paths
Add a stable operator entrypoint for normal local use and keep the existing development script for reload-oriented repository work.

Why: Operators need a predictable command that does not implicitly depend on dev reload behavior, while repository contributors still benefit from the current hot-reload path.

Alternative considered: keep a single script and drive behavior only through environment flags. Rejected because it keeps operator startup semantics implicit and easier to misconfigure.

### 2. Resolve default config and state under application directories
Define application-specific config and state directories for the standalone runtime and use them as the defaults for `.env` loading and token persistence. Explicit `BLUETTI_*` environment overrides remain authoritative.

Why: The packaged runtime needs deterministic persistence that survives changes to the launch directory.

Alternative considered: leave paths relative and only update documentation. Rejected because it would keep the operator flow brittle and make support harder.

### 3. Keep packaging lightweight and Python-native in this slice
Focus on installable package behavior, entrypoints, path resolution, and documentation instead of adding a binary packager or OS-specific service wrapper now.

Why: The immediate roadmap gap is repeatable operator runtime behavior, not a full distribution story.

Alternative considered: jump directly to PyInstaller or platform-specific packaging. Rejected because that increases blast radius before the operator runtime contract is stable.

### 4. Add focused verification around runtime path behavior
Cover the new operator defaults with focused tests for path resolution and startup configuration, and keep OpenSpec plus narrow runtime checks as the validation gate.

Why: Packaging changes are easy to regress quietly because they often fail only outside development.

## Risks / Trade-offs

- [Operator paths differ from existing ad-hoc local runs] -> Preserve explicit path overrides and document the new defaults clearly.
- [Two entrypoints may drift] -> Keep both paths thin and route them through shared startup helpers.
- [Future distribution formats may want different defaults] -> Centralize directory resolution so later packaging formats can adapt without rewriting the app contract.

## Migration Plan

1. Introduce the operator/runtime path abstraction and operator entrypoint without removing the existing development command.
2. Update docs and examples to prefer the operator path for normal local use.
3. Verify that explicit environment overrides still work for development and smoke flows.
4. Keep rollback simple by preserving the current development command and explicit path settings until the new defaults are proven.

## Open Questions

- Whether the operator entrypoint should also expose a small first-run helper or remain a plain server command in this slice.
- Whether XDG-style defaults alone are sufficient on macOS, or if a macOS-specific application support path is worth a follow-up slice.