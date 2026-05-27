## Why

The repository now has a public-facing documentation surface, but it still looks unfinished to outside readers because the project does not yet advertise repeatable automated checks, contributor issue paths, or package metadata links. The next small public-polish slice should make the repository look maintained and navigable without widening into release engineering or package publishing.

## What Changes

- Add a lightweight GitHub Actions workflow that runs the existing Python, web, and Swift verification commands already documented in the repository.
- Add GitHub issue templates and a pull-request template that match the token-sensitive contribution and security guidance already documented publicly.
- Add public project metadata links for the Python package and repository surface.
- Add README badges only after the workflow names and project URLs exist.

## Capabilities

### New Capabilities

- `public-repository-automation`: Public repository automation, contributor intake templates, and project metadata for the standalone Python, local web, and Swift surfaces.

### Modified Capabilities

None.

## Impact

- Affects GitHub workflow configuration, repository templates, root README status signals, and Python package metadata.
- Reuses existing verification commands instead of changing runtime behavior or test scope.
- Does not add release publishing, binary distribution, installers, or live-account CI automation.