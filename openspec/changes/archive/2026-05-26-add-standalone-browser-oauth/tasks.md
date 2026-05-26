## 1. OAuth Backend State And Settings

- [x] 1.1 Add backend OAuth settings and a local pending-state store for browser login attempts
- [x] 1.2 Add authorize-URL and authorization-code exchange helpers around the BLUETTI SSO endpoints

## 2. Backend Session Flow

- [x] 2.1 Add backend routes for browser OAuth start and callback completion
- [x] 2.2 Reuse the existing token-store and session bootstrap path when OAuth callback exchange succeeds
- [x] 2.3 Add sanitized callback failure handling for invalid or expired state and upstream exchange errors

## 3. Local UI Flow

- [x] 3.1 Add a browser-login action to the local session panel while keeping manual token entry available
- [x] 3.2 Handle callback success or failure feedback on return to the local page and refresh the runtime session view

## 4. Verification And Documentation

- [x] 4.1 Add focused tests for OAuth state validation, callback exchange, and local return-path feedback
- [x] 4.2 Update runtime documentation and repo context for local callback configuration and the browser-OAuth verification path