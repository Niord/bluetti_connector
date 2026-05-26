## Context

The current standalone backend creates a session only from an access token supplied in settings or through the session endpoint. The repository already carries placeholders for refresh token and token store settings, but the runtime does not yet use them. The extracted core can report token expiry, yet the backend currently converts that directly into a visible failure instead of attempting refresh or reusing persisted session state.

The next change needs to harden real-account operation without breaking the first baseline constraints: browser code still talks only to the local backend, secrets must not be exposed in logs or UI payloads, and the standalone core must remain free of `homeassistant` imports. A direct password-grant probe against `https://sso.bluettipower.com/oauth2/token` returned `unsupported_grant_type`, so credential bootstrap is treated as unsupported from current verified behavior.

## Goals / Non-Goals

**Goals:**
- support backend-managed BLUETTI session bootstrap from direct access-token input, optional refresh-token input, or previously stored refresh context
- persist refreshed token material locally without persisting the operator password
- recover from token expiry with a bounded refresh-and-retry path before surfacing auth failure
- expose sanitized session-state metadata to the local UI so the operator can tell whether the backend is using direct, credential-backed, or stored auth state

**Non-Goals:**
- multi-user auth or remote deployment hardening
- encrypted secret storage beyond the local file boundary for this iteration
- direct browser-to-cloud BLUETTI authentication
- implementing an unverified username/password bootstrap path against the BLUETTI token endpoint
- broad device-command expansion beyond what the baseline already supports

## Decisions

### 1. Introduce a backend-owned auth resolver with explicit precedence
The backend will resolve session bootstrap in this order: explicit token request payload, persisted token store, then static settings defaults. This keeps local operator intent authoritative while still allowing unattended reuse of previously refreshed tokens.

Alternative considered: settings-only auth bootstrap. Rejected because it would force file edits for routine re-authentication and would not support the current interactive local UI flow.

### 2. Persist only token material and minimal session metadata
The local runtime will persist access token, refresh token, and minimal metadata needed to reuse or refresh a session. Passwords stay request- or settings-scoped and are never written into the token store.

Alternative considered: storing the full credential bundle in the token store. Rejected because it widens local secret exposure without being necessary for refresh-driven recovery.

### 3. Handle token expiry with one refresh-and-retry cycle
When the extracted core reports token expiry, the backend will attempt one refresh using the best available refresh context, persist the resulting tokens, and retry the failed operation once. If refresh cannot recover the session, the backend will clear the active auth state and surface a sanitized re-authentication failure.

Alternative considered: surfacing token expiry directly to the UI with no retry. Rejected because it keeps the baseline in a brittle state for normal long-lived local use.

### 4. Extend the session API and UI to describe token mode, not secrets
The session configuration flow will accept a direct access token and optional refresh token, and the session snapshot will expose sanitized metadata such as auth mode, source, refresh capability, and stored-session usage. The UI will render those hints without displaying raw secrets.

Alternative considered: implementing direct username/password bootstrap. Rejected for this change because the live BLUETTI token endpoint rejects the password grant type, so that behavior is unknown from current verified code.

## Risks / Trade-offs

- [Upstream refresh semantics are only partially documented outside Home Assistant] -> Use the upstream `oauth.py` behavior and verified `/oauth2/token` endpoint as the technical reference and keep the first implementation behind narrow smoke checks plus documented live-account verification.
- [Plain local token persistence increases filesystem secret exposure] -> Persist only token material, create the store under the existing local-state path, and avoid persisting passwords.
- [Mixed auth sources can leave stale runtime state after repeated session changes] -> Make the precedence rules explicit and clear in-memory state whenever a new session source is configured.
- [Automatic refresh can hide loops or partial failures] -> Allow only one refresh-and-retry attempt per failing operation and surface sanitized auth failure after that bound.

## Migration Plan

1. Add the token-store abstraction and backend auth resolver while preserving the current access-token flow.
2. Adapt the upstream refresh behavior into standalone core or backend-owned auth helpers.
3. Extend the session API and UI for refresh-capable token configuration and sanitized auth-state reporting.
4. Add focused smoke coverage for login bootstrap, persisted token reuse, and refresh recovery.
5. Update documentation, roadmap, and known-issues notes with the new auth model and remaining live-account gaps.

Rollback strategy: fall back to the existing access-token-only session bootstrap path and ignore persisted refresh state if the new auth resolver proves unstable.

## Open Questions

- Whether BLUETTI offers any supported standalone browser-OAuth path for local apps beyond the Home Assistant integration remains unknown from current code.
- It is not yet confirmed whether refresh-token-only bootstrap is always sufficient after long idle periods for every account state.
- The exact amount of auth-state detail that is useful in the UI without creating noise may need one iteration during implementation.