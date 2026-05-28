## Why

The repository's first public CI slice proved useful, but the current single workflow runs the expensive macOS Swift job on every push and pull request, even when a change only touches Python, docs, or repository metadata. During recent Swift debugging loops that behavior turned a small experiment into a noticeable GitHub Actions bill.

The next repository-automation slice should keep the public safety net while making the expensive path harder to trigger accidentally and cheaper to recover when a run is superseded or hangs.

## What Changes

- Split the existing mixed-language workflow into a cheap always-on Python or web workflow and a separate macOS Swift workflow.
- Trigger the Swift workflow only for Swift-related paths, workflow edits, or explicit manual dispatch.
- Add workflow concurrency cancellation so newer pushes automatically stop older in-progress runs on the same ref.
- Add an explicit timeout to the Swift macOS job so a future hang cannot burn unbounded runner minutes.
- Update the README badges and verification text to reflect the new workflow split and Swift trigger scope.

## Capabilities

### Modified Capabilities

- `public-repository-automation`: Public CI should preserve deterministic repository checks while containing expensive macOS validation to relevant Swift changes.

## Impact

- Affects GitHub Actions workflow configuration, root README automation badges, and durable roadmap context.
- Keeps the existing Python, browser, BluettiKit, and BluettiMonitorSample verification commands unchanged.
- Does not remove public Swift validation; it only scopes when that macOS job runs and bounds how long it can consume runner time.