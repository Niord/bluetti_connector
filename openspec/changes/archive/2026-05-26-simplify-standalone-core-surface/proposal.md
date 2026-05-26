## Why

The standalone BLUETTI runtime now satisfies its current OpenSpec behavior, but parts of the Python implementation still carry extraction leftovers and avoidable indirection from the upstream Home Assistant baseline. That extra surface makes the code harder to reason about, easier to misuse, and more expensive to extend even when the user-visible behavior stays the same.

## What Changes

- Remove or narrow standalone-internal APIs that are no longer part of the active runtime flow, especially Home Assistant-shaped lifecycle and callback remnants in the extracted core models.
- Simplify backend orchestration code where the current implementation repeats exception mapping, serializes and deserializes the same state shape unnecessarily, or keeps dead type branches.
- Tighten small correctness and maintainability issues in configuration and websocket support code without widening the product scope or changing the accepted standalone behavior.
- Add focused regression coverage and hygiene checks for the simplified code paths so cleanup does not regress the existing standalone contract.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `bluetti-standalone-core`: tighten the extracted core contract so the active standalone device and state flow does not depend on inactive Home Assistant-style lifecycle hooks.
- `local-operator-runtime`: tighten the development and operator runtime contract so path resolution and focused verification stay aligned with the declared standalone support surface.

## Impact

- Affects the standalone Python core in `src/bluetti_connector/core/`, especially extracted model and websocket support code.
- Affects backend orchestration and session plumbing in `src/bluetti_connector/backend/`, with the largest changes expected in `service.py` and related schema or helper boundaries.
- May tighten configuration and version-alignment details in `src/bluetti_connector/config.py`, `pyproject.toml`, and focused tests.
- Requires focused regression validation for the cleaned runtime paths because this change intentionally preserves current OpenSpec-visible behavior while reducing internal complexity.