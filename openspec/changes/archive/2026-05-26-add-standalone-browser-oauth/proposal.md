## Why

The standalone app now survives token expiry, but first-time real-account setup still requires manual access-token or refresh-token entry. The next change should remove that operator friction by letting the local app start a BLUETTI browser login flow and complete the token exchange on the backend.

## What Changes

- Add a backend-owned browser OAuth flow that starts from the local app, redirects the operator to BLUETTI SSO, validates callback state, and exchanges the authorization code for local session tokens.
- Add local callback routing, token persistence updates, and re-authentication behavior that reuses the existing refresh-capable backend session model.
- Extend the local web UI with a browser-login action, auth progress feedback, and callback completion state while keeping manual token entry available as a fallback.
- Add focused verification and documentation for the local OAuth callback flow, fake-OAuth harnesses, and the real-account validation path.

## Capabilities

### New Capabilities
- `standalone-browser-oauth-session`: backend-managed browser OAuth start, callback validation, code exchange, and local session bootstrap for the standalone app.

### Modified Capabilities
- `local-bluetti-control-ui`: extend the session UX so an operator can start browser-based BLUETTI login and understand callback or re-authentication state from the local page.

## Impact

- Affects backend API routing, auth helpers, runtime settings, local callback handling, and token-store integration.
- Likely adds backend-owned OAuth state management and authorization-code exchange around the verified BLUETTI SSO endpoints.
- Changes the local session UI to launch and reflect browser login flow instead of relying only on pasted tokens.
- Requires new focused tests, fake OAuth harness coverage, and updated documentation for local callback configuration and live-account verification.