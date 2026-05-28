## MODIFIED Requirements

### Requirement: Public CI Reflects Existing Safe Verification
The repository SHALL expose automated public checks that run the existing safe Python, web, and Swift verification commands without requiring a live BLUETTI account, while containing expensive macOS verification to relevant Swift-related changes or explicit manual dispatch.

#### Scenario: Non-Swift change avoids unnecessary macOS verification
- **WHEN** a contributor pushes or updates a pull request that does not change Swift sources or workflow definitions
- **THEN** the repository automation still runs the public Python and browser checks without scheduling the macOS Swift workflow

#### Scenario: Swift-related change still triggers public macOS verification
- **WHEN** a contributor changes files under `swift/` or edits the repository workflow definitions
- **THEN** the repository automation runs the documented macOS Swift verification and reports success or failure in GitHub

#### Scenario: Superseded run is canceled on the same ref
- **WHEN** a contributor pushes a newer commit to the same branch while an older public automation run is still executing
- **THEN** the older in-progress run is canceled so the newest run becomes the authoritative result