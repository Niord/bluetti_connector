## Why

The repository now contains a standalone Python BLUETTI connector, a backend-served local web control page, a Swift client package, and a macOS sample app, but the public entry points still read like an internal extraction log. Before publishing the repository, users need clear module boundaries, trustworthy setup instructions, and visible attribution to the official BLUETTI Home Assistant integration that informed the work.

## What Changes

- Restructure the root README into a concise public overview with explicit links to module-specific documentation.
- Add public documentation for Python/backend usage, the local browser test page, the Swift package, and the macOS sample app.
- Move upstream provenance from agent-only context into public-facing attribution documentation.
- Add lightweight public repository files for attribution, contribution, and security reporting where they are missing.
- Clean up temporary, duplicated, or overly internal README wording without changing runtime behavior.

## Capabilities

### New Capabilities

- `public-repository-documentation`: Public documentation, attribution, and repository navigation for publishing the mixed Python, local web, Swift package, and macOS sample project.

### Modified Capabilities

None.

## Impact

- Affects documentation and packaging metadata only: root README, module docs, public attribution files, and repository guidance files.
- Does not change Python APIs, backend routes, local web UI behavior, Swift package APIs, macOS sample behavior, or test expectations.
- May clarify existing development commands and verification workflows by moving detailed instructions out of the root README.