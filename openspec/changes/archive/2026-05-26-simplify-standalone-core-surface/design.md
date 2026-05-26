## Context

The current standalone runtime meets its accepted OpenSpec behavior, but the Python implementation still mixes active standalone code with extraction leftovers from the Home Assistant baseline. The main examples are inactive callback or loop-oriented model hooks in the core, repeated exception mapping and state-shape round-trips in the backend service, and small contract drifts such as dead auth branches, import-time development-path resolution, and verification code that can outrun the declared Python support surface.

This change should reduce that internal drag without widening functionality. The goal is not to redesign the runtime around new abstractions, but to make the existing standalone path smaller, clearer, and more truthful to what the repository actually runs today.

## Goals / Non-Goals

**Goals:**
- remove inactive Home Assistant-shaped lifecycle helpers from the active standalone core surface when they are not exercised by the local backend or tests
- simplify active backend orchestration paths where the current implementation repeats the same failure mapping or converts model state through unnecessary intermediate shapes
- align runtime configuration and focused verification helpers with the declared standalone support contract
- preserve the current operator-facing behavior, API routes, and accepted OpenSpec capabilities while tightening maintainability

**Non-Goals:**
- adding new BLUETTI features, controls, or auth flows
- broad architectural rewrites such as splitting the backend service into many new modules without a clear payoff
- changing the accepted UI, OAuth, live-update, or operator-runtime behavior already covered by the current specs
- restoring extraction parity with upstream Home Assistant code where that parity is not used by the standalone runtime

## Decisions

### 1. Prune inactive Home Assistant-shaped model APIs instead of preserving them as speculative compatibility
The cleanup will remove or narrow model methods and constructor inputs that are not part of the active standalone runtime path, especially callback, loop, and update hooks that survived extraction but are no longer called by the backend, tests, or live-update manager.

Why: keeping unused lifecycle surface makes the standalone core look more general than it is, obscures the real command or refresh path, and raises the maintenance cost of future changes.

Alternative considered: keep the extra methods as potential future reuse points. Rejected because speculative compatibility is already causing confusion and there is no current standalone consumer for those hooks.

### 2. Favor small boundary extractions over a wholesale backend-service rewrite
`BackendService` is large because it owns several OpenSpec capabilities at once. This change will only extract or normalize the pieces that clearly reduce duplication or interface mismatch, such as repeated verification-stage error mapping, private client-context helpers, or state serialization boundaries.

Why: the service is broad for legitimate reasons, so a full decomposition would create churn without necessarily improving clarity.

Alternative considered: split `BackendService` aggressively into many new service classes. Rejected because it increases refactor risk and is not required to fix the currently identified cleanup issues.

### 3. Keep active model and backend interfaces typed and direct
Where the backend already has typed `BluettiState` or session data, the cleanup will prefer direct typed merge or helper paths instead of converting through raw dictionaries or dead type branches.

Why: the extra conversions do not add behavior; they only hide the actual state flow and make bugs harder to spot.

Alternative considered: preserve the raw-dict interfaces because they match upstream payload shape. Rejected because the standalone runtime already has typed model objects at these boundaries.

### 4. Align repository verification with declared runtime support
The cleanup will treat the declared support contract as authoritative: development-path defaults should resolve at the right time for the selected runtime profile, dead auth or import branches should be removed, and focused tests or verification helpers should not rely on language features beyond the declared supported Python version without updating metadata.

Why: silent drift between metadata, runtime defaults, and verification erodes trust in the repository even when the current tests happen to pass on the maintainer's machine.

Alternative considered: leave those small mismatches for a later hygiene pass. Rejected because they are cheap to fix now and directly support the cleanup goal.

## Risks / Trade-offs

- [A supposedly inactive extracted hook may still be valuable for a future upstream sync] -> Remove only symbols with confirmed no current standalone call path and keep upstream provenance notes for later recovery if needed.
- [Cross-cutting cleanup can accidentally change accepted runtime behavior] -> Keep the change bounded to the reviewed hotspots and run the focused regression slices plus full Python tests before closing tasks.
- [Small simplifications may tempt a broader refactor while touching the same files] -> Limit each task to the smallest root-cause simplification that removes verified dead surface or duplication.
- [Tightening version-alignment may reveal pre-existing test assumptions] -> Treat metadata, docs, and focused tests as one contract and update them together when required.

## Migration Plan

1. Remove or narrow dead standalone-core surface and update any affected backend call sites.
2. Simplify active backend helpers and state-merge paths without changing route behavior.
3. Align configuration and verification code with the declared runtime contract.
4. Re-run focused regressions, full Python tests, and OpenSpec validation.

Rollback strategy: revert the cleanup slice and restore the previous implementation; no user data migration is required because this change does not alter persisted state formats.

## Open Questions

- Whether any retained but awkward helper in `BackendService` still deserves a follow-up extraction after the low-risk cleanup is complete.
- Whether the repository should raise its declared minimum Python version instead of keeping tests compatible with the current `>=3.9` contract.