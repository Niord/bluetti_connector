## 1. Standalone Core Surface Cleanup

- [x] 1.1 Remove inactive Home Assistant-shaped lifecycle hooks from `src/bluetti_connector/core/models.py` and keep only the standalone device-state surface exercised by the backend and tests
- [x] 1.2 Simplify the active state merge and command path so backend code uses direct typed model helpers instead of raw dict round-trips
- [x] 1.3 Tighten extracted core support code such as logger contracts and websocket reconnect handling without changing accepted standalone behavior

## 2. Backend And Runtime Alignment

- [x] 2.1 Simplify `src/bluetti_connector/backend/service.py` helper boundaries to remove repeated verification-stage plumbing, dead imports, and other cleanup-only duplication
- [x] 2.2 Align runtime configuration path resolution with the selected runtime profile so development defaults are resolved at settings-build time instead of stale import time
- [x] 2.3 Align focused verification helpers and tests with the declared supported Python version, or update project metadata if a higher baseline is intentionally required

## 3. Validation And Documentation

- [x] 3.1 Add or update focused regression coverage for the cleaned standalone core and backend paths
- [x] 3.2 Run the narrowest relevant lint and pytest slices, then run the full Python test suite for the touched cleanup surface
- [x] 3.3 Update README and repository context notes if the cleanup changes any documented runtime or verification expectations