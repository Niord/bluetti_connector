# Security Policy

BLUETTI Connector handles local access tokens, refresh tokens, account sessions, device identifiers, and cloud requests. Treat reports and examples as sensitive by default.

## Reporting A Vulnerability

Use GitHub private vulnerability reporting if it is enabled for the public repository. If no private reporting channel is available yet, open a public issue with only redacted, non-sensitive details and ask for a private contact path.

Do not include:

- access tokens or refresh tokens
- `.env` files or token-store files
- BLUETTI account credentials
- full device serial numbers unless explicitly needed and redacted
- raw cloud responses that include account-specific data

## Supported Surface

Security-sensitive behavior currently includes:

- Python backend token handling and token-store persistence
- browser OAuth start and callback handling
- local backend device and command routes
- live-update websocket/SSE handling
- Swift Keychain token persistence and browser OAuth handling

## Local Development Hygiene

- Keep `.env` and `.local/` out of commits.
- Use fake-gateway verification when live account access is not required.
- Enable `BLUETTI_ENABLE_LIVE_ACCOUNT_VERIFICATION=true` only when intentionally making live cloud verification calls.
- Do not paste tokens or account data into test output, logs, screenshots, issues, or pull requests.
