## Context

The standalone app already owns token persistence and refresh recovery, but it still relies on a manually pasted access token or refresh token for the first successful real-account session. The next slice needs to remove that initial setup friction without moving secrets into browser code or coupling the standalone runtime back to Home Assistant OAuth helpers.

The verified upstream and live BLUETTI surface gives us the same `authorize_url = /oauth2/grant` and `token_url = /oauth2/token` endpoints used by the Home Assistant integration. The existing backend already owns session bootstrap, token storage, and refresh recovery, so browser OAuth should terminate in that backend and feed the resulting token state through the same persistence and retry path.

## Goals / Non-Goals

**Goals:**
- let the local app start a BLUETTI browser login flow without asking the operator to paste tokens by hand
- keep the authorization-code exchange and client secret on the local backend, not in browser code
- reuse the existing token-store and refresh-capable session model after browser login succeeds
- surface sanitized success or failure feedback back on the local page after the OAuth callback completes

**Non-Goals:**
- replacing the existing manual token form in this slice
- multi-user or remote-network OAuth hardening beyond local-operator use
- implementing popup orchestration or websocket callback signaling in the first pass
- changing the standalone core device API contract, which still consumes access or refresh tokens from the backend

## Decisions

### 1. The backend owns both OAuth start and callback routes
The first implementation will expose backend routes such as `/api/session/oauth/start` and `/api/session/oauth/callback`. The local page will navigate to the start route, the backend will redirect to BLUETTI SSO, and the callback route will complete the authorization-code exchange before redirecting back to the local app.

Alternative considered: generating the authorize URL in browser code and posting the callback code back to the backend. Rejected because it would expose more OAuth details to browser code and complicate state validation without giving the standalone app any real benefit.

### 2. Pending OAuth state is stored in local backend memory with TTL
Each browser login attempt will create a random state value plus minimal metadata such as creation time and post-login redirect target. The backend will validate that state on callback and reject unknown or expired entries without mutating the active session.

Alternative considered: persisting pending OAuth state in the token store. Rejected because pending state is short-lived, local to a single login attempt, and should disappear cleanly across restarts rather than surviving as durable auth data.

### 3. Authorization-code exchange feeds the existing session and token-store path
When the callback succeeds, the backend will exchange the code at `/oauth2/token`, derive access and refresh tokens, and route that token state through the existing backend session configuration and persistence path. This keeps refresh recovery, token precedence, and auth error handling consistent across manual-token and browser-login session sources.

Alternative considered: creating a separate OAuth-specific session model. Rejected because it would duplicate token handling and risk divergence from the already validated refresh-retry path.

### 4. The first UX uses full-page redirect round-trips, not a popup
The local page will offer a "Connect with BLUETTI" action that navigates the current page through the backend start route. After callback processing, the backend will redirect back to `/` with sanitized query state that lets the page show success or failure feedback and reload the active session snapshot.

Alternative considered: popup-based login and `postMessage` back to the opener. Rejected for the first slice because full-page redirects are simpler to implement, easier to debug locally, and avoid extra browser coordination logic.

## Risks / Trade-offs

- [BLUETTI may enforce redirect URI constraints that differ from what upstream Home Assistant hides] -> verify the authorization-code grant shape early and keep callback URI configurable for local testing.
- [In-memory pending state is lost on backend restart during login] -> fail callback validation cleanly and ask the operator to restart the login flow.
- [Full-page redirects can feel less smooth than a popup] -> keep the callback return path explicit and surface clear status on the local page; revisit popup UX only if needed after the first working slice.
- [OAuth callback errors can leak raw upstream details] -> map callback failures to sanitized local query states and backend error messages only.

## Migration Plan

1. Add backend OAuth settings, pending-state storage, and authorize or token exchange helpers.
2. Add backend start and callback routes that convert successful OAuth login into the existing session and token-store model.
3. Extend the local UI with a browser-login action and callback status handling while preserving manual token entry as fallback.
4. Add focused tests and fake OAuth harness coverage for state validation, code exchange success, and callback failure behavior.
5. Update roadmap, docs, and live-account verification notes after the first end-to-end browser login slice works.

Rollback strategy: disable the browser-login routes and fall back to the existing manual token-entry path while keeping the token-store and refresh-recovery behavior unchanged.

## Open Questions

- Whether BLUETTI requires a specific pre-registered redirect URI format for the Home Assistant client credentials is still not confirmed from current local code.
- It is not yet confirmed whether the local app should use `/` query parameters or a dedicated callback page once the first UX is working.
- If browser OAuth succeeds, we still need to decide whether manual token entry remains a permanent fallback or only a development escape hatch.