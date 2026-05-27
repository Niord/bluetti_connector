## ADDED Requirements

### Requirement: Public CI Reflects Existing Safe Verification
The repository SHALL expose automated public checks that run the existing safe Python, web, and Swift verification commands without requiring a live BLUETTI account.

#### Scenario: Pull request triggers repository checks
- **WHEN** a contributor opens or updates a pull request
- **THEN** the repository automation runs the documented deterministic Python, web, and Swift checks and reports success or failure in GitHub

### Requirement: Public Contributor Intake Is Structured
The repository SHALL provide GitHub issue templates and a pull-request template that guide contributors toward reproducible reports and warn against sharing tokens, account details, or unnecessary device identifiers.

#### Scenario: Contributor opens an issue or pull request
- **WHEN** a contributor starts a bug report, feature request, or pull request in the public repository
- **THEN** the repository presents structured prompts that request actionable context and explicitly discourage posting BLUETTI secrets or sensitive account data

### Requirement: Public Repository Metadata Is Linked
The repository SHALL expose public project metadata links for the Python package and root README once the canonical public repository URL is configured.

#### Scenario: Reader inspects package or README metadata
- **WHEN** a reader looks at the package metadata or the root README in the public repository
- **THEN** they can find the canonical repository, issue tracker, and automation status without relying on internal context files or placeholder URLs