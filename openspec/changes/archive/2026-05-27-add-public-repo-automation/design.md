## Context

The repository now has a public documentation surface, but it still lacks the basic automation and community-facing repository mechanics that readers expect from a maintained public project. There are no GitHub Actions workflows, no issue or pull-request templates, and no project URLs in the Python package metadata.

The repository already has a safe verification baseline: Python pytest coverage against fake-gateway and backend slices, `ruff`, browser-side JavaScript checks, Swift package tests, and Swift sample builds. This change should expose that baseline through automation rather than inventing new test coverage.

## Goals / Non-Goals

**Goals:**

- Add a lightweight CI workflow that runs the existing safe repository checks.
- Add public issue and pull-request templates aligned with the current contribution and security guidance.
- Add package and repository metadata links once the canonical public repository URL is known.
- Add README badges only for checks and links that actually exist after the change.

**Non-Goals:**

- Do not add live-account verification to CI.
- Do not add release publishing, PyPI uploads, Swift package registry publishing, binary packaging, installers, or notarization.
- Do not widen the test surface beyond the currently documented safe verification commands unless a separate change justifies it.
- Do not fabricate repository URLs before the canonical public repository path is confirmed.

## Decisions

1. Use one repository CI workflow with separate Python or web and Swift jobs.

   Rationale: this keeps the public badge surface simple while still reflecting the mixed-language repository. The jobs can reuse the existing commands without introducing matrix complexity in the first automation slice.

   Alternative considered: split Python, web, and Swift into multiple workflows immediately. Rejected because the first public automation slice benefits more from clarity than from fine-grained workflow separation.

2. Keep CI limited to deterministic local checks.

   Rationale: the repository already documents safe checks that do not require a live BLUETTI account. Using those same commands in CI preserves the public trust contract without risking cloud calls or token handling in automation.

   Alternative considered: include live-account verification behind repository secrets. Rejected because it widens operational complexity and secret handling before the public repository basics are stable.

3. Add structured community templates under `.github/`.

   Rationale: issue templates and a PR template make the repository feel maintained, and they can reinforce the existing rules about redacting tokens, account details, and device identifiers.

4. Treat repository URLs as a required input for implementation, not a guessed constant.

   Rationale: README badges and `pyproject.toml` URLs should point at the canonical public repository. This change can be designed now, but implementation should either use a confirmed owner or repository path or stop short of inserting placeholder links.

## Risks / Trade-offs

- [Workflow friction from mixed toolchains] -> Reuse the exact repository commands already run locally and keep the first workflow small.
- [False public confidence from partial badges] -> Only add badges for checks and links that exist in the repository after implementation.
- [Missing canonical repository URL] -> Treat the exact GitHub owner or path as an explicit open question before implementation.
- [Template noise for a still-small project] -> Keep templates lightweight and focused on actionable bug reports, feature requests, and safe PR context.

## Migration Plan

1. Confirm the canonical public GitHub repository URL.
2. Add the workflow and templates under `.github/`.
3. Add `project.urls` metadata in `pyproject.toml`.
4. Update the root README with badges that reflect the new workflow and public links.
5. Validate the new workflow files plus the existing local verification commands.

## Open Questions

- None for this slice. The canonical public repository URL is `https://github.com/Niord/bluetti_connector`, and the first workflow uses both `push` and `pull_request` triggers.
