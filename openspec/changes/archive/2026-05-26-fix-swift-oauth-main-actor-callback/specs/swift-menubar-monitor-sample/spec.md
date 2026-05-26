## ADDED Requirements

### Requirement: Menu Bar Sample Survives Browser OAuth Return
The menu bar sample SHALL be able to return from the BLUETTI browser login callback into the app without crashing on callback-threading or queue-assertion failure.

#### Scenario: Browser OAuth completes from the sample app
- **WHEN** the sample app starts BLUETTI browser login and the operator completes authentication in the browser
- **THEN** the app returns from the callback into the menu bar flow without a dispatch queue assertion and proceeds to device loading or sanitized error display