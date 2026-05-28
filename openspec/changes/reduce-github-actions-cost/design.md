## Context

The repository currently exposes one public GitHub Actions workflow that always schedules both an Ubuntu Python or web job and a macOS Swift job for every push and pull request. The Linux portion is cheap, but the macOS runner is materially more expensive and has already consumed most of the observed bill during iterative Swift debugging.

The repository still needs public Swift verification because the Swift package and menu bar sample are part of the published surface. The problem is not the existence of Swift CI; the problem is that the expensive check currently runs even when a change cannot affect Swift behavior, and older runs continue burning minutes until they finish or fail.

## Goals / Non-Goals

**Goals:**

- Preserve public deterministic verification for Python, browser, and Swift surfaces.
- Avoid spending macOS runner minutes on non-Swift changes.
- Ensure repeated pushes cancel obsolete in-progress runs automatically.
- Bound the maximum macOS cost of a single bad run.

**Non-Goals:**

- Do not remove Swift CI entirely.
- Do not expand the Swift verification surface beyond the current `swift build --build-tests`, `xcrun xctest`, and `swift build` sample check.
- Do not optimize Linux workflow minutes beyond small hygiene changes.

## Decisions

1. Split Python or web and Swift into separate workflows.

   Rationale: GitHub path filters apply cleanly at the workflow trigger layer, so splitting the workflows avoids extra third-party filtering actions and makes the cost boundary explicit.

2. Keep Python and web checks broad, but path-scope Swift.

   Rationale: the Linux workflow is cheap and provides the baseline public signal. The macOS workflow should run only when `swift/**` or workflow files change, plus manual dispatch for ad hoc verification.

3. Add `concurrency.cancel-in-progress` to both workflows.

   Rationale: when several commits are pushed to the same branch during debugging, only the newest run matters. Canceling older runs reduces waste and shortens feedback loops.

4. Add a job-level timeout to the Swift workflow.

   Rationale: a future hang should fail loudly and stop billing within a bounded window rather than consuming an hour of macOS time.

## Risks / Trade-offs

- [Swift breakage from indirect non-Swift changes] -> Keep manual dispatch available and still run Swift when workflow files change.
- [More badges and workflow links in the README] -> Use only two clear public workflow surfaces: Python or web and Swift.
- [Timeout too aggressive for cold macOS runners] -> Use a conservative job cap rather than an ultra-short step cap.

## Migration Plan

1. Split the current workflow into a Linux Python or web workflow and a path-scoped macOS Swift workflow.
2. Add concurrency cancellation and a Swift timeout.
3. Update README badges and verification text to reflect the new workflow layout.
4. Validate the workflow YAML and OpenSpec artifacts.