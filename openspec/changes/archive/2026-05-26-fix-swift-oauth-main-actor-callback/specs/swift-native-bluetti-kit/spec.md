## ADDED Requirements

### Requirement: Swift Package Completes Browser OAuth Callback Safely On macOS
The Swift package SHALL keep the native BLUETTI browser OAuth session lifecycle on a callback path that is safe for a macOS app to resume without queue-assertion or callback-threading failure.

#### Scenario: Browser login returns to the native app
- **WHEN** a macOS app using the Swift package completes BLUETTI browser login and the callback URL returns to the app
- **THEN** the package finishes the auth-session callback flow without a dispatch queue assertion and continues to token exchange or sanitized error handling