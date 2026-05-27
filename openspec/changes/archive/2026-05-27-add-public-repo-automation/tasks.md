## 1. Repository Inputs

- [x] 1.1 Confirm the canonical public GitHub repository URL and the desired workflow trigger scope (`pull_request` only or `push` plus `pull_request`).

## 2. CI Workflow

- [x] 2.1 Add a GitHub Actions workflow that runs the existing deterministic Python, web, and Swift checks.
- [x] 2.2 Ensure the workflow names and job names are stable enough to support README badges.

## 3. Community Templates

- [x] 3.1 Add lightweight issue templates for bug reports and feature requests with token-redaction guidance.
- [x] 3.2 Add a pull-request template that asks for scope, verification, and secret-safety confirmation.

## 4. Public Metadata

- [x] 4.1 Add canonical project URLs to `pyproject.toml` using the confirmed public repository path.
- [x] 4.2 Add README badges and public links only for workflows and URLs that exist after implementation.

## 5. Validation

- [x] 5.1 Validate OpenSpec artifacts, workflow YAML, and the local Python, web, and Swift commands mirrored by CI.